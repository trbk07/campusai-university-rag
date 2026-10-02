"""Query orchestration: route, retrieve, then ground the answer."""

from __future__ import annotations

import hashlib
import json
import re
from threading import local
from ..request_timings import stage, timed_stage
from typing import Any

from ..retrieval.hybrid import HybridRetriever, RetrievalResult
from .cache import RAGAnswerCache, build_rag_cache_key
from .grounding import GroundedAnswer, GroundedAnswerGenerator
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
        """Return a stable version from the selected corpus/index manifests."""

        selected = sorted(doc_ids or [
            path.name for path in self.retriever.index_root.iterdir()
            if path.is_dir() and (path / "dense.json").is_file()
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
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()

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
    ) -> list[RetrievalResult]:
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
    ) -> GroundedAnswer:
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
        )
        with self.metrics.observe("rag.ask"):
            return self._ask_uncached_or_cached(question, doc_ids, filters, top_k, selected_mode, language, version, key)

    def _ask_uncached_or_cached(self, question, doc_ids, filters, top_k, selected_mode, language, version, key):
        self.last_retrieval = []
        cached = self.cache.get(key)
        if cached is not None:
            self.last_cache_hit = True
            return cached
        self.last_cache_hit = False
        # Re-check under the key lock so concurrent identical requests make
        # only one retrieval/LLM call when they share a service instance.
        with self.cache.lock(key):
            cached = self.cache.get(key)
            if cached is not None:
                self.last_cache_hit = True
                return cached
            with stage("retrieval"):
                results = self.retriever.search(
                    retrieval_query(question), doc_ids=doc_ids, filters=filters,
                    top_k=top_k, mode=selected_mode,
                )
            self.last_retrieval = list(results)
            answer = self.answer_generator.answer(question, results, language)
            self.cache.put(key, answer)
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
