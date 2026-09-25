"""Process-wide warm model runtime for low-latency retrieval.

Loading a dense encoder or cross-encoder per request is the dominant avoidable
latency in the current CPU deployment.  This module keeps one model instance
per (kind, model name, device) and serializes first-loads so concurrent requests
do not create duplicate multi-gigabyte model copies.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class RuntimeKey:
    kind: str
    model_name: str
    device: str


class RetrievalModelRuntime:
    """Thread-safe process-wide cache for Sentence Transformers models."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._models: dict[RuntimeKey, Any] = {}

    def get_encoder(self, model_name: str, device: str = "cpu") -> Any:
        key = RuntimeKey("encoder", model_name, device)
        with self._lock:
            if key not in self._models:
                from sentence_transformers import SentenceTransformer

                self._models[key] = SentenceTransformer(model_name, device=device)
            return self._models[key]

    def get_reranker(self, model_name: str, device: str = "cpu") -> Any:
        key = RuntimeKey("reranker", model_name, device)
        with self._lock:
            if key not in self._models:
                from sentence_transformers import CrossEncoder

                self._models[key] = CrossEncoder(model_name, device=device)
            return self._models[key]

    def loaded_models(self) -> list[dict[str, str]]:
        with self._lock:
            return [
                {
                    "kind": key.kind,
                    "model_name": key.model_name,
                    "device": key.device,
                }
                for key in self._models
            ]

    def clear(self) -> None:
        """Release cached models explicitly, primarily for tests/shutdown."""

        with self._lock:
            self._models.clear()


_RUNTIME = RetrievalModelRuntime()


def retrieval_runtime() -> RetrievalModelRuntime:
    """Return the shared runtime used by all indexes in this process."""

    return _RUNTIME


def warm_retrieval_models(
    dense_model: str | None = None,
    reranker_model: str | None = None,
    device: str = "cpu",
    texts: list[str] | None = None,
) -> list[dict[str, str]]:
    """Load configured retrieval models once during application startup."""

    texts = texts or ["course prerequisite and semester registration"]
    runtime = retrieval_runtime()
    # The deterministic fallback encoder is implemented by DenseIndex itself;
    # it is deliberately not sent through Sentence Transformers.
    if dense_model and dense_model != "fallback-hash-256":
        encoder = runtime.get_encoder(dense_model, device=device)
        encoder.encode(texts, batch_size=1, show_progress_bar=False, normalize_embeddings=True)
    if reranker_model:
        reranker = runtime.get_reranker(reranker_model, device=device)
        reranker.predict([["What is the course prerequisite?", texts[0]]], batch_size=1, show_progress_bar=False)
    return runtime.loaded_models()
