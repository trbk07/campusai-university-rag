"""Search one or many per-document indexes and preserve chunk provenance."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from collections import OrderedDict
from pathlib import Path
from threading import RLock, local

from .bm25_index import BM25Index
from .dense_index import DenseIndex
from .fusion import reciprocal_rank_fusion
from .reranker import Reranker
from .calibration import RetrievalPolicy
from .contracts import RETRIEVAL_MODES, RETRIEVAL_SCHEMA_VERSION, validate_filters
from .dense_index import IndexNotFoundError
from .routing import RoutingTrace, choose_route, detected_codes
from .negative import negative_query_reason
from .tokenizer_vi import normalize_retrieval_query, normalized_tokens, retrieval_text


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
    rank: int = 1
    raw_score: float | None = None
    fusion_score: float | None = None
    confidence_score: float | None = None
    retriever_ranks: dict[str, int] | None = None
    retriever_sources: tuple[str, ...] = ()
    deduplicated: bool = False
    schema_version: str = RETRIEVAL_SCHEMA_VERSION

    @property
    def page_range(self) -> tuple[int, int]:
        value = self.metadata.get("page_range", [self.page, self.page])
        return int(value[0]), int(value[1])

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id, "doc_id": self.doc_id, "page": self.page,
            "page_range": list(self.page_range), "content": self.content,
            "content_type": self.content_type, "score": self.score,
            "raw_score": self.raw_score, "fusion_score": self.fusion_score,
            "confidence_score": self.confidence_score,
            "retrieval_mode": self.retriever, "rank": self.rank,
            "retriever_ranks": dict(self.retriever_ranks or {}),
            "retriever_sources": list(self.retriever_sources),
            "deduplicated": self.deduplicated, "metadata": dict(self.metadata),
            "schema_version": self.schema_version,
        }


class HybridRetriever:
    def __init__(
        self,
        index_root: str | Path = "data/index",
        rrf_k: int = 3,
        reranker: Reranker | None = None,
        query_cache_size: int = 128,
        rerank_candidate_limit: int = 8,
        candidate_limit: int = 40,
        rrf_weights: tuple[float, float] = (1.0, 1.2),
        policies: dict[str, RetrievalPolicy] | None = None,
    ) -> None:
        self.index_root = Path(index_root)
        self.rrf_k = rrf_k
        self.reranker = reranker
        self.query_cache_size = max(0, query_cache_size)
        self.rerank_candidate_limit = max(1, rerank_candidate_limit)
        self.candidate_limit = max(1, candidate_limit)
        if len(rrf_weights) != 2 or any(weight < 0 for weight in rrf_weights):
            raise ValueError("rrf_weights must contain non-negative BM25 and dense weights")
        self.rrf_weights = tuple(float(weight) for weight in rrf_weights)
        self.policies = dict(policies or {})
        self._indexes: dict[str, tuple[BM25Index, DenseIndex | None]] = {}
        self._query_cache: OrderedDict[tuple, list[RetrievalResult]] = OrderedDict()
        self._trace_cache: dict[tuple, RoutingTrace] = {}
        self._index_lock = RLock()
        self._cache_lock = RLock()
        self._trace_state = local()
        self.last_trace = RoutingTrace(route="uninitialized")

    @property
    def last_trace(self) -> RoutingTrace:
        return getattr(self._trace_state, "value", RoutingTrace(route="uninitialized"))

    @last_trace.setter
    def last_trace(self, value: RoutingTrace) -> None:
        self._trace_state.value = value

    def load_document(self, doc_id: str) -> None:
        root = self.index_root / doc_id
        bm25 = BM25Index.load(root / "bm25.json")
        try:
            dense = DenseIndex.load(root / "dense.json")
        except IndexNotFoundError:
            dense = None
        self._indexes[doc_id] = (bm25, dense)
        self._query_cache.clear()
        self._trace_cache.clear()

    def remove_document(self, doc_id: str) -> None:
        self._indexes.pop(doc_id, None)
        self._query_cache.clear()
        self._trace_cache.clear()

    def _ensure_loaded(self, doc_ids: list[str]) -> None:
        for doc_id in doc_ids:
            if doc_id not in self._indexes:
                with self._index_lock:
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
        total_started = time.perf_counter()
        parse_started = total_started
        if score_threshold is not None and score_threshold < 0:
            raise ValueError("score_threshold must be non-negative")
        if mode not in RETRIEVAL_MODES:
            raise ValueError(f"unsupported retrieval mode: {mode}")
        normalized_filters = validate_filters(filters)
        route = choose_route(query, filters=normalized_filters) if mode == "auto" else mode
        codes = detected_codes(query)
        effective_mode = {
            "filtered_hybrid_rrf": "hybrid_rrf", "exact_course": "exact_code",
        }.get(route, route)
        parse_ms = (time.perf_counter() - parse_started) * 1000
        if doc_ids is None:
            doc_ids = sorted(path.name for path in self.index_root.iterdir() if path.is_dir()) if self.index_root.exists() else []
        if not doc_ids or top_k <= 0:
            self.last_trace = RoutingTrace(route=route, detected_codes=codes, filters_applied=bool(normalized_filters),
                                           abstained=True, latency_ms={"parse": round(parse_ms, 3), "total": round((time.perf_counter()-total_started)*1000, 3)})
            return []
        if not query or not query.strip():
            self.last_trace = RoutingTrace(route="abstain", abstained=True,
                                           latency_ms={"parse": round(parse_ms, 3), "total": round((time.perf_counter()-total_started)*1000, 3)})
            return []
        guard_reason = negative_query_reason(query)
        if guard_reason:
            self.last_trace = RoutingTrace(route="abstain", detected_codes=codes,
                                           filters_applied=bool(normalized_filters), abstained=True,
                                           fallback=guard_reason,
                                           latency_ms={"parse": round(parse_ms, 3),
                                                       "total": round((time.perf_counter()-total_started)*1000, 3)})
            return []
        # A calibrated policy is the production default when supplied by the
        # service. Explicit call-site thresholds remain supported for tests and
        # offline experiments, but cannot silently override a stricter policy.
        policy = self.policies.get(effective_mode) or self.policies.get(mode)
        # An exact route may later prove ambiguous and fall back to hybrid
        # after the selected indexes are inspected. Bind the same calibrated
        # abstention policy up front so the cache key and fallback behavior
        # remain consistent.
        if policy is None and effective_mode == "exact_code":
            policy = self.policies.get("hybrid_rrf")
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
            self.candidate_limit,
            self.rrf_weights,
            getattr(self.reranker, "model_name", None),
        )
        if self.query_cache_size:
            with self._cache_lock:
                cached = self._query_cache.get(cache_key)
                if cached is not None:
                    self._query_cache.move_to_end(cache_key)
                    self.last_trace = self._trace_cache.get(cache_key, self.last_trace)
                    return list(cached)
        self._ensure_loaded(doc_ids)
        search_query = normalize_retrieval_query(query)
        records = self._records(doc_ids)
        eligible_ids = set(records)
        if normalized_filters:
            eligible_ids = {
                item_id for item_id, item in records.items()
                if all(str((item.get("metadata", {}) or {}).get(key, "")).casefold() == str(value).casefold()
                       for key, value in normalized_filters.items())
            }
        primary_code = codes[0] if codes else None
        exact_candidate_ids = {
            item_id for item_id, item in records.items()
            if item_id in eligible_ids and primary_code
            and re.search(rf"(?<![\w]){re.escape(primary_code)}(?![\w])", retrieval_text(item), re.I)
        }
        exact_candidate_documents = {records[item_id].get("doc_id") for item_id in exact_candidate_ids}
        exact_fast_path = (
            effective_mode == "exact_code" and len(codes) == 1
            and len(exact_candidate_documents) == 1 and 0 < len(exact_candidate_ids) <= top_k
        )
        route_fallback = None
        if effective_mode == "exact_code" and exact_candidate_ids and not exact_fast_path:
            # Multiple codes, documents, or more candidates than can safely be
            # returned are ambiguous. Preserve the exact candidate list as an
            # additional ranker, but let BM25+dense resolve the surrounding
            # context instead of choosing a document arbitrarily.
            effective_mode = "hybrid_rrf"
            route_fallback = "ambiguous_exact_code_hybrid_rrf"
        requested_pages = {int(value) for value in re.findall(r"\b(?:page|trang)\s+(\d+)\b", query, re.I)}
        requested_years = set(re.findall(r"\b(?:19|20|21)\d{2}\b", query))
        if requested_years:
            # The corpus contains historical documents whose effective year
            # may live in page text rather than filename metadata. Reject only
            # clearly impossible future years here; exact year filters remain
            # strict and evidence-backed through ``validate_filters``.
            if all(int(year) > 2030 for year in requested_years):
                self.last_trace = RoutingTrace(route=route, detected_codes=codes,
                                               filters_applied=bool(normalized_filters), abstained=True,
                                               fallback="year_not_in_corpus", latency_ms={
                                                   "parse": round(parse_ms, 3),
                                                   "total": round((time.perf_counter()-total_started)*1000, 3)})
                return []
        bm25_ranked, dense_ranked = [], []
        dense_query_vectors: dict[tuple[str, str], list[float]] = {}
        bm25_started = time.perf_counter()
        for doc_id in doc_ids:
            bm25, dense = self._indexes[doc_id]
            # An explicit page constraint is a provenance constraint, not just
            # a ranking hint. Search all chunks in that case so a relevant
            # page cannot disappear before the page filter is applied.
            candidate_top_k = len(bm25.items) if (requested_pages or normalized_filters or effective_mode == "exact_code") else min(self.candidate_limit, max(top_k * 3, 10))
            bm25_ranked.extend(bm25.search(search_query, top_k=candidate_top_k))
        bm25_ms = (time.perf_counter() - bm25_started) * 1000
        dense_started = time.perf_counter()
        for doc_id in doc_ids:
            _bm25, dense = self._indexes[doc_id]
            if dense is None or effective_mode in {"bm25", "exact_code"}:
                continue
            candidate_top_k = len(_bm25.items) if (requested_pages or normalized_filters) else min(self.candidate_limit, max(top_k * 3, 10))
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
        dense_ms = (time.perf_counter() - dense_started) * 1000
        bm25_ranked = [pair for pair in bm25_ranked if pair[0] in eligible_ids]
        dense_ranked = [pair for pair in dense_ranked if pair[0] in eligible_ids]
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
        # Per-document indexes return scores in their own local order. RRF
        # requires one global rank per retriever; concatenating those lists
        # would silently make filesystem/doc-id order a ranking signal. Apply
        # filters first, then globally rank and cap each candidate list.
        bm25_ranked = sorted(bm25_ranked, key=lambda pair: (-pair[1], pair[0]))[: self.candidate_limit]
        dense_ranked = sorted(dense_ranked, key=lambda pair: (-pair[1], pair[0]))[: self.candidate_limit]
        fallback_reason = route_fallback
        fusion_started = time.perf_counter()
        if effective_mode == "exact_code":
            if not exact_candidate_ids:
                self.last_trace = RoutingTrace(route=route, detected_codes=codes, filters_applied=bool(normalized_filters),
                                               bm25_used=True, dense_used=False, abstained=True,
                                               candidate_count=0, final_count=0,
                                               latency_ms={"parse": round(parse_ms, 3), "bm25": round(bm25_ms, 3),
                                                           "dense": 0.0, "fusion": 0.0,
                                                           "total": round((time.perf_counter()-total_started)*1000, 3)})
                return []
            score_by_bm25 = dict(bm25_ranked)
            ranked = sorted(((item_id, score_by_bm25.get(item_id, 1.0)) for item_id in exact_candidate_ids),
                            key=lambda pair: (-pair[1], pair[0]))[:top_k]
            label = "exact_code"
        elif effective_mode == "bm25":
            ranked = sorted(bm25_ranked, key=lambda pair: (-pair[1], pair[0]))[:top_k]
            label = "bm25"
        elif effective_mode == "dense":
            ranked = sorted(dense_ranked, key=lambda pair: (-pair[1], pair[0]))[:top_k]
            label = "dense"
        else:
            available = [bm25_ranked]
            weights = [self.rrf_weights[0]]
            if dense_ranked:
                available.append(dense_ranked)
                weights.append(self.rrf_weights[1])
            else:
                fallback_reason = "dense_unavailable_or_empty"
            if route_fallback and exact_candidate_ids:
                exact_ranked = sorted(
                    ((item_id, dict(bm25_ranked).get(item_id, 0.0)) for item_id in exact_candidate_ids),
                    key=lambda pair: (-pair[1], pair[0]),
                )
                available.append(exact_ranked)
                weights.append(1.0)
            ranked = reciprocal_rank_fusion(available, self.rrf_k, min(self.candidate_limit, top_k * 3), weights)
            label = "hybrid_rrf" if effective_mode == "hybrid_rrf" else "hybrid"
        fusion_ms = (time.perf_counter() - fusion_started) * 1000
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
        # A reranker has its own score space. Apply thresholds after reranking
        # there; applying the dense/RRF threshold first would discard useful
        # candidates before the calibrated confidence is available.
        bm25_scores = dict(bm25_ranked)
        dense_scores = dict(dense_ranked)
        query_terms = {token for token in normalized_tokens(search_query) if len(token) >= 3}
        confidence_scores: dict[str, float] = {}
        for item_id, _score in ranked:
            item_terms = set(normalized_tokens(retrieval_text(records[item_id])))
            lexical = len(query_terms & item_terms) / max(1, len(query_terms))
            dense_support = max(0.0, min(1.0, float(dense_scores.get(item_id, 0.0))))
            agreement = item_id in bm25_scores and item_id in dense_scores
            confidence_scores[item_id] = round(min(1.0, .55 * lexical + .35 * dense_support + (.10 if agreement else 0.0)), 6)
        if effective_mode == "exact_code":
            confidence_scores.update({item_id: 1.0 for item_id, _score in ranked})
        elif route_fallback:
            confidence_scores.update({item_id: max(.8, confidence_scores.get(item_id, 0.0))
                                      for item_id in exact_candidate_ids})
        if score_threshold is not None and not (self.reranker is not None and effective_mode in {"rerank", "hybrid_rerank"}):
            if effective_mode in {"hybrid", "hybrid_rrf"}:
                # Confidence is an abstention decision for the query, not a
                # second ranker. Once at least one candidate establishes that
                # the query is supported by the selected corpus, preserve the
                # complete RRF order and per-result confidence/provenance.
                # Filtering individual chunks here can remove a relevant
                # result at rank 3 merely because rank 1 carried the strongest
                # lexical signal.
                if not ranked or max(confidence_scores.get(item_id, 0.0) for item_id, _score in ranked) < score_threshold:
                    ranked = []
            else:
                ranked = [(item_id, score) for item_id, score in ranked if score >= score_threshold]
        ranked = ranked[:top_k * 3]
        candidates = [
            records[item_id]
            for item_id, _score in ranked[: self.rerank_candidate_limit]
        ]
        # Keep the normal hybrid path cheap. Cross-encoder reranking is an
        # explicit expensive mode so the router can reserve it for Hard
        # questions instead of paying the model-load cost for every query.
        if self.reranker is not None and effective_mode in {"rerank", "hybrid_rerank"}:
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
        bm25_ranks = {item_id: rank for rank, (item_id, _score) in enumerate(bm25_ranked, 1)}
        dense_ranks = {item_id: rank for rank, (item_id, _score) in enumerate(dense_ranked, 1)}
        raw_scores = dict(bm25_ranked if effective_mode in {"bm25", "exact_code"} else dense_ranked if effective_mode == "dense" else [])
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
                rank=rank,
                raw_score=raw_scores.get(item_id),
                fusion_score=float(score_by_id[item_id]) if label in {"hybrid", "hybrid_rrf"} else None,
                confidence_score=confidence_scores.get(item_id),
                retriever_ranks={name: values[item_id] for name, values in (("bm25", bm25_ranks), ("dense", dense_ranks)) if item_id in values},
                retriever_sources=tuple(name for name, values in (("bm25", bm25_ranks), ("dense", dense_ranks)) if item_id in values),
                deduplicated=item_id in bm25_ranks and item_id in dense_ranks,
            )
            for rank, (item_id, _score) in enumerate(ranked, 1)
            if item_id in records
        ][:top_k]
        self.last_trace = RoutingTrace(
            route=route, detected_codes=codes, exact_match=effective_mode == "exact_code" and bool(results),
            filters_applied=bool(normalized_filters), bm25_used=bool(bm25_ranked), dense_used=bool(dense_ranked),
            abstained=not results, fallback=fallback_reason,
            candidate_count=len(set(item_id for item_id, _ in bm25_ranked + dense_ranked)), final_count=len(results),
            latency_ms={"parse": round(parse_ms, 3), "bm25": round(bm25_ms, 3),
                        "dense": round(dense_ms, 3), "fusion": round(fusion_ms, 3),
                        "total": round((time.perf_counter()-total_started)*1000, 3)},
        )
        if self.query_cache_size:
            with self._cache_lock:
                self._query_cache[cache_key] = list(results)
                self._trace_cache[cache_key] = self.last_trace
                self._query_cache.move_to_end(cache_key)
                while len(self._query_cache) > self.query_cache_size:
                    old_key, _ = self._query_cache.popitem(last=False)
                    self._trace_cache.pop(old_key, None)
        return results

    @classmethod
    def with_calibration_report(cls, index_root: str | Path, report_path: str | Path, **kwargs) -> "HybridRetriever":
        """Construct a retriever whose abstention threshold is auditable."""
        policy = RetrievalPolicy.from_report(report_path)
        return cls(index_root, policies={policy.mode: policy}, **kwargs)
