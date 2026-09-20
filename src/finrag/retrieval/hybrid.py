"""Search one or many per-document indexes and preserve chunk provenance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .bm25_index import BM25Index
from .dense_index import DenseIndex
from .fusion import reciprocal_rank_fusion
from .reranker import Reranker


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    doc_id: str
    page: int
    content: str
    content_type: str
    score: float
    retriever: str
    metadata: dict


class HybridRetriever:
    def __init__(self, index_root: str | Path = "data/index", rrf_k: int = 60, reranker: Reranker | None = None) -> None:
        self.index_root = Path(index_root)
        self.rrf_k = rrf_k
        self.reranker = reranker
        self._indexes: dict[str, tuple[BM25Index, DenseIndex]] = {}

    def load_document(self, doc_id: str) -> None:
        root = self.index_root / doc_id
        self._indexes[doc_id] = (BM25Index.load(root / "bm25.json"), DenseIndex.load(root / "dense.json"))

    def remove_document(self, doc_id: str) -> None:
        self._indexes.pop(doc_id, None)

    def _ensure_loaded(self, doc_ids: list[str]) -> None:
        for doc_id in doc_ids:
            if doc_id not in self._indexes:
                self.load_document(doc_id)

    def _records(self, doc_ids: list[str]) -> dict[str, dict]:
        records = {}
        for doc_id in doc_ids:
            bm25, _dense = self._indexes[doc_id]
            for item in bm25.items:
                chunk_id = item["chunk_id"]
                if chunk_id in records and records[chunk_id].get("doc_id") != doc_id:
                    raise ValueError(f"Duplicate chunk_id across documents: {chunk_id}")
                records[chunk_id] = item
        return records

    def search(self, query: str, doc_ids: list[str] | None = None, filters: dict | None = None, top_k: int = 5, mode: str = "hybrid") -> list[RetrievalResult]:
        if doc_ids is None:
            doc_ids = sorted(path.name for path in self.index_root.iterdir() if path.is_dir()) if self.index_root.exists() else []
        if not doc_ids or top_k <= 0:
            return []
        self._ensure_loaded(doc_ids)
        records = self._records(doc_ids)
        bm25_ranked, dense_ranked = [], []
        for doc_id in doc_ids:
            bm25, dense = self._indexes[doc_id]
            bm25_ranked.extend(bm25.search(query, top_k=max(top_k * 3, 10)))
            dense_ranked.extend(dense.search(query, top_k=max(top_k * 3, 10)))
        if mode == "bm25":
            ranked = sorted(bm25_ranked, key=lambda pair: (-pair[1], pair[0]))[:top_k]
            label = "bm25"
        elif mode == "dense":
            ranked = sorted(dense_ranked, key=lambda pair: (-pair[1], pair[0]))[:top_k]
            label = "dense"
        else:
            ranked = reciprocal_rank_fusion([bm25_ranked, dense_ranked], self.rrf_k, top_k * 3)
            label = "hybrid"
        ranked = [(item_id, score) for item_id, score in ranked if item_id in records]
        if filters:
            ranked = [
                (item_id, score)
                for item_id, score in ranked
                if all(records[item_id].get("metadata", {}).get(key) == value for key, value in filters.items())
            ]
        ranked = ranked[:top_k * 3]
        candidates = [records[item_id] for item_id, _score in ranked]
        if self.reranker is not None and mode in {"hybrid", "rerank", "hybrid_rerank"}:
            reranked = self.reranker.rerank(query, candidates, top_k)
            score_by_id = dict(reranked)
            ranked = reranked
            label = "hybrid_rerank"
        else:
            ranked = ranked[:top_k]
            score_by_id = dict(ranked)
        return [
            RetrievalResult(item_id, records[item_id]["doc_id"], records[item_id]["page"], records[item_id]["content"], records[item_id]["content_type"], float(score_by_id[item_id]), label, records[item_id].get("metadata", {}))
            for item_id, _score in ranked
            if item_id in records
        ][:top_k]
