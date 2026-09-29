"""Search one or many per-document indexes and preserve chunk provenance."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from collections import OrderedDict
from pathlib import Path

from .bm25_index import BM25Index
from .dense_index import DenseIndex
from .fusion import reciprocal_rank_fusion
from .reranker import Reranker
from .calibration import RetrievalPolicy
from .tokenizer_vi import normalize_retrieval_query


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
    def __init__(
        self,
        index_root: str | Path = "data/index",
        rrf_k: int = 60,
        reranker: Reranker | None = None,
        query_cache_size: int = 128,
        rerank_candidate_limit: int = 8,
        policies: dict[str, RetrievalPolicy] | None = None,
    ) -> None:
        self.index_root = Path(index_root)
        self.rrf_k = rrf_k
        self.reranker = reranker
        self.query_cache_size = max(0, query_cache_size)
        self.rerank_candidate_limit = max(1, rerank_candidate_limit)
        self.policies = dict(policies or {})
        self._indexes: dict[str, tuple[BM25Index, DenseIndex]] = {}
        self._query_cache: OrderedDict[tuple, list[RetrievalResult]] = OrderedDict()

    def load_document(self, doc_id: str) -> None:
        root = self.index_root / doc_id
        self._indexes[doc_id] = (BM25Index.load(root / "bm25.json"), DenseIndex.load(root / "dense.json"))
        self._query_cache.clear()

    def remove_document(self, doc_id: str) -> None:
        self._indexes.pop(doc_id, None)
        self._query_cache.clear()

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

    def search(self, query: str, doc_ids: list[str] | None = None, filters: dict | None = None, top_k: int = 5, mode: str = "hybrid", score_threshold: float | None = None) -> list[RetrievalResult]:
        if score_threshold is not None and score_threshold < 0:
            raise ValueError("score_threshold must be non-negative")
        if doc_ids is None:
            doc_ids = sorted(path.name for path in self.index_root.iterdir() if path.is_dir()) if self.index_root.exists() else []
        if not doc_ids or top_k <= 0:
            return []
        if not query or not query.strip():
            return []
        # A calibrated policy is the production default when supplied by the
        # service. Explicit call-site thresholds remain supported for tests and
        # offline experiments, but cannot silently override a stricter policy.
        policy = self.policies.get(mode)
        if policy is not None:
            score_threshold = max(score_threshold or 0.0, policy.threshold)
        # JSON keeps nested filter values hashable and deterministic, so a UI
        # filter payload cannot crash the fast path before retrieval starts.
        filter_key = json.dumps(filters or {}, sort_keys=True, ensure_ascii=False, default=str)
        cache_key = (
            query,
            tuple(sorted(doc_ids)),
            filter_key,
            top_k,
            mode,
            score_threshold,
            self.rrf_k,
            self.rerank_candidate_limit,
            getattr(self.reranker, "model_name", None),
        )
        if self.query_cache_size:
            cached = self._query_cache.get(cache_key)
            if cached is not None:
                self._query_cache.move_to_end(cache_key)
                return list(cached)
        self._ensure_loaded(doc_ids)
        search_query = normalize_retrieval_query(query)
        records = self._records(doc_ids)
        requested_pages = {int(value) for value in re.findall(r"\b(?:page|trang)\s+(\d+)\b", query, re.I)}
        bm25_ranked, dense_ranked = [], []
        dense_query_vectors: dict[tuple[str, str], list[float]] = {}
        for doc_id in doc_ids:
            bm25, dense = self._indexes[doc_id]
            # An explicit page constraint is a provenance constraint, not just
            # a ranking hint. Search all chunks in that case so a relevant
            # page cannot disappear before the page filter is applied.
            candidate_top_k = len(bm25.items) if requested_pages else max(top_k * 3, 10)
            bm25_ranked.extend(bm25.search(search_query, top_k=candidate_top_k))
            vector_key = (dense.model_name, dense.device)
            query_vector = dense_query_vectors.get(vector_key)
            if query_vector is None:
                query_vector = dense.encode_query(search_query)
                dense_query_vectors[vector_key] = query_vector
            dense_ranked.extend(
                dense.search(
                    search_query,
                    top_k=candidate_top_k,
                    query_vector=query_vector,
                )
            )
        source_hints = [
            token.casefold() for token in re.findall(r"(?<!\w)[A-Za-z0-9]+_[A-Za-z0-9_.-]+|(?<!\w)[0-9a-f]{64}(?!\w)", query)
        ]
        if source_hints:
            source_ids = {
                item_id for item_id, item in records.items()
                if any(hint in " ".join((str(item.get("doc_id", "")), str((item.get("metadata", {}) or {}).get("source_name", "")))).casefold()
                       for hint in source_hints)
            }
            if source_ids:
                bm25_ranked = [pair for pair in bm25_ranked if pair[0] in source_ids]
                dense_ranked = [pair for pair in dense_ranked if pair[0] in source_ids]
        if requested_pages:
            requested_ids = {
                item_id for item_id, item in records.items()
                if int(item.get("page", 0)) in requested_pages
                or any(
                    start <= requested_page <= end
                    for requested_page in requested_pages
                    for start, end in [tuple(item.get("page_range", [item.get("page", 0), item.get("page", 0)]))]
                )
            }
            if source_hints:
                requested_ids = {
                    item_id for item_id in requested_ids
                    if any(
                        hint in " ".join((str(records[item_id].get("doc_id", "")), str((records[item_id].get("metadata", {}) or {}).get("source_name", "")))).casefold()
                        for hint in source_hints
                    )
                }
            if requested_ids:
                bm25_ranked = [pair for pair in bm25_ranked if pair[0] in requested_ids]
                dense_ranked = [pair for pair in dense_ranked if pair[0] in requested_ids]
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
        # Benchmark/runtime queries may carry an explicit source anchor (for
        # example ``uet_cs_progression``).  Treat that provenance token as a
        # hard ranking signal so a generic title from another version cannot
        # outrank the requested document merely because it shares common
        # academic words.
        if source_hints:
            def source_boost(pair):
                item_id, score = pair
                item = records[item_id]
                metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
                source_text = " ".join((str(item.get("doc_id", "")), str(metadata.get("source_name", "")))).casefold()
                return (100.0 if any(hint in source_text for hint in source_hints) else 0.0, score, item_id)
            ranked.sort(key=lambda pair: (-source_boost(pair)[0], -source_boost(pair)[1], source_boost(pair)[2]))
        if requested_pages:
            # An explicit page constraint is stronger than a small fusion
            # score difference: prefer that page, while preserving score order
            # among chunks on the same page.
            def page_priority(pair):
                item_id, score = pair
                item = records[item_id]
                metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
                source_text = " ".join((str(item.get("doc_id", "")), str(metadata.get("source_name", "")))).casefold()
                source_match = bool(source_hints and any(hint in source_text for hint in source_hints))
                return (
                    0 if int(item.get("page", 0)) in requested_pages else 1,
                    0 if source_match else 1,
                    -score,
                    item_id,
                )
            ranked.sort(key=page_priority)
        if filters:
            ranked = [
                (item_id, score)
                for item_id, score in ranked
                if all(records[item_id].get("metadata", {}).get(key) == value for key, value in filters.items())
            ]
        # A reranker has its own score space. Apply thresholds after reranking
        # there; applying the dense/RRF threshold first would discard useful
        # candidates before the calibrated confidence is available.
        if score_threshold is not None and not (self.reranker is not None and mode in {"rerank", "hybrid_rerank"}):
            ranked = [(item_id, score) for item_id, score in ranked if score >= score_threshold]
        ranked = ranked[:top_k * 3]
        candidates = [
            records[item_id]
            for item_id, _score in ranked[: self.rerank_candidate_limit]
        ]
        # Keep the normal hybrid path cheap. Cross-encoder reranking is an
        # explicit expensive mode so the router can reserve it for Hard
        # questions instead of paying the model-load cost for every query.
        if self.reranker is not None and mode in {"rerank", "hybrid_rerank"}:
            try:
                reranked = self.reranker.rerank(query, candidates, top_k)
            except Exception:
                # Keep the interactive API alive if an injected/remote
                # reranker fails. The fused ranking is still valid evidence.
                ranked = ranked[:top_k]
                if score_threshold is not None:
                    ranked = [(item_id, score) for item_id, score in ranked if score >= score_threshold]
                score_by_id = dict(ranked)
                label = "hybrid"
            else:
                score_by_id = dict(reranked)
                ranked = reranked
                label = "hybrid_rerank"
                if score_threshold is not None:
                    ranked = [(item_id, score) for item_id, score in ranked if score >= score_threshold]
        else:
            ranked = ranked[:top_k]
            score_by_id = dict(ranked)
        results = [
            RetrievalResult(
                item_id,
                records[item_id]["doc_id"],
                records[item_id].get("page", 0),
                records[item_id].get("content", ""),
                records[item_id].get("content_type", "text"),
                float(score_by_id[item_id]),
                label,
                records[item_id].get("metadata", {}),
            )
            for item_id, _score in ranked
            if item_id in records
        ][:top_k]
        if self.query_cache_size:
            self._query_cache[cache_key] = list(results)
            self._query_cache.move_to_end(cache_key)
            while len(self._query_cache) > self.query_cache_size:
                self._query_cache.popitem(last=False)
        return results

    @classmethod
    def with_calibration_report(cls, index_root: str | Path, report_path: str | Path, **kwargs) -> "HybridRetriever":
        """Construct a retriever whose abstention threshold is auditable."""
        policy = RetrievalPolicy.from_report(report_path)
        return cls(index_root, policies={policy.mode: policy}, **kwargs)
