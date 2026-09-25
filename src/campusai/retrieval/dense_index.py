"""Persistent dense retrieval with versioned providers and fail-closed loading."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Protocol

from .model_runtime import retrieval_runtime
from .tokenizer_vi import normalized_tokens

SCHEMA_VERSION = 2
HASH_MODEL = "fallback-hash-256"


class IndexErrorBase(RuntimeError):
    """Base class for persisted-index failures."""


class IndexNotFoundError(IndexErrorBase):
    pass


class IndexCorruptError(IndexErrorBase):
    pass


class IndexVersionMismatchError(IndexErrorBase):
    pass


class IndexCorpusMismatchError(IndexErrorBase):
    pass


class EmbeddingProvider(Protocol):
    name: str
    version: str
    dimension: int

    def encode_documents(self, texts: list[str]) -> list[list[float]]: ...
    def encode_query(self, text: str) -> list[float]: ...


def _fallback_vector(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in normalized_tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        vector[int.from_bytes(digest, "big") % dimensions] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class HashEmbeddingProvider:
    name = HASH_MODEL
    version = "1"
    dimension = 256

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return [_fallback_vector(text, self.dimension) for text in texts]

    def encode_query(self, text: str) -> list[float]:
        return _fallback_vector(text, self.dimension)


class SentenceTransformerEmbeddingProvider:
    """Lazy model provider; it never silently degrades to hash."""

    name = "sentence-transformers"

    def __init__(self, model_name: str, device: str = "cpu", batch_size: int = 8, version: str = "runtime") -> None:
        self.model_name, self.device, self.batch_size, self.version = model_name, device, batch_size, version
        self._model = None
        self.dimension = 0

    def _encoder(self):
        if self._model is None:
            self._model = retrieval_runtime().get_encoder(self.model_name, device=self.device)
            probe = self._model.encode(["dimension probe"], normalize_embeddings=True)
            self.dimension = len(probe[0])
        return self._model

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        result = self._encoder().encode(texts, batch_size=self.batch_size, show_progress_bar=False, normalize_embeddings=True)
        return result.tolist()

    def encode_query(self, text: str) -> list[float]:
        return self.encode_documents([text])[0]


def _canonical_items(items: list[dict]) -> str:
    stable = []
    for item in items:
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        stable.append({"chunk_id": item.get("chunk_id"), "doc_id": item.get("doc_id"),
                       "content": item.get("content", ""), "page": item.get("page"),
                       "page_range": item.get("page_range"), "content_type": item.get("content_type"),
                       "table_id": metadata.get("table_id")})
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def corpus_hash(items: list[dict]) -> str:
    return hashlib.sha256(_canonical_items(items).encode("utf-8")).hexdigest()


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class DenseIndex:
    """Dense index using an explicit provider and validated persistence."""

    def __init__(self, items: list[dict] | None = None, model_name: str = HASH_MODEL,
                 device: str = "cpu", batch_size: int = 8, model_revision: str = "1") -> None:
        self.items, self.model_name, self.device = items or [], model_name, device
        self.batch_size, self.model_revision = batch_size, model_revision
        self.vectors: list[list[float]] = []
        self.manifest: dict[str, Any] = {}
        self._provider_cache: EmbeddingProvider | None = None

    def _provider(self) -> EmbeddingProvider:
        if self._provider_cache is not None:
            return self._provider_cache
        if self.model_name == HASH_MODEL:
            self._provider_cache = HashEmbeddingProvider()
        else:
            self._provider_cache = SentenceTransformerEmbeddingProvider(self.model_name, self.device, self.batch_size, self.model_revision)
        return self._provider_cache

    def _encode(self, texts: list[str]) -> list[list[float]]:
        return self._provider().encode_documents(texts)

    def build(self, items: list[dict], *, corpus_id: str | None = None, document_id: str | None = None) -> None:
        started = time.perf_counter()
        self.items = list(items)
        self.vectors = self._encode([item.get("content", "") for item in self.items])
        dimension = len(self.vectors[0]) if self.vectors else (256 if self.model_name == HASH_MODEL else 0)
        self.manifest = self._make_manifest(corpus_id, document_id, dimension, time.perf_counter() - started, corpus_hash(self.items))

    def _make_manifest(self, corpus_id, document_id, dimension, build_seconds, content_fingerprint) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "index_type": "dense", "corpus_id": corpus_id or "default",
                "corpus_hash": content_fingerprint, "document_id": document_id, "model_name": self.model_name,
                "model_revision": self.model_revision, "provider": "hash" if self.model_name == HASH_MODEL else "sentence-transformers",
                "embedding_dimension": dimension, "metric": "cosine", "normalized": True, "item_count": len(self.items),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "build_seconds": build_seconds,
                "content_fingerprint": content_fingerprint, "format": "json"}

    def encode_query(self, query: str) -> list[float]:
        return self._provider().encode_query(query)

    def search(self, query: str, top_k: int = 10, query_vector: list[float] | None = None) -> list[tuple[str, float]]:
        if not self.items:
            return []
        query_vector = query_vector or self.encode_query(query)
        if len(query_vector) != len(self.vectors[0]):
            raise IndexVersionMismatchError("query embedding dimension does not match index")
        scored = [(item["chunk_id"], _cosine(query_vector, vector)) for item, vector in zip(self.items, self.vectors)]
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:top_k]

    def to_dict(self) -> dict:
        manifest = self.manifest or self._make_manifest(None, None, len(self.vectors[0]) if self.vectors else 256, None, corpus_hash(self.items))
        return {"manifest": manifest, "model_name": self.model_name, "model_revision": self.model_revision,
                "device": self.device, "batch_size": self.batch_size, "items": self.items, "vectors": self.vectors}

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload["checksum"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        fd, temporary_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, target)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    @classmethod
    def load(cls, path: str | Path, *, expected_model_name: str | None = None,
             expected_model_revision: str | None = None, expected_corpus_hash: str | None = None,
             expected_schema_version: int = SCHEMA_VERSION) -> "DenseIndex":
        target = Path(path)
        if not target.exists():
            raise IndexNotFoundError(str(target))
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IndexCorruptError(f"cannot parse dense index: {target}") from error
        checksum = data.pop("checksum", None)
        actual = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if not checksum or checksum != actual:
            raise IndexCorruptError("dense index checksum mismatch")
        manifest = data.get("manifest")
        required = {"schema_version", "model_name", "model_revision", "embedding_dimension", "item_count", "corpus_hash"}
        if not isinstance(manifest, dict) or not required.issubset(manifest):
            raise IndexCorruptError("dense index manifest is incomplete")
        if manifest["schema_version"] != expected_schema_version:
            raise IndexVersionMismatchError("unsupported dense index schema")
        if expected_model_name and manifest["model_name"] != expected_model_name:
            raise IndexVersionMismatchError("dense index model mismatch")
        if expected_model_revision and manifest["model_revision"] != expected_model_revision:
            raise IndexVersionMismatchError("dense index model revision mismatch")
        if expected_corpus_hash and manifest["corpus_hash"] != expected_corpus_hash:
            raise IndexCorpusMismatchError("dense index corpus mismatch")
        items, vectors = data.get("items"), data.get("vectors")
        if not isinstance(items, list) or not isinstance(vectors, list) or len(items) != len(vectors):
            raise IndexCorruptError("items and vectors must have equal lengths")
        if int(manifest["item_count"]) != len(items) or manifest["corpus_hash"] != corpus_hash(items):
            raise IndexCorruptError("dense index content fingerprint mismatch")
        dimension = int(manifest["embedding_dimension"])
        if any(not isinstance(vector, list) or len(vector) != dimension for vector in vectors):
            raise IndexCorruptError("vector dimension mismatch")
        index = cls(items, data.get("model_name", HASH_MODEL), data.get("device", "cpu"), int(data.get("batch_size", 8)), data.get("model_revision", "1"))
        index.vectors, index.manifest = vectors, manifest
        return index
