"""Rank fusion utilities."""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[tuple[str, float]]], rrf_k: int = 60, top_k: int | None = None) -> list[tuple[str, float]]:
    """Fuse ranked result lists using reciprocal rank fusion."""

    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, (item_id, _score) in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (rrf_k + rank)
    result = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return result[:top_k] if top_k is not None else result


rrf = reciprocal_rank_fusion
