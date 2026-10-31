"""Query orchestration: route, retrieve, then ground the answer."""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import replace, asdict
from threading import local, RLock
from datetime import datetime
from zoneinfo import ZoneInfo
from ..request_timings import stage, timed_stage
from typing import Any

from ..retrieval.hybrid import HybridRetriever, RetrievalResult
from ..retrieval.routing import RoutingTrace
from .cache import RAGAnswerCache, build_rag_cache_key
from .grounding import GroundedAnswer, GroundedAnswerGenerator
from .context import resolve_query, authorized_scope, small_talk_kind
from ..observability import MetricsRegistry
from ..retrieval.canary_rollout import CanaryController, rollback_retriever
from ..retrieval.contracts import validate_filters, RETRIEVAL_MODES
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
    from .course_credits import folded
    separator='\nContext topic (untrusted user input): '
    if separator in raw:
        current,topic=raw.split(separator,1)
        term=r'(?:(?:học\s+)?k[ỳì]|(?:hoc\s+)?k[yi]|semester|term)\s+(?:chính|chinh|hè|he|phụ|phu|main|summer|secondary)'
        if re.search(term,current,re.I):
            topic=re.sub(term,'',topic,flags=re.I)
        raw=current+separator+topic
    normalized = folded(raw)
    normalized_words = re.sub(r"[^\w\s]", " ", normalized)
    cohort = re.search(r"\bcohorts?\s+admitted\s+from\s+(\d{4})\b", normalized_words)
    if (cohort and re.search(r"\bforeign\s+language\b", normalized_words)
            and re.search(r"\b(?:exit\s+level|graduation\s+standard)\b", normalized_words)):
        raw += (f" cohorts admitted from {cohort[1]} chuan dau ra "
                "doi voi trinh do ngoai ngu")
    if re.search(r'\b(?:footnote|asterisk note|starred note|chu thich|ghi chu dau sao)\b', normalized):
        numbered = re.search(r'\b(?:institutions?|organizations?|establishments?|rows?|items?)\s+(?:numbered|nos?\.?)\s+(\d+)\s+(?:through|to|and)\s+(\d+)\b', normalized)
        if numbered:
            raw += f" note for row numbers {numbered[1]} through {numbered[2]} date"
        else:
            raw += " note marked with an asterisk below the table date"
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
        relation_index=None,
        cache_namespace: str | None = None,
        context_candidates: int | None = None,
        document_scope_reader=None,
        confirm_institution_scope: bool = False,
    ) -> None:
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.cache = cache if cache is not None else RAGAnswerCache()
        self.cache_namespace = cache_namespace
        self.context_candidates = context_candidates
        self.document_scope_reader = document_scope_reader
        if type(confirm_institution_scope) is not bool:
            raise ValueError('confirm_institution_scope must be boolean')
        self.confirm_institution_scope = confirm_institution_scope
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
        self.relation_index = relation_index

    def _institution_request(self, question, documents, history):
        from ..retrieval.institution_scope import (InstitutionRequest, resolve_institution_request,
            requested_institution_documents, needs_institution_clarification)
        if self.confirm_institution_scope:
            return resolve_institution_request(question,documents,history)
        matched=requested_institution_documents(question,documents)
        return InstitutionRequest(question,frozenset(matched),not matched and
            needs_institution_clarification(question,documents,strict=False))

    def _calibration_cache_identity(self):
        from .calibration import calibration_payload_sha256
        calibrator = self.answer_generator.calibrator
        return calibration_payload_sha256(calibrator.to_dict()) if calibrator is not None else None

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
        self._request_local.relation_trace = None
        self._request_local.conversation_kind = None
        self._request_local.document_scope_audit = None
        self._request_local.document_scope_request = None

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
        institution = self._institution_request(question,temporal_docs,resolved.history)
        if institution.needs_clarification:
            self.retriever.last_trace = RoutingTrace(route='abstain', abstained=True,
                abstention_reason='ambiguous_question')
            return []
        question=institution.question
        if institution.doc_ids:
            temporal_docs = [d for d in temporal_docs if d['doc_id'] in institution.doc_ids]
            doc_ids = sorted(institution.doc_ids)
        temporal_intent = parse_temporal_intent(question, reference_date=self.temporal_clock(), filters=filters,
                                               source_selected=doc_ids is not None and len(doc_ids) == 1)
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
        if self.relation_index is not None:
            from .relations import plan_relation,relation_results
            plan=plan_relation(question,[d for d in temporal_docs if doc_ids is None or d['doc_id'] in doc_ids])
            if plan is not None:
                if plan.problem or top_k<=0:
                    self._request_local.relation_trace=dict(kind=plan.kind,problem=plan.problem or 'retrieval_budget_empty',
                        adjacency_lookups=0,nodes_visited=0,edges_visited=0,candidate_chunks=0,proof_fetches=0)
                    return []
                outcome=self.relation_index.lookup(plan.source.doc_id,plan.code,kind=plan.kind,filters=filters)
                self._request_local.relation_trace=outcome['trace']
                legacy=plan_request(question,temporal_docs)
                if (outcome['trace']['problem'] and not outcome['trace']['adjacency_lookups']
                        and not outcome['trace']['proof_fetches'] and plan.kind=='direct'
                        and legacy.kind=='prerequisite_lookup' and not legacy.problem):
                    self._request_local.relation_trace['fallback']='legacy_composition_no_graph_work'
                else:
                    self.last_retrieval=relation_results(outcome)
                    return self.last_retrieval
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

    def ask_source_pages(self, question, results, *, language='vi', history=None,
                         selected_text=None, requires_context=False):
        """Internal trusted-source lane; HTTP clients cannot supply evidence."""
        self.reset_request_state()
        resolved = resolve_query(question, history=history, selected_text=selected_text,
                                 requires_context=requires_context)
        self._request_local.context_trace = {'raw_question':resolved.raw, **resolved.cache_context()}
        from ..retrieval.negative import negative_query_reason
        if negative_query_reason(resolved.raw) == 'prompt_injection':
            return GroundedAnswer('Câu hỏi này không phải yêu cầu tra cứu nội dung tài liệu.' if language == 'vi'
                else 'This is not a document-content question.', (), 'low', True,
                reason='no_retrieval_evidence', evidence_status='missing')
        if resolved.needs_clarification:
            return GroundedAnswer('Bạn muốn hỏi phần nào trong các trang đã chọn?' if language == 'vi'
                else 'Which topic in the selected pages do you mean?', (), 'low', True,
                reason='ambiguous_question', evidence_status='ambiguous')
        self.last_retrieval = list(results)
        self.retriever.last_trace = RoutingTrace(route='source_pages')
        identity = hashlib.sha256(json.dumps([(r.doc_id,r.page,r.content,r.metadata) for r in results],
                                             ensure_ascii=False).encode()).hexdigest()
        key = build_rag_cache_key(question=resolved.resolved, language=language,
            doc_ids=sorted({r.doc_id for r in results}), filters=None, top_k=len(results),
            mode='source_pages', corpus_version=identity,
            model=getattr(self.answer_generator.llm,'model',None),
            calibration_artifact_sha256=self._calibration_cache_identity(),
            context_budget={'max_chars':self.answer_generator.max_context_chars,
                'max_tokens':self.answer_generator.max_context_tokens,
                'source_citations':getattr(self.answer_generator,'source_citations',False),
                'generation_config':getattr(self.answer_generator.llm,'generation_config',None),
                'json_mode':getattr(self.answer_generator.llm,'json_mode','native'),
                **({'citation_handle_policy':self.answer_generator.citation_handle_policy}
                   if getattr(self.answer_generator,'citation_handle_policy',None) else {}),
                **({'response_format_mode':self.answer_generator.llm.response_format_mode}
                   if getattr(self.answer_generator.llm,'response_format_mode','json_object') != 'json_object' else {}),
                **({'system_prompt_sha256':hashlib.sha256(self.answer_generator.llm.default_system_prompt.encode()).hexdigest()}
                   if getattr(self.answer_generator.llm,'default_system_prompt',None) else {}),
                'balanced_context':getattr(self.answer_generator,'balanced_context',False),
                'namespace':self.cache_namespace}, request_context=resolved.cache_context())
        with self.cache.lock(key):
            cached = self.cache.get(key)
            if cached is not None:
                self.last_cache_hit = True
                return cached
            answer = self.answer_generator.answer(resolved.resolved, list(results), language)
            # Explicit page requests retain their bounded insufficient-evidence
            # response. They never expand to unrequested pages. This cache is
            # already bound to the exact physical page text supplied above.
            if answer.document_absence_requested:
                answer = replace(answer, document_absence_requested=False)
            self.cache.put(key, answer)
            return answer

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
        kind = small_talk_kind(resolved.raw)
        if kind:
            self._request_local.conversation_kind = kind
            message = (('Chào bạn! Bạn muốn tìm hiểu phần nào trong tài liệu đã chọn?' if language == 'vi'
                        else 'Hello! Which part of the selected document would you like to explore?')
                       if kind == 'greeting' else
                       ('Bạn cứ hỏi tiếp phần cần tìm hiểu trong tài liệu nhé.' if language == 'vi'
                        else 'You can ask another question about the selected document.'))
            return GroundedAnswer(message, (), 'low', True, reason='ambiguous_question', evidence_status='ambiguous')
        if resolved.needs_clarification:
            self.last_cache_hit, self.last_retrieval = False, []
            self.retriever.last_trace = RoutingTrace(route="abstain", abstained=True, abstention_reason="ambiguous_question")
            return GroundedAnswer("Bạn muốn hỏi về nội dung hoặc phần nào trong tài liệu?" if language == "vi"
                                  else "Which topic or section in the document do you mean?", (), "low", True,
                                  reason="ambiguous_question", evidence_status="ambiguous")
        question = resolved.resolved
        temporal_docs = self._temporal_documents(doc_ids, filters)
        institution = self._institution_request(question,temporal_docs,resolved.history)
        if institution.needs_clarification:
            self.retriever.last_trace = RoutingTrace(route='abstain',abstained=True,abstention_reason='ambiguous_question')
            return GroundedAnswer(institution.clarification(language),
                (), 'low', True, reason='ambiguous_question', evidence_status='ambiguous')
        question=institution.question
        if institution.doc_ids:
            temporal_docs = [d for d in temporal_docs if d['doc_id'] in institution.doc_ids]
            doc_ids = sorted(institution.doc_ids)
        cache_context=resolved.cache_context()
        if self.confirm_institution_scope:
            cache_context={**cache_context,'institution_scope':'confirmed-v1','institution_question':question}
        temporal_intent = parse_temporal_intent(question, reference_date=self.temporal_clock(), filters=filters,
                                               source_selected=doc_ids is not None and len(doc_ids) == 1)
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
        if self.relation_index is not None:
            if selected_mode not in RETRIEVAL_MODES:
                raise ValueError('unsupported retrieval mode')
            related = self._ask_relation_if_supported(question, doc_ids, filters, top_k,
                selected_mode, language, corpus_version, [d for d in temporal_docs
                    if doc_ids is None or d['doc_id'] in doc_ids], cache_context)
            if related is not None:
                return related
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
        if getattr(self.answer_generator, 'source_citations', False):
            budget['citation_protocol'] = 'source-resolved-v1'
        if getattr(self.answer_generator, 'citation_handle_policy', None):
            budget['citation_handle_policy'] = self.answer_generator.citation_handle_policy
        if self.cache_namespace is not None:
            budget['cache_namespace'] = self.cache_namespace
        if self.context_candidates is not None or getattr(self.answer_generator, 'balanced_context', False):
            budget['source_windows'] = {'version': 'balanced-source-windows-v1',
                'candidates': self.context_candidates, 'balanced': self.answer_generator.balanced_context}
        if generation_config:
            budget["llm_generation_config"] = generation_config
        if getattr(self.answer_generator.llm, 'response_format_mode', 'json_object') != 'json_object':
            budget['llm_response_format_mode'] = self.answer_generator.llm.response_format_mode
        if getattr(self.answer_generator.llm, 'default_system_prompt', None):
            budget['llm_system_prompt_sha256'] = hashlib.sha256(self.answer_generator.llm.default_system_prompt.encode()).hexdigest()
        if self.document_scope_reader is not None:
            budget['document_scope_policy'] = self.document_scope_reader.policy_identity()
        if getattr(self.answer_generator.llm, 'json_mode', 'native') != 'native':
            budget['llm_json_mode'] = self.answer_generator.llm.json_mode
        if selected_mode == "phase7":
            budget["phase7_retrieval_fingerprint"] = self.retriever.phase7_cache_fingerprint
        if temporal.status == 'resolved':
            budget['temporal_fingerprint'] = temporal_fingerprint(temporal_intent, temporal, temporal_docs)
        if composition.kind != 'single':
            budget['multi_hop_fingerprint'] = request_fingerprint(composition)
        self._request_local.temporal_resolution = temporal
        self._request_local.temporal_documents = temporal_docs
        self._request_local.temporal_intent = temporal_intent
        self._request_local.document_scope_request = (question, doc_ids, filters, language)
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
            calibration_artifact_sha256=self._calibration_cache_identity(),
            request_context=cache_context,
        )
        with self.metrics.observe("rag.ask"):
            return self._ask_uncached_or_cached(question, doc_ids, filters, top_k, selected_mode, language, version, key)

    def _ask_relation_if_supported(self, question, doc_ids, filters, top_k, selected_mode,
                                   language, supplied_version, documents, request_context):
        from .relations import plan_relation,compose_relation,relation_results,answer_policy_fingerprint
        from .relation_index import RelationUnavailable
        from .grounding import _abstention
        plan=plan_relation(question,documents)
        if plan is None:
            return None
        trace=dict(kind=plan.kind,adjacency_lookups=0,nodes_visited=0,edges_visited=0,
                   candidate_chunks=0,proof_fetches=0,cold_source_loads=0,problem=plan.problem,cache_hit=False)
        self._request_local.relation_trace=trace
        if plan.problem or top_k<=0:
            return _abstention('ambiguous_question' if plan.problem else 'no_retrieval_evidence')
        try:
            fingerprint=self.relation_index.fingerprint([plan.source.doc_id])
        except RelationUnavailable as exc:
            trace['problem']=str(exc)
            legacy=plan_request(question,documents)
            if plan.kind=='direct' and legacy.kind=='prerequisite_lookup' and not legacy.problem:
                trace['fallback']='legacy_composition_no_graph_work'
                return None
            return _abstention('insufficient_evidence')
        budget=dict(max_chars=min(12000,self.answer_generator.max_context_chars),
                    max_tokens=self.answer_generator.max_context_tokens,
                    relation_generation=fingerprint,relation_request=asdict(plan),
                    relation_answer_policy=answer_policy_fingerprint())
        key=build_rag_cache_key(question=question,language=language,doc_ids=doc_ids,filters=filters,
            top_k=top_k,mode=selected_mode,corpus_version=supplied_version or fingerprint,
            model='source-relations/local',context_budget=budget,request_context=request_context,
            calibration_artifact_sha256=self._calibration_cache_identity())
        with self.metrics.observe('rag.ask'),self.cache.lock(key):
            cached=self.cache.get(key)
            if cached is not None:
                try:
                    if self.relation_index.fingerprint([plan.source.doc_id])!=fingerprint:
                        return _abstention('insufficient_evidence')
                except RelationUnavailable:
                    return _abstention('insufficient_evidence')
                trace['cache_hit']=True
                return self._cached_answer(cached,'source_relations')
            with stage('relation_lookup'):
                outcome=self.relation_index.lookup(plan.source.doc_id,plan.code,kind=plan.kind,filters=filters)
            self._request_local.relation_trace={**outcome['trace'],'cache_hit':False}
            self.last_retrieval=relation_results(outcome)
            with stage('grounding'):
                answer=compose_relation(plan,outcome,self.answer_generator,language)
            self.retriever.last_trace=RoutingTrace(route='source_relations',exact_match=not answer.abstained,
                filters_applied=bool(filters),candidate_count=outcome['trace']['candidate_chunks'],
                final_count=len(self.last_retrieval),abstained=answer.abstained,abstention_reason=answer.reason)
            # Never persist a transient corrupt/missing/proof-failure result.
            if not answer.abstained:
                try:
                    if self.relation_index.fingerprint([plan.source.doc_id])!=fingerprint:
                        return _abstention('insufficient_evidence')
                except RelationUnavailable:
                    return _abstention('insufficient_evidence')
                self.cache.put(key,answer)
            return answer

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
            if (composition.kind == 'single' and top_k > 0 and selected_mode in RETRIEVAL_MODES
                    and doc_ids is not None and len(doc_ids) == 1):
                from .curriculum_lookup import lookup_curriculum
                with stage('source_table_lookup'):
                    snapshot = self.corpus_version(doc_ids)
                    documents = self._temporal_documents(doc_ids, filters)
                    if any(item.get('metadata', {}).get('coverage_complete') is False
                           for document in documents for item in document['items']):
                        # Whole-source uniqueness/completeness cannot be proved
                        # from a published snapshot whose OCR is still running.
                        documents = []
                    projection = lookup_curriculum(question, documents, doc_ids=doc_ids,
                        language=language, calibrator=self.answer_generator.calibrator)
                    if projection is None:
                        from .course_schedule import lookup_course_schedule
                        projection = lookup_course_schedule(question, documents, doc_ids=doc_ids,
                            language=language, calibrator=self.answer_generator.calibrator)
                    if projection is None:
                        from .notice_dates import lookup_notice_date
                        projection = lookup_notice_date(question, documents, doc_ids=doc_ids,
                            language=language, calibrator=self.answer_generator.calibrator)
                    if projection is None:
                        from .award_conditions import lookup_award_condition
                        projection = lookup_award_condition(question, documents, doc_ids=doc_ids,
                            language=language, calibrator=self.answer_generator.calibrator)
                if projection is not None:
                    # An ingest/index replacement must not bind an older table
                    # snapshot to a newer cache identity (or vice versa).
                    if (snapshot != self.corpus_version(doc_ids)
                            or (version.startswith('sha256:') and snapshot != version)):
                        from .grounding import _abstention
                        self.retriever.last_trace = RoutingTrace(route='abstain', abstained=True,
                            abstention_reason='insufficient_evidence', fallback='source_changed_during_lookup')
                        return _abstention('insufficient_evidence', language=language)
                    answer, self.last_retrieval = projection
                    self.retriever.last_trace = RoutingTrace(route=self.last_retrieval[0].retriever, exact_match=True,
                        filters_applied=bool(filters), candidate_count=len(self.last_retrieval),
                        final_count=len(self.last_retrieval), abstained=False)
                    self.cache.put(key, answer)
                    return answer
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
                    retrieval_k = top_k
                    if (top_k > 0 and self.context_candidates is not None
                            and selected_mode in {'auto', 'hybrid', 'hybrid_rrf'}
                            and (not temporal or temporal.status != 'resolved')):
                        retrieval_k = max(top_k, self.context_candidates)
                    from ..retrieval.institution_scope import requested_institution_documents
                    source_groups=requested_institution_documents(question,
                        getattr(self._request_local,'temporal_documents',[]))
                    if (2<=len(source_groups)<=5 and retrieval_k>=len(source_groups)
                            and selected_mode in {'auto','hybrid','hybrid_rrf'}
                            and (not temporal or temporal.status!='resolved')):
                        # A global top-k can fill both comparison arms with one
                        # institution's rules. Reserve source-owned candidates
                        # per explicitly requested group, within the same cap.
                        each,extra=divmod(retrieval_k,len(source_groups))
                        results=[]
                        for i,doc in enumerate(sorted(source_groups)):
                            results.extend(self.retriever.search(temporal_query,doc_ids=[doc],filters=filters,
                                top_k=each+(i<extra),mode=selected_mode))
                        self.retriever.last_trace=RoutingTrace(route=selected_mode,
                            candidate_count=len(results),final_count=len(results))
                    else:
                        results = self.retriever.search(
                            temporal_query, doc_ids=doc_ids, filters=filters,
                            top_k=max(top_k, 20) if top_k > 0 and temporal and len(temporal.groups) > 1 else retrieval_k, mode=selected_mode,
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
            if (top_k>0 and composition.kind=='single' and (not temporal or temporal.status!='resolved')
                    and selected_mode in {'auto','hybrid','hybrid_rrf'}):
                from .grade_ranges import retrieval_evidence
                documents=[d for d in getattr(self._request_local,'temporal_documents',[])
                           if doc_ids is None or d['doc_id'] in doc_ids]
                from ..retrieval.institution_scope import requested_institution_documents
                groups=requested_institution_documents(question,documents)
                cap=max(top_k,self.context_candidates or top_k)
                if len(documents)==1 or (len(groups)>=2 and 2*len(groups)<=cap):
                    from .source_windows import registration_evidence
                    fields=[*retrieval_evidence(question,documents),*registration_evidence(question,documents)]
                    if fields:
                        merged=[]
                        for item in [*fields,*results]:
                            if item.chunk_id not in {r.chunk_id for r in merged}:merged.append(item)
                        results=merged[:cap]
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
            answer = self._disambiguate_institution_answer(answer,question,language)
            trace = getattr(self.retriever, "last_trace", None)
            # A temporary provider fault must not pin its Phase 6 fallback
            # answer in the active Phase 7 cache after the provider recovers.
            transient_fallback = selected_mode == "phase7" and getattr(trace, "rerank_reason", None) in {
                "queue_full", "reranker_timeout", "model_not_ready", "reranker_unavailable",
                "reranker_submit_failed", "reranker_drain_failed"}
            missing_selected_evidence = (bool(doc_ids) and not results
                and selected_mode in {'auto', 'hybrid', 'hybrid_rrf'}
                and answer.reason == 'no_retrieval_evidence'
                and self.document_scope_reader is not None)
            if (answer.document_absence_requested or missing_selected_evidence) and composition.kind == 'single':
                answer = self._audit_document_absence(answer)
            if not transient_fallback and not answer.document_absence_requested and not answer.source_scope_checked:
                self.cache.put(key, answer)
            return answer

    def _disambiguate_institution_answer(self,answer,question,language):
        """Do not blend different institutions' rules into one unqualified rule."""
        cited={c.doc_id for c in answer.citations}
        if answer.abstained or len(cited)<2:
            return answer
        documents=[d for d in getattr(self._request_local,'temporal_documents',[]) if d['doc_id'] in cited]
        if len(documents)!=len(cited) or any(not any(
                item.get('metadata',{}).get('document_type')=='regulation' for item in d['items']) for d in documents):
            return answer
        from ..retrieval.institution_scope import institution_headers,requested_institution_documents
        names=[institution_headers(d['items']) for d in documents]
        if any(not n for n in names) or set.intersection(*names):
            return answer
        if len(requested_institution_documents(question,documents))>=2:
            return answer
        labelled=requested_institution_documents(answer.answer,documents)
        if cited<=labelled:
            return answer
        return GroundedAnswer('Bạn đang hỏi quy định của trường nào? Các nguồn đã chọn có quy định riêng; hãy cho biết tên trường.'
            if language=='vi' else 'Which institution do you mean? The selected sources have separate rules.',
            (), 'low', True,reason='ambiguous_question',evidence_status='ambiguous')

    def _prepare_complete_document_scope(self):
        from .document_scope import DocumentScopeUnavailable
        reader = self.document_scope_reader
        request = getattr(self._request_local, 'document_scope_request', None)
        if reader is None or request is None:
            raise DocumentScopeUnavailable('reader_not_configured')
        question, doc_ids, filters, language = request
        composition = getattr(self._request_local, 'multi_hop_plan', None)
        if filters or composition is None or composition.kind != 'single':
            raise DocumentScopeUnavailable('filtered_or_composed_scope_not_complete')
        temporal = getattr(self._request_local, 'temporal_resolution', None)
        if temporal and temporal.status == 'resolved':
            doc_ids = list(temporal.eligible_doc_ids)
        if doc_ids is None:
            doc_ids = [d['doc_id'] for d in getattr(self._request_local, 'temporal_documents', [])]
        scope = reader.read(doc_ids)
        if scope.pdf_documents and not getattr(self.answer_generator.llm, 'allow_pdf_scope', False):
            raise DocumentScopeUnavailable('pdf_provider_scope_not_enabled')
        generator = GroundedAnswerGenerator(self.answer_generator.llm,
            max_context_chars=reader.max_context_chars, calibrator=self.answer_generator.calibrator,
            source_citations=self.answer_generator.source_citations)
        return question, language, scope, generator

    def prepare_document_scope_prompt(self):
        """Local preflight of the possible follow-up; never calls the provider."""
        question, language, scope, generator = self._prepare_complete_document_scope()
        return {'prompt': generator.prompt(question, list(scope.results), language,
                    **self._complete_scope_prompt_context(scope)),
                'answer_schema': generator.response_schema(), 'source_scope': scope.trace(),
                **({'generation_arguments': {'pdf_documents': list(scope.pdf_documents)}}
                    if scope.pdf_documents else {})}

    def _complete_scope_prompt_context(self, scope):
        context = {'document_scope_context': scope.trace()}
        temporal = getattr(self._request_local, 'temporal_resolution', None)
        if temporal and temporal.status == 'resolved':
            intent = self._request_local.temporal_intent
            context['temporal_context'] = dict(intent=intent.kind, as_of=intent.as_of,
                reference_date=intent.reference_date, selected_doc_ids=list(temporal.eligible_doc_ids),
                source_groups=[list(group) for group in temporal.groups],
                qualification='Only the selected and source-verified document scope.')
        return context

    def _audit_document_absence(self, original):
        """One authorized, bounded full-source inference after top-k abstention."""
        from .document_scope import DocumentScopeUnavailable
        from .grounding import build_context
        try:
            question, language, scope, generator = self._prepare_complete_document_scope()
        except DocumentScopeUnavailable as error:
            self._request_local.document_scope_audit = {'status': 'unavailable', 'reason': str(error)}
            return original
        digest = hashlib.sha256(build_context(scope.results, generator.max_context_chars).encode()).hexdigest()
        if digest != scope.context_sha256:
            self._request_local.document_scope_audit = {'status': 'unavailable', 'reason': 'source_scope_changed'}
            return original
        trace = {**scope.trace(), 'status': 'inference_started',
                 'initial_retrieved_evidence': [asdict(item) for item in self.last_retrieval]}
        self._request_local.document_scope_audit = trace
        self.last_retrieval = list(scope.results)
        answer = generator.answer(question, list(scope.results), language,
            verified_document_absence=True,
            **({'pdf_documents': list(scope.pdf_documents)} if scope.pdf_documents else {}),
            **self._complete_scope_prompt_context(scope))
        trace.update(status='provider_failure' if answer.provider_failure else 'checked',
                     outcome=answer.reason if answer.abstained else 'found')
        # Physical sources are outside the ordinary retrieval-index cache key.
        # Recheck them on another request instead of persisting these results.
        return replace(answer, source_scope_checked=True)

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
