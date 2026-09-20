"""Optional cross-encoder reranker with a safe lexical fallback."""

from __future__ import annotations

from .tokenizer_vi import normalized_tokens


class Reranker:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self.model_name and self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
            except ImportError:
                self.model_name = None
        return self._model

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[tuple[str, float]]:
        if not candidates:
            return []
        model = self._load()
        if model is not None:
            scores = model.predict([(query, item.get("content", "")) for item in candidates])
            ranked = [(item["chunk_id"], float(score)) for item, score in zip(candidates, scores)]
        else:
            query_tokens = set(normalized_tokens(query))
            ranked = []
            for item in candidates:
                tokens = set(normalized_tokens(item.get("content", "")))
                ranked.append((item["chunk_id"], len(query_tokens & tokens) / max(1, len(query_tokens))))
        return sorted(ranked, key=lambda pair: (-pair[1], pair[0]))[:top_k]
