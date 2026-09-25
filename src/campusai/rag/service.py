"""Query orchestration: route, retrieve, then ground the answer."""

from __future__ import annotations

from typing import Any

from ..retrieval.hybrid import HybridRetriever, RetrievalResult
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
    ) -> None:
        self.retriever = retriever
        self.answer_generator = answer_generator

    def retrieve(
        self,
        question: str,
        doc_ids: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
        mode: str | None = None,
    ) -> list[RetrievalResult]:
        selected_mode = mode or choose_query_mode(
            question,
            reranker_available=self.retriever.reranker is not None,
        )
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
    ) -> GroundedAnswer:
        results = self.retrieve(question, doc_ids, filters, top_k, mode)
        return self.answer_generator.answer(question, results, language)
