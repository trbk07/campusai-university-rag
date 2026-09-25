"""Optional cross-encoder reranker with a safe lexical fallback."""

from __future__ import annotations

import logging

from .model_runtime import retrieval_runtime
from .tokenizer_vi import normalized_tokens


log = logging.getLogger(__name__)


class Reranker:
    def __init__(
        self,
        model_name: str | None = None,
        device: str = "cpu",
        batch_size: int = 8,
        max_candidates: int = 8,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_candidates = max_candidates

    def _load(self):
        if self.model_name:
            try:
                return retrieval_runtime().get_reranker(self.model_name, device=self.device)
            except ImportError:
                self.model_name = None
        return None

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[tuple[str, float]]:
        if not candidates:
            return []
        candidates = candidates[: self.max_candidates]
        model = self._load()
        if model is not None:
            try:
                scores = model.predict(
                    [(query, item.get("content", "")) for item in candidates],
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                )
                ranked = [(item["chunk_id"], float(score)) for item, score in zip(candidates, scores)]
            except Exception as error:
                # A remote/model failure must not turn a hard query into a 5xx.
                # Keep the same deterministic lexical fallback used when the
                # optional model dependency is unavailable.
                log.warning("reranker failed; using lexical fallback: %s", error)
                ranked = self._lexical_scores(query, candidates)
        else:
            ranked = self._lexical_scores(query, candidates)
        return sorted(ranked, key=lambda pair: (-pair[1], pair[0]))[:top_k]

    @staticmethod
    def _lexical_scores(query: str, candidates: list[dict]) -> list[tuple[str, float]]:
        query_tokens = set(normalized_tokens(query))
        return [
            (
                item["chunk_id"],
                len(query_tokens & set(normalized_tokens(item.get("content", ""))))
                / max(1, len(query_tokens)),
            )
            for item in candidates
        ]
