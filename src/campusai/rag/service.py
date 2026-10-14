"""Query orchestration: route, retrieve, then ground the answer."""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import replace
from threading import local, RLock
from datetime import datetime
from zoneinfo import ZoneInfo
from ..request_timings import stage, timed_stage
from typing import Any

from ..retrieval.hybrid import HybridRetriever, RetrievalResult
from ..retrieval.routing import RoutingTrace
from .cache import RAGAnswerCache, build_rag_cache_key
from .grounding import GroundedAnswer, GroundedAnswerGenerator
from .context import resolve_query, authorized_scope
from ..observability import MetricsRegistry
from ..retrieval.canary_rollout import CanaryController, rollback_retriever
from ..retrieval.contracts import validate_filters
from .temporal import (parse_temporal_intent, resolve_temporal, temporal_fingerprint,
                       document_from_items, verified_documents, fold)
from ..retrieval.tokenizer_vi import source_body
from .multi_hop import PDF, plan_request, request_fingerprint
from .multi_hop_evidence import retrieve_composition, resolve_premises


def choose_query_mode(question: str, *, reranker_available: bool) -> str:
    """Reserve expensive reranking for comparison and multi-hop questions."""

    hard_markers = (
        "compare",
        "comparison",
        "difference",
        "khác nhau",
        "so sánh",
        "why",
        "vì sao",
        "prerequisite",
        "tiên quyết",
        "path",
        "quy trình",
    )
    hard = any(marker in question.casefold() for marker in hard_markers)
    return "hybrid_rerank" if hard and reranker_available else "hybrid"


def retrieval_query(question: str) -> str:
    """Prefer an explicit topic anchor while retaining page/scope markers."""
    raw = str(question).strip()
    if "Topic:" not in raw:
        return raw
    intent, topic = raw.split("Topic:", 1)
    topic = topic.strip()
    scope = " ".join(re.findall(r"(?:page|trang)\s+\d+|\b20\d{2}\b|\b[A-Z]{2,}\d{2,}\b", intent, re.I))
    return " ".join(part for part in (topic, scope) if part).strip() or raw


