"""Persistent dense retrieval with optional bge-m3 and a deterministic fallback."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .model_runtime import retrieval_runtime
from .tokenizer_vi import normalized_tokens


def _fallback_vector(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in normalized_tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class DenseIndex:
    """Dense index using bge-m3 when available, otherwise hashed vectors."""

    def __init__(
        self,
        items: list[dict] | None = None,
        model_name: str = "fallback-hash-256",
        device: str = "cpu",
        batch_size: int = 8,
    ) -> None:
        self.items = items or []
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.vectors: list[list[float]] = []

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if self.model_name != "fallback-hash-256":
            model = retrieval_runtime().get_encoder(self.model_name, device=self.device)
            return model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            ).tolist()
        return [_fallback_vector(text) for text in texts]

    def build(self, items: list[dict]) -> None:
        self.items = items
        try:
            self.vectors = self._encode([item.get("content", "") for item in items])
        except ImportError:
            # Optional model dependency: use the deterministic offline fallback
            # only while building, never silently while searching a persisted
            # index created with a different embedding model.
            self.model_name = "fallback-hash-256"
            self.vectors = self._encode([item.get("content", "") for item in items])

    def encode_query(self, query: str) -> list[float]:
        return self._encode([query])[0]

    def search(
        self,
        query: str,
        top_k: int = 10,
        query_vector: list[float] | None = None,
    ) -> list[tuple[str, float]]:
        if not self.items:
            return []
        query_vector = query_vector or self.encode_query(query)
        scored = [
            (item["chunk_id"], _cosine(query_vector, vector))
            for item, vector in zip(self.items, self.vectors)
        ]
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:top_k]

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "items": self.items,
            "vectors": self.vectors,
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "DenseIndex":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        index = cls(
            data["items"],
            data.get("model_name", "fallback-hash-256"),
            data.get("device", "cpu"),
            int(data.get("batch_size", 8)),
        )
        index.vectors = data["vectors"]
        return index
