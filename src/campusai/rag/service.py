"""Query orchestration: route, retrieve, then ground the answer."""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from threading import local, RLock
from ..request_timings import stage, timed_stage
from typing import Any

from ..retrieval.hybrid import HybridRetriever, RetrievalResult
from ..retrieval.routing import RoutingTrace
from .cache import RAGAnswerCache, build_rag_cache_key
from .grounding import GroundedAnswer, GroundedAnswerGenerator
from .context import resolve_query, authorized_scope
from ..observability import MetricsRegistry
from ..retrieval.canary_rollout import CanaryController, rollback_retriever


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
        doc_ids = authorized_scope(doc_ids, authorized_doc_ids)
        resolved = resolve_query(question, history=history, selected_text=selected_text, requires_context=requires_context)
        self._request_local.context_trace = resolved.cache_context()
        if resolved.needs_clarification:
            self.retriever.last_trace = RoutingTrace(route="abstain", abstained=True, abstention_reason="ambiguous_question")
            return []
        question = resolved.resolved
        selected_mode = self._selected_mode(question, mode, request_id)
        return self.retriever.search(
            question,
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
        selected_mode = self._selected_mode(question, mode, request_id)
        version = corpus_version or self.corpus_version(doc_ids)
        budget = {
            "max_chars": self.answer_generator.max_context_chars,
            "max_tokens": self.answer_generator.max_context_tokens,
            "min_retrieval_score": self.answer_generator.min_retrieval_score,
        }
        if selected_mode == "phase7":
            budget["phase7_retrieval_fingerprint"] = self.retriever.phase7_cache_fingerprint
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
            with stage("retrieval"):
                results = self.retriever.search(
                    retrieval_query(question), doc_ids=doc_ids, filters=filters,
                    top_k=top_k, mode=selected_mode,
                )
            self.last_retrieval = list(results)
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