class CampusAIQueryService:
    """Public application service used by a future web/API adapter."""

    def __init__(
        self,
        retriever: HybridRetriever,
        answer_generator: GroundedAnswerGenerator,
        cache: RAGAnswerCache | None = None,
        metrics: MetricsRegistry | None = None,
        default_mode: str | None = None,
        canary: CanaryController | None = None,
        temporal_clock=None,
        temporal_timezone: str = "Asia/Bangkok",
    ) -> None:
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.cache = cache if cache is not None else RAGAnswerCache()
        self._request_local = local()
        self._corpus_identity_lock = RLock()
        self._corpus_file_hashes = OrderedDict()
        self.last_cache_hit = False
        self.last_retrieval: list[RetrievalResult] = []
        self.metrics = metrics or MetricsRegistry()
        self.default_mode = default_mode
        self.canary = canary
        self.temporal_timezone = temporal_timezone
        self.temporal_clock = temporal_clock or (lambda: datetime.now(ZoneInfo(temporal_timezone)).date())
        self._temporal_index_cache = OrderedDict()

    def _temporal_documents(self, doc_ids, filters=None):
        """Read existing BM25 metadata once per file generation; never load a model."""
        normalized_filters = validate_filters(filters)
        root = getattr(self.retriever, 'index_root', None)
        if root is None or not root.is_dir():
            return []
        selected = doc_ids if doc_ids is not None else sorted(
            path.name for path in root.iterdir() if path.is_dir() and (path / 'bm25.json').is_file())
        result = []
        with self._corpus_identity_lock:
            for doc_id in selected:
                path = root / doc_id / 'bm25.json'
                try:
                    stat = path.stat()
                    generation = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
                    cached = self._temporal_index_cache.get(path)
                    if not cached or cached[0] != generation:
                        items = json.loads(path.read_text(encoding='utf-8'))['items']
                        cached = (generation, document_from_items(doc_id, items))
                        self._temporal_index_cache[path] = cached
                    self._temporal_index_cache.move_to_end(path)
                    doc = cached[1]
                    if normalized_filters:
                        items = [i for i in doc['items'] if all(
                            str(i.get('metadata', {}).get(k, '')).casefold() == str(v).casefold()
                            for k, v in normalized_filters.items())]
                        if not items:
                            continue
                        doc = dict(doc, items=items)
                    result.append(doc)
                except (OSError, ValueError, KeyError):
                    result.append(dict(doc_id=doc_id, items=[]))
            while len(self._temporal_index_cache) > 64:
                self._temporal_index_cache.popitem(last=False)
        return result

    @property
    def last_cache_hit(self):
        return getattr(self._request_local, "cache_hit", False)

    @last_cache_hit.setter
    def last_cache_hit(self, value):
        self._request_local.cache_hit = bool(value)

    @property
    def last_retrieval(self):
        return getattr(self._request_local, "retrieval", [])

    @last_retrieval.setter
    def last_retrieval(self, value):
        self._request_local.retrieval = value

    def reset_request_state(self) -> None:
        """Discard the worker's previous request before any validation can fail."""
        self.last_cache_hit = False
        self.last_retrieval = []
        self.retriever.last_trace = None
        self._request_local.temporal_resolution = None
        self._request_local.temporal_documents = []
        self._request_local.temporal_intent = None
        self._request_local.temporal_trace = None
        self._request_local.multi_hop_trace = None
        self._request_local.multi_hop_plan = None

    @timed_stage("corpus_identity")
    def corpus_version(self, doc_ids: list[str] | None = None) -> str:
        """Bind answer reuse to the physical indexes in the selected scope."""

        selected = sorted(doc_ids if doc_ids is not None else [
            path.name for path in self.retriever.index_root.iterdir()
            if path.is_dir() and (path / "bm25.json").is_file()
        ]) if self.retriever.index_root.exists() else []
        manifest_path = self.retriever.index_root / "manifest.json"
        payload: list[dict[str, Any]] = []
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                by_doc = {item.get("document_id"): item for item in manifest.get("document_manifests", [])}
                payload = [by_doc.get(doc_id, {"document_id": doc_id}) for doc_id in selected]
            except (OSError, json.JSONDecodeError):
                payload = []
        if not payload:
            for doc_id in selected:
                path = self.retriever.index_root / doc_id / "dense.json"
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    payload.append({"document_id": doc_id, "manifest": data.get("manifest", {})})
                except (OSError, json.JSONDecodeError):
                    payload.append({"document_id": doc_id, "missing": True})
        # Corpus manifests describe their intended generation. Bind both
        # actual indexes as well, so a repaired/replaced file or a BM25-only
        # document cannot reuse an answer grounded in older bytes.
        payload = {"manifests": payload, "indexes": [
            {"document_id": doc_id,
             "bm25_sha256": self._corpus_file_sha256(self.retriever.index_root / doc_id / "bm25.json"),
             "dense_sha256": self._corpus_file_sha256(self.retriever.index_root / doc_id / "dense.json")}
            for doc_id in selected]}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _corpus_file_sha256(self, path) -> str | None:
        """Memoize verified bytes by file generation, with bounded memory."""
        with self._corpus_identity_lock:
            try:
                info = path.stat()
                generation = (info.st_mtime_ns, info.st_ctime_ns, info.st_size)
                cached = self._corpus_file_hashes.get(path)
                if cached is not None and cached[0] == generation:
                    self._corpus_file_hashes.move_to_end(path)
                    return cached[1]
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                value = digest.hexdigest()
                self._corpus_file_hashes[path] = (generation, value)
                self._corpus_file_hashes.move_to_end(path)
                while len(self._corpus_file_hashes) > 256:
                    self._corpus_file_hashes.popitem(last=False)
                return value
            except OSError:
                self._corpus_file_hashes.pop(path, None)
                return None

    @timed_stage("routing")
    def _selected_mode(self, question: str, mode: str | None, request_id: str | None = None) -> str:
        if self.canary is not None and getattr(self.retriever, "phase7_enabled", False):
            # Explicit phase7 mode must not bypass the configured canary cohort.
            if mode in {None, "phase7"}:
                return "phase7" if request_id and self.canary.admits(request_id) else "auto"
        if (not getattr(self.retriever, "phase7_enabled", False)
                and getattr(self.retriever, "phase7_activation_reason", "") != "feature_disabled"
                and mode is None and self.default_mode is None):
            return "auto"
        if mode is None and self.default_mode is None and getattr(self.retriever, "phase7_enabled", False):
            return "phase7"
        return mode or self.default_mode or choose_query_mode(
            question, reranker_available=self.retriever.reranker is not None
        )

    def retrieve(
        self,
        question: str,
        doc_ids: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        mode: str | None = None,
        request_id: str | None = None,
        history: list[dict] | None = None,
        selected_text: str | None = None,
        requires_context: bool = False,
        authorized_doc_ids: list[str] | None = None,
    ) -> list[RetrievalResult]:
        self.reset_request_state()
        doc_ids = authorized_scope(doc_ids, authorized_doc_ids)
        resolved = resolve_query(question, history=history, selected_text=selected_text, requires_context=requires_context)
        self._request_local.context_trace = resolved.cache_context()
        if resolved.needs_clarification:
            self.retriever.last_trace = RoutingTrace(route="abstain", abstained=True, abstention_reason="ambiguous_question")
            return []
        question = resolved.resolved
        temporal_docs = self._temporal_documents(doc_ids, filters)
        temporal_intent = parse_temporal_intent(question, reference_date=self.temporal_clock(), filters=filters)
        temporal = resolve_temporal(temporal_intent, temporal_docs)
        self._request_local.temporal_trace = dict(status=temporal.status, reason=temporal.reason,
            eligible_doc_ids=list(temporal.eligible_doc_ids), intent=temporal_intent.kind,
            timezone=self.temporal_timezone)
        if temporal.status not in {'resolved', 'not_applicable'}:
            reason = 'ambiguous_question' if temporal.status == 'needs_clarification' else 'insufficient_evidence'
            self.retriever.last_trace = RoutingTrace(route='abstain', abstained=True, abstention_reason=reason)
            return []
        if temporal.status == 'resolved':
            doc_ids = list(temporal.eligible_doc_ids)
        composition = plan_request(question, [d for d in temporal_docs
            if doc_ids is None or d['doc_id'] in doc_ids])
        self._request_local.multi_hop_plan = composition
        self._request_local.multi_hop_trace = None
        if composition.problem:
            self._request_local.multi_hop_trace = dict(kind=composition.kind,
                problem=composition.problem, search_calls=0, returned_candidates=0)
            return []
        selected_mode = self._selected_mode(question, mode, request_id)
        if composition.kind != 'single':
            results, trace = retrieve_composition(composition, self.retriever.search,
                filters=filters, mode=selected_mode, top_k=top_k)
            self._request_local.multi_hop_trace = trace
            self.last_retrieval = list(results)
            return results
        return self.retriever.search(
            re.sub(r'\b(?:19|20|21)\d{2}\b', '', question) if temporal.status == 'resolved' else question,
            doc_ids=doc_ids,
            filters=filters,
            top_k=top_k,
            mode=selected_mode,
        )

    def ask(
        self,
        question: str,
        doc_ids: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        mode: str | None = None,
        language: str = "vi",
        corpus_version: str | None = None,
        request_id: str | None = None,
        history: list[dict] | None = None,
        selected_text: str | None = None,
        requires_context: bool = False,
        authorized_doc_ids: list[str] | None = None,
    ) -> GroundedAnswer:
        self.reset_request_state()
        doc_ids = authorized_scope(doc_ids, authorized_doc_ids)
        resolved = resolve_query(question, history=history, selected_text=selected_text, requires_context=requires_context)
        self._request_local.context_trace = {"raw_question": resolved.raw, **resolved.cache_context()}
        if resolved.needs_clarification:
            self.last_cache_hit, self.last_retrieval = False, []
            self.retriever.last_trace = RoutingTrace(route="abstain", abstained=True, abstention_reason="ambiguous_question")
            return GroundedAnswer("Bạn đang hỏi về môn học hoặc chương trình nào?" if language == "vi"
                                  else "Which course or program are you referring to?", (), "low", True,
                                  reason="ambiguous_question", evidence_status="ambiguous")
        question = resolved.resolved
        temporal_docs = self._temporal_documents(doc_ids, filters)
        temporal_intent = parse_temporal_intent(question, reference_date=self.temporal_clock(), filters=filters)
        temporal = resolve_temporal(temporal_intent, temporal_docs)
        self._request_local.temporal_trace = dict(status=temporal.status, reason=temporal.reason,
            eligible_doc_ids=list(temporal.eligible_doc_ids), intent=temporal_intent.kind,
            timezone=self.temporal_timezone)
        if temporal.status not in {'resolved', 'not_applicable'}:
            reason = 'ambiguous_question' if temporal.status == 'needs_clarification' else 'insufficient_evidence'
            self.retriever.last_trace = RoutingTrace(route='abstain', abstained=True, abstention_reason=reason)
            message = ('Chưa đủ bằng chứng để xác định đúng phiên bản hoặc thời điểm áp dụng trong tài liệu đã chọn.'
                       if language == 'vi' else 'The selected sources do not establish the requested version or applicability date.')
            return GroundedAnswer(message, (), 'low', True, reason=reason, evidence_status='ambiguous')
        if temporal.status == 'resolved':
            doc_ids = list(temporal.eligible_doc_ids)
        selected_mode = self._selected_mode(question, mode, request_id)
        composition = plan_request(question, [d for d in temporal_docs
            if doc_ids is None or d['doc_id'] in doc_ids])
        self._request_local.multi_hop_plan = composition
        if composition.problem:
            self._request_local.multi_hop_trace = dict(kind=composition.kind,
                problem=composition.problem, search_calls=0, returned_candidates=0)
            return GroundedAnswer('Chưa đủ bằng chứng cho các nguồn hoặc quan hệ được yêu cầu.' if language == 'vi'
                else 'The selected sources do not establish all required source roles or the requested relation.',
                (), 'low', True, reason='insufficient_evidence', evidence_status='missing')
        version = corpus_version or self.corpus_version(doc_ids)
        budget = {
            "max_chars": self.answer_generator.max_context_chars,
            "max_tokens": self.answer_generator.max_context_tokens,
            "min_retrieval_score": self.answer_generator.min_retrieval_score,
            "relation_proof_policy": "direct-prerequisite-v1",
        }
        generation_config = getattr(self.answer_generator.llm, "generation_config", None)
        if generation_config:
            budget["llm_generation_config"] = generation_config
        if selected_mode == "phase7":
            budget["phase7_retrieval_fingerprint"] = self.retriever.phase7_cache_fingerprint
        if temporal.status == 'resolved':
            budget['temporal_fingerprint'] = temporal_fingerprint(temporal_intent, temporal, temporal_docs)
        if composition.kind != 'single':
            budget['multi_hop_fingerprint'] = request_fingerprint(composition)
        self._request_local.temporal_resolution = temporal
        self._request_local.temporal_documents = temporal_docs
        self._request_local.temporal_intent = temporal_intent
        key = build_rag_cache_key(
            question=question,
            language=language,
            doc_ids=doc_ids,
            filters=filters,
            top_k=top_k,
            mode=selected_mode,
            corpus_version=version,
            model=getattr(self.answer_generator.llm, "model", None) or getattr(self.answer_generator.llm, "model_name", None),
            context_budget=budget,
            request_context=resolved.cache_context(),
        )
        with self.metrics.observe("rag.ask"):
            return self._ask_uncached_or_cached(question, doc_ids, filters, top_k, selected_mode, language, version, key)

    def _ask_uncached_or_cached(self, question, doc_ids, filters, top_k, selected_mode, language, version, key):
        self.last_retrieval = []
        cached = self.cache.get(key)
        if cached is not None:
            return self._cached_answer(cached, selected_mode)
        self.last_cache_hit = False
        # Re-check under the key lock so concurrent identical requests make
        # only one retrieval/LLM call when they share a service instance.
        with self.cache.lock(key):
            cached = self.cache.get(key)
            if cached is not None:
                return self._cached_answer(cached, selected_mode)
            composition = self._request_local.multi_hop_plan
            legacy_comparison = composition.kind == 'compare' and not PDF.search(question)
            with stage("retrieval"):
                temporal = getattr(self._request_local, 'temporal_resolution', None)
                temporal_query = retrieval_query(question)
                if temporal and temporal.status == 'resolved':
                    # Eligibility was resolved already. A request's year need
                    # not occur in the selected fact chunk's text.
                    temporal_query = re.sub(r'\b(?:19|20|21)\d{2}\b', '', temporal_query)
                if legacy_comparison:
                    # Existing source-qualified comparisons already retrieve
                    # both rows. Keep their actual payload when complete, then
                    # add source-role coverage checks without re-asking Chat.
                    results = self.retriever.search(temporal_query, doc_ids=doc_ids,filters=filters,
                        top_k=min(top_k,20),mode=selected_mode)
                    premises, edge, _missing, problem = resolve_premises(composition, results)
                    self._request_local.multi_hop_trace = dict(kind=composition.kind,
                        roles=[dict(doc_id=r.doc_id,source_name=r.source_name,code=r.code) for r in composition.roles],
                        premises=[p.proof() for p in premises],edge=edge,problem=problem,
                        search_calls=1,returned_candidates=len(results),preserve_existing_prompt=True)
                    if problem:
                        self.last_retrieval=list(results)
                        return GroundedAnswer('Chưa đủ bằng chứng cho cả hai nguồn.' if language=='vi'
                            else 'Evidence is missing for a required source.',(), 'low', True,
                            reason='insufficient_evidence', evidence_status='missing')
                elif composition.kind != 'single':
                    results, composition_trace = retrieve_composition(composition, self.retriever.search,
                        filters=filters, mode=selected_mode, top_k=top_k)
                    self._request_local.multi_hop_trace = composition_trace
                    if composition_trace['problem']:
                        self.last_retrieval = list(results)
                        return GroundedAnswer('Chưa đủ bằng chứng cho tất cả các bước và nguồn được yêu cầu.' if language == 'vi'
                            else 'Evidence is missing or ambiguous for a required source or hop.',
                            (), 'low', True, reason='insufficient_evidence', evidence_status='missing')
                else:
                    results = self.retriever.search(
                        temporal_query, doc_ids=doc_ids, filters=filters,
                        top_k=max(top_k, 20) if top_k > 0 and temporal and len(temporal.groups) > 1 else top_k, mode=selected_mode,
                    )
            if (composition.kind == 'single' or legacy_comparison) and temporal and temporal.status == 'resolved':
                if any(not any(r.doc_id in group for r in results) for group in temporal.groups):
                    return GroundedAnswer('Chưa đủ bằng chứng cho từng phiên bản đã chọn.' if language == 'vi'
                        else 'Evidence is missing for a selected version.', (), 'low', True,
                        reason='insufficient_evidence', evidence_status='missing')
                # Allocate a bounded result set per comparison arm, then include
                # source-owned version/date proofs under the existing context cap.
                if len(temporal.groups) > 1:
                    per_group = max(1, top_k // len(temporal.groups))
                    # A long program name can outrank the short requested fact
                    # in split HTML blocks. Prefer that fact in the existing
                    # bounded candidates, without another retrieval/model pass.
                    focus = re.search(r'\b(?:so sanh|compare)\s+(.+?)\s+(?:cua|of)\b', fold(question))
                    if focus and 2 <= len(focus[1].split()) <= 12:
                        results = sorted(results, key=lambda r: focus[1] not in fold(source_body(
                            dict(content=r.content), decode_tables=False)))
                    results = [r for group in temporal.groups
                               for r in [x for x in results if x.doc_id in group][:per_group]]
                have = {r.chunk_id for r in results}
                for doc in getattr(self._request_local, 'temporal_documents', []):
                    if doc['doc_id'] not in temporal.eligible_doc_ids:
                        continue
                    for item in doc['items']:
                        if item['chunk_id'] in temporal.evidence_ids and item['chunk_id'] not in have:
                            results.append(RetrievalResult(item['chunk_id'], doc['doc_id'], item['page'],
                                item['content'], item.get('content_type', 'text'), 1.0, 'temporal_provenance',
                                item.get('metadata', {})))
                            have.add(item['chunk_id'])
                # Grounding must see the source-verified version of a fact
                # even when its label lives in a separate title/signature block.
                # Never use a filename or an unverified temporal annotation.
                versions = {d['doc_id']: d['version_label'] for d in verified_documents(
                    self._request_local.temporal_documents) if d.get('version_label')
                    and set(d['evidence_ids']) <= have}
                results = [replace(r, metadata={**r.metadata, 'version': versions[r.doc_id]})
                           if r.doc_id in versions else r for r in results]
            self.last_retrieval = list(results)
            if composition.kind != 'single':
                intent = self._request_local.temporal_intent
                answer = self.answer_generator.answer(question, results, language,
                    multi_hop_context=self._request_local.multi_hop_trace,
                    temporal_context=(dict(intent=intent.kind,as_of=intent.as_of,
                        reference_date=intent.reference_date,selected_doc_ids=list(temporal.eligible_doc_ids),
                        source_groups=[list(group) for group in temporal.groups],
                        qualification='Only the selected and source-verified document scope.')
                        if temporal and temporal.status=='resolved' else None))
            elif temporal and temporal.status == 'resolved':
                intent = self._request_local.temporal_intent
                answer = self.answer_generator.answer(question, results, language,
                    temporal_context=dict(intent=intent.kind, as_of=intent.as_of,
                        reference_date=intent.reference_date, selected_doc_ids=list(temporal.eligible_doc_ids),
                        source_groups=[list(group) for group in temporal.groups],
                        qualification='Only the selected and source-verified document scope.'))
            else:
                answer = self.answer_generator.answer(question, results, language)
            trace = getattr(self.retriever, "last_trace", None)
            # A temporary provider fault must not pin its Phase 6 fallback
            # answer in the active Phase 7 cache after the provider recovers.
            transient_fallback = selected_mode == "phase7" and getattr(trace, "rerank_reason", None) in {
                "queue_full", "reranker_timeout", "model_not_ready", "reranker_unavailable",
                "reranker_submit_failed", "reranker_drain_failed"}
            if not transient_fallback:
                self.cache.put(key, answer)
            return answer

    def _cached_answer(self, answer: GroundedAnswer, selected_mode: str) -> GroundedAnswer:
        self.last_cache_hit = True
        # This request performed no routing features, retrieval or inference.
        # Never attach a previous request's worker trace to a cache response.
        self.retriever.last_trace = RoutingTrace(route=selected_mode,
            answer_cache_hit=True, abstained=answer.abstained, abstention_reason=answer.reason,
            latency_ms={"parse": 0.0, "bm25": 0.0, "dense": 0.0, "fusion": 0.0,
                        "reranker": 0.0, "reranker_queue": 0.0,
                        "reranker_inference_observed": 0.0, "total": 0.0})
        return answer

    def close(self) -> None:
        try:
            close_provider = getattr(getattr(self.retriever, "phase7_provider", None), "close", None)
            if close_provider is not None:
                close_provider()
        finally:
            try:
                self.cache.close()
            finally:
                close_llm = getattr(getattr(self.answer_generator, "llm", None), "close", None)
                if close_llm is not None:
                    close_llm()

    def observe_canary_window(self, window: dict) -> str | None:
        if self.canary is None:
            raise ValueError("canary controller is not configured")
        reason = self.canary.observe(window)
        if reason:
            rollback_retriever(self.retriever, reason)
        return reason
