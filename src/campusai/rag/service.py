"""Query orchestration: route, retrieve, then ground the answer."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..retrieval.hybrid import HybridRetriever, RetrievalResult
from .cache import RAGAnswerCache, build_rag_cache_key
from .grounding import GroundedAnswer, GroundedAnswerGenerator


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


class CampusAIQueryService:
    """Public application service used by a future web/API adapter."""

    def __init__(
        self,
        retriever: HybridRetriever,
        answer_generator: GroundedAnswerGenerator,
        cache: RAGAnswerCache | None = None,
    ) -> None:
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.cache = cache if cache is not None else RAGAnswerCache()
        self.last_cache_hit = False

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

    def _selected_mode(self, question: str, mode: str | None) -> str:
        return mode or choose_query_mode(question, reranker_available=self.retriever.reranker is not None)

    def retrieve(
        self,
        question: str,
        doc_ids: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        mode: str | None = None,
    ) -> list[RetrievalResult]:
        selected_mode = self._selected_mode(question, mode)
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
    ) -> GroundedAnswer:
        selected_mode = self._selected_mode(question, mode)
        version = corpus_version or self.corpus_version(doc_ids)
        budget = {
            "max_chars": self.answer_generator.max_context_chars,
            "max_tokens": self.answer_generator.max_context_tokens,
            "min_retrieval_score": self.answer_generator.min_retrieval_score,
        }
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
            results = self.retrieve(question, doc_ids, filters, top_k, selected_mode)
            answer = self.answer_generator.answer(question, results, language)
            self.cache.put(key, answer)
            return answer

    def close(self) -> None:
        self.cache.close()
