"""Search one or many per-document indexes and preserve chunk provenance."""

from __future__ import annotations

import json
import hashlib
import math
import re
import time
from dataclasses import dataclass, replace
from collections import OrderedDict
from pathlib import Path
from threading import RLock, local

from .bm25_index import BM25Index
from .dense_index import DenseIndex
from .fusion import reciprocal_rank_fusion
from .reranker import Reranker
from .calibration import CalibrationError, RetrievalPolicy
from .confidence import LEGACY_CONFIDENCE_MODEL
from .contracts import RETRIEVAL_MODES, RETRIEVAL_SCHEMA_VERSION, validate_filters
from .dense_index import IndexNotFoundError
from .routing import RoutingTrace, choose_route, detected_codes
from .negative import negative_query_reason
from .rerank_policy import Phase7Policy
from .cross_encoder_provider import RerankCandidate, RerankerProvider, RerankerUnavailable
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
    confidence_features: dict[str, float] | None = None
    retriever_ranks: dict[str, int] | None = None
    retriever_sources: tuple[str, ...] = ()
    deduplicated: bool = False
    reranker_score: float | None = None
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
            "confidence_features": dict(self.confidence_features or {}),
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
        phase7_provider: RerankerProvider | None = None,
        phase7_policy: Phase7Policy | None = None,
        phase7_enabled: bool = False,
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
        self.phase7_provider = phase7_provider
        self.phase7_policy = phase7_policy
        self.phase7_enabled = phase7_enabled
        self.phase7_activation_reason = "active" if phase7_enabled else "feature_disabled"
        if phase7_enabled and (phase7_provider is None or phase7_policy is None
                               or "hybrid_rrf" not in self.policies):
            raise ValueError("Phase 7 requires a provider, calibrated policy and Phase 6 hybrid policy")
        if phase7_enabled and phase7_policy.model_identity_sha256 != phase7_provider.model_identity.fingerprint:
            raise ValueError("Phase 7 provider/calibration identity mismatch")
        if phase7_enabled and (self.rrf_k != 3 or self.rrf_weights != (1.0, 1.2)
                               or self.candidate_limit != 40):
            raise ValueError("Phase 7 requires the frozen Phase 6 candidate-generation settings")
        self._indexes: dict[str, tuple[BM25Index, DenseIndex | None]] = {}
        self._index_generations: dict[str, tuple] = {}
        self._postings: dict[str, dict[str, dict[str, set[str]]]] = {}
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
        postings: dict[str, dict[str, set[str]]] = {}
        for item in bm25.items:
            item_id = item["chunk_id"]
            metadata = item.get("metadata", {}) or {}
            for key in ("institution", "program", "course_code", "academic_year",
                        "semester", "document_type", "language"):
                value = metadata.get(key)
                if value is not None:
                    postings.setdefault(key, {}).setdefault(str(value).casefold(), set()).add(item_id)
            page_range = item.get("page_range", [item.get("page", 0), item.get("page", 0)])
            for page in range(int(page_range[0]), int(page_range[1]) + 1):
                postings.setdefault("page", {}).setdefault(str(page), set()).add(item_id)
            years = set(re.findall(r"\b(?:19|20|21)\d{2}\b", str(item.get("content", ""))))
            years.update(re.findall(r"\b(?:19|20|21)\d{2}\b", str(metadata.get("academic_year", ""))))
            for year in years:
                postings.setdefault("mentioned_year", {}).setdefault(year, set()).add(item_id)
        self._postings[doc_id] = postings
        self._index_generations[doc_id] = self._generation(doc_id)
        self._query_cache.clear()
        self._trace_cache.clear()

    def remove_document(self, doc_id: str) -> None:
        self._indexes.pop(doc_id, None)
        self._postings.pop(doc_id, None)
        self._index_generations.pop(doc_id, None)
        self._query_cache.clear()
        self._trace_cache.clear()

    def _ensure_loaded(self, doc_ids: list[str]) -> None:
        for doc_id in doc_ids:
            if doc_id not in self._indexes or self._index_generations.get(doc_id) != self._generation(doc_id):
                with self._index_lock:
                    if doc_id not in self._indexes or self._index_generations.get(doc_id) != self._generation(doc_id):
                        self.load_document(doc_id)

    def _generation(self, doc_id: str) -> tuple:
        root = self.index_root / doc_id
        return tuple((path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None
                     for path in (root / "bm25.json", root / "dense.json"))

    def _records(self, doc_ids: list[str], eligible_ids: set[str] | None = None) -> dict[str, dict]:
        records = {}
        for doc_id in doc_ids:
            bm25, _dense = self._indexes[doc_id]
            for item in bm25.items:
                chunk_id = item["chunk_id"]
                if eligible_ids is not None and chunk_id not in eligible_ids:
                    continue
                if chunk_id in records and records[chunk_id].get("doc_id") != doc_id:
                    raise ValueError(f"Duplicate chunk_id across documents: {chunk_id}")
                records[chunk_id] = item
        return records

    def search(self, query: str, doc_ids: list[str] | None = None, filters: dict | None = None, top_k: int = 5, mode: str = "hybrid", score_threshold: float | None = None) -> list[RetrievalResult]:
        if mode == "phase7":
            return self.search_phase7(query, doc_ids=doc_ids, filters=filters,
                                      top_k=top_k, score_threshold=score_threshold)
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
                                           abstained=True, abstention_reason="no_candidate", latency_ms={"parse": round(parse_ms, 3), "total": round((time.perf_counter()-total_started)*1000, 3)})
            return []
        if not query or not query.strip():
            self.last_trace = RoutingTrace(route="abstain", abstained=True, abstention_reason="empty_query",
                                           latency_ms={"parse": round(parse_ms, 3), "total": round((time.perf_counter()-total_started)*1000, 3)})
            return []
        guard_reason = negative_query_reason(query)
        if guard_reason:
            self.last_trace = RoutingTrace(route="abstain", detected_codes=codes,
                                           filters_applied=bool(normalized_filters), abstained=True,
                                           fallback=guard_reason, abstention_reason="negative_query_policy",
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
        confidence_model = policy.confidence_model if policy is not None else LEGACY_CONFIDENCE_MODEL
        self._ensure_loaded(doc_ids)
        corpus_manifest = self.index_root / "manifest.json"
        corpus_fingerprint = (hashlib.sha256(corpus_manifest.read_bytes()).hexdigest()
                              if corpus_manifest.is_file() else None)
        if policy is not None and policy.index_sha256 and policy.index_sha256 != corpus_fingerprint:
            raise CalibrationError("calibration index fingerprint mismatch")
        # JSON keeps nested filter values hashable and deterministic, so a UI
        # filter payload cannot crash the fast path before retrieval starts.
        filter_key = json.dumps(filters or {}, sort_keys=True, ensure_ascii=False, default=str)
        query_plan_hash = hashlib.sha256(json.dumps(
            {"query": query, "doc_ids": sorted(doc_ids), "filters": filter_key,
             "top_k": top_k, "mode": mode}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        cache_key = (
            query_plan_hash,
            tuple((doc_id, self._index_generations[doc_id]) for doc_id in sorted(doc_ids)),
            corpus_fingerprint,
            score_threshold,
            confidence_model.fingerprint,
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
        search_query = normalize_retrieval_query(query)
        requested_years = set(re.findall(r"\b(?:19|20|21)\d{2}\b", query))
        if requested_years and not any(
            self._postings[doc_id].get("mentioned_year", {}).get(year)
            for doc_id in doc_ids for year in requested_years
        ):
            self.last_trace = RoutingTrace(
                route=route, detected_codes=codes, filters_applied=bool(normalized_filters),
                abstained=True, abstention_reason="negative_query_policy", fallback="year_not_in_corpus",
                latency_ms={"parse": round(parse_ms, 3),
                            "total": round((time.perf_counter() - total_started) * 1000, 3)},
            )
            return []
        eligible_ids: set[str] | None = None
        if normalized_filters:
            for key, value in normalized_filters.items():
                matches = {item_id for doc_id in doc_ids
                           for item_id in self._postings[doc_id].get(key, {}).get(str(value).casefold(), set())}
                eligible_ids = matches if eligible_ids is None else eligible_ids & matches
        requested_pages = {int(value) for value in re.findall(r"\b(?:page|trang)\s+(\d+)\b", query, re.I)}
        if requested_pages:
            page_ids = {
                item_id for doc_id in doc_ids for page in requested_pages
                for item_id in self._postings[doc_id].get("page", {}).get(str(page), set())
            }
            if page_ids:
                eligible_ids = page_ids if eligible_ids is None else eligible_ids & page_ids
        records = self._records(doc_ids, eligible_ids)
        if eligible_ids is None:
            eligible_ids = set(records)
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
        bm25_ranked, dense_ranked = [], []
        dense_query_vectors: dict[tuple[str, str], list[float]] = {}
        bm25_started = time.perf_counter()
        for doc_id in doc_ids:
            bm25, dense = self._indexes[doc_id]
            candidate_top_k = min(self.candidate_limit, max(top_k * 3, 10))
            bm25_ranked.extend(bm25.search(search_query, top_k=candidate_top_k, eligible_ids=eligible_ids))
        bm25_ms = (time.perf_counter() - bm25_started) * 1000
        dense_started = time.perf_counter()
        for doc_id in doc_ids:
            _bm25, dense = self._indexes[doc_id]
            if dense is None or effective_mode in {"bm25", "exact_code"}:
                continue
            candidate_top_k = min(self.candidate_limit, max(top_k * 3, 10))
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
                    eligible_ids=eligible_ids,
                )
            )
        dense_ms = (time.perf_counter() - dense_started) * 1000
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
                                               abstention_reason="no_candidate",
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
        if requested_pages:
            # An explicit page constraint is stronger than a small fusion
            # score difference: prefer that page, while preserving score order
            # among chunks on the same page.
            def page_priority(pair):
                item_id, score = pair
                item = records[item_id]
                return (
                    0 if int(item.get("page", 0)) in requested_pages else 1,
                    -score,
                    item_id,
                )
            ranked.sort(key=page_priority)
        # A reranker has its own score space. Apply thresholds after reranking
        # there; applying the dense/RRF threshold first would discard useful
        # candidates before the calibrated confidence is available.
        bm25_scores = dict(bm25_ranked)
        dense_scores = dict(dense_ranked)
        bm25_ranks = {item_id: rank for rank, (item_id, _score) in enumerate(bm25_ranked, 1)}
        dense_ranks = {item_id: rank for rank, (item_id, _score) in enumerate(dense_ranked, 1)}
        query_terms = {token for token in normalized_tokens(search_query) if len(token) >= 3}
        confidence_scores: dict[str, float] = {}
        confidence_features: dict[str, dict[str, float]] = {}
        fusion_margin = max(0.0, ranked[0][1] - ranked[1][1]) if len(ranked) > 1 else 0.0
        for item_id, _score in ranked:
            item_terms = set(normalized_tokens(retrieval_text(records[item_id])))
            lexical = len(query_terms & item_terms) / max(1, len(query_terms))
            dense_support = max(0.0, min(1.0, float(dense_scores.get(item_id, 0.0))))
            agreement = item_id in bm25_scores and item_id in dense_scores
            features = {
                "lexical_overlap": lexical,
                "dense_cosine": dense_support,
                "agreement": float(agreement),
                "bm25_reciprocal_rank": 1.0 / bm25_ranks[item_id] if item_id in bm25_ranks else 0.0,
                "dense_reciprocal_rank": 1.0 / dense_ranks[item_id] if item_id in dense_ranks else 0.0,
                "fusion_margin": fusion_margin,
                "query_length": min(1.0, len(query_terms) / 12.0),
                "exact_code": float(item_id in exact_candidate_ids),
                "filter_match": float(bool(normalized_filters)),
            }
            confidence_features[item_id] = features
            confidence_scores[item_id] = confidence_model.predict(features)
        if effective_mode == "exact_code":
            confidence_scores.update({item_id: 1.0 for item_id, _score in ranked})
        elif route_fallback:
            confidence_scores.update({item_id: max(.8, confidence_scores.get(item_id, 0.0))
                                      for item_id in exact_candidate_ids})
        abstention_reason = None
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
                    abstention_reason = "below_score_threshold" if ranked else "no_candidate"
                    ranked = []
            else:
                ranked = [(item_id, score) for item_id, score in ranked if score >= score_threshold]
                if not ranked:
                    abstention_reason = "below_score_threshold"
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
                confidence_features=confidence_features.get(item_id),
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
            abstained=not results, abstention_reason=(abstention_reason or "no_candidate") if not results else None,
            fallback=fallback_reason,
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

    @property
    def phase7_cache_fingerprint(self) -> str:
        if not self.phase7_enabled or self.phase7_policy is None or self.phase7_provider is None:
            return "phase7-disabled"
        return self.phase7_policy.fingerprint + ":" + self.phase7_provider.model_identity.fingerprint

    def search_phase7(self, query: str, doc_ids: list[str] | None = None,
                      filters: dict | None = None, top_k: int = 5,
                      score_threshold: float | None = None) -> list[RetrievalResult]:
        """Rerank only Phase 6-accepted candidates; otherwise return Phase 6."""
        started = time.perf_counter()
        policy = self.phase7_policy
        provider = self.phase7_provider
        # The fallback must be the *requested* Phase 6 search. top_k changes
        # candidate generation and exact-code routing in Phase 6.
        baseline = self.search(query, doc_ids=doc_ids, filters=filters,
                               top_k=top_k, mode="auto", score_threshold=score_threshold)
        trace = self.last_trace

        def finish(values: list[RetrievalResult], selected: bool, reason: str) -> list[RetrievalResult]:
            latency = dict(trace.latency_ms or {})
            latency["reranker"] = round(max(0.0, (time.perf_counter() - started) * 1000
                                             - latency.get("total", 0.0)), 3)
            latency["total"] = round((time.perf_counter() - started) * 1000, 3)
            self.last_trace = replace(trace, rerank_selected=selected,
                                      rerank_reason=reason, final_count=len(values), latency_ms=latency)
            return values

        if not self.phase7_enabled or policy is None or provider is None:
            return finish(baseline[:top_k], False, "feature_disabled")
        manifest = self.index_root / "manifest.json"
        phase6 = self.policies.get("hybrid_rrf")
        phase6_source = Path(phase6.source) if phase6 is not None else None
        if (not manifest.is_file() or not phase6_source or not phase6_source.is_file()
                or hashlib.sha256(manifest.read_bytes()).hexdigest() != policy.index_sha256
                or hashlib.sha256(phase6_source.read_bytes()).hexdigest() != policy.phase6_calibration_sha256):
            return finish(baseline[:top_k], False, "calibration_or_index_mismatch")
        # Routing is fitted at five results and must use that same feature
        # extraction plan when the caller asks for Recall@10 or a larger view.
        routing_baseline = baseline
        routing_trace = trace
        if top_k != 5:
            routing_baseline = self.search(query, doc_ids=doc_ids, filters=filters,
                                           top_k=5, mode="auto", score_threshold=score_threshold)
            routing_trace = self.last_trace
        selected, reason = policy.route(query, routing_baseline, routing_trace)
        if not selected:
            return finish(baseline[:top_k], False, reason)
        pool = self.search(query, doc_ids=doc_ids, filters=filters,
                           top_k=policy.candidate_cap, mode="auto", score_threshold=score_threshold)
        if not pool:
            return finish(baseline[:top_k], False, "empty_candidate_pool")
        candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id,
                                      item.page, item.content, item.rank,
                                      float(item.fusion_score or 0.0))
                      for item in pool[:policy.rerank_candidate_cap]]
        if not self.phase7_enabled:
            return finish(baseline[:top_k], False, "feature_disabled")
        try:
            ranked = provider.score(query, candidates)
        except RerankerUnavailable as error:
            # Providers are injectable; their exception text is untrusted.
            safe_reasons = {"queue_full", "circuit_open", "reranker_timeout",
                            "model_checksum_mismatch", "model_snapshot_missing",
                            "invalid_model_scores", "reranker_inference_failed", "feature_disabled"}
            return finish(baseline[:top_k], False,
                          str(error) if str(error) in safe_reasons else "reranker_unavailable")
        except Exception:
            return finish(baseline[:top_k], False, "reranker_unavailable")
        by_id = {item.chunk_id: item for item in pool}
        try:
            invalid = (len(ranked) != len(candidates) or len({item.candidate_id for item in ranked}) != len(ranked)
                or {item.candidate_id for item in ranked} != {item.candidate_id for item in candidates}
                or any(isinstance(item.reranker_score, bool)
                       or not math.isfinite(item.reranker_score) for item in ranked)
                or any(item.final_rank != rank or item.model_identity != provider.model_identity
                       for rank, item in enumerate(ranked, 1))
                or any(ranked[index - 1].reranker_score < ranked[index].reranker_score
                       for index in range(1, len(ranked)))
                or any((item.doc_id, item.chunk_id, item.page) !=
                       (by_id[item.candidate_id].doc_id, by_id[item.candidate_id].chunk_id,
                        by_id[item.candidate_id].page) for item in ranked)
                or any(item.original_rank != by_id[item.candidate_id].rank
                       or item.original_rrf_score != float(by_id[item.candidate_id].fusion_score or 0.0)
                       for item in ranked))
        except (AttributeError, KeyError, TypeError, ValueError):
            invalid = True
        if invalid:
            return finish(baseline[:top_k], False, "reranker_provenance_invalid")
        margin = ranked[0].reranker_score - ranked[1].reranker_score if len(ranked) > 1 else 0.0
        if ranked[0].reranker_score < policy.threshold or margin < policy.margin_threshold:
            return finish(baseline[:top_k], False, "reranker_score_or_margin_below_threshold")
        results = [replace(by_id[item.candidate_id], rank=rank,
                           reranker_score=item.reranker_score, retriever="hybrid_rerank")
                   for rank, item in enumerate(ranked, 1)]
        results.extend(replace(item, rank=rank) for rank, item in
                       enumerate(pool[len(candidates):], len(candidates) + 1))
        return finish(results[:top_k], True, reason)

    @classmethod
    def with_calibration_report(cls, index_root: str | Path, report_path: str | Path, **kwargs) -> "HybridRetriever":
        """Construct a retriever whose abstention threshold is auditable."""
        policy = RetrievalPolicy.from_report(report_path)
        return cls(index_root, policies={policy.mode: policy}, **kwargs)
