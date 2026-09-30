"""Rank fusion utilities."""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[tuple[str, float]]], rrf_k: int = 60,
                           top_k: int | None = None, weights: list[float] | None = None) -> list[tuple[str, float]]:
    """Fuse ranked result lists using reciprocal rank fusion."""
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings) or any(weight < 0 for weight in weights):
        raise ValueError("weights must be non-negative and match rankings")
    scores: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights):
        seen: set[str] = set()
        unique_rank = 0
        for item_id, _score in ranking:
            if item_id in seen:
                continue
            seen.add(item_id)
            unique_rank += 1
            scores[item_id] = scores.get(item_id, 0.0) + weight / (rrf_k + unique_rank)
    result = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return result[:top_k] if top_k is not None else result


rrf = reciprocal_rank_fusion


def rrf_details(rankings: dict[str, list[tuple[str, float]]], rrf_k: int = 60,
                weights: dict[str, float] | None = None, top_k: int | None = None) -> list[dict]:
    """Return auditable rank-only fusion details without mixing raw scores."""
    names = list(rankings)
    configured = weights or {name: 1.0 for name in names}
    fused = reciprocal_rank_fusion([rankings[name] for name in names], rrf_k, top_k,
                                   [float(configured.get(name, 1.0)) for name in names])
    rank_maps = {}
    for name, values in rankings.items():
        ranks = {}
        for item_id, _score in values:
            if item_id not in ranks:
                ranks[item_id] = len(ranks) + 1
        rank_maps[name] = ranks
    return [{"chunk_id": item_id, "fusion_score": score,
             "retriever_ranks": {name: ranks[item_id] for name, ranks in rank_maps.items() if item_id in ranks},
             "retriever_sources": [name for name, ranks in rank_maps.items() if item_id in ranks]}
            for item_id, score in fused]
