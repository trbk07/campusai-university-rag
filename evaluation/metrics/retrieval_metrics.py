"""Deterministic retrieval metrics for document-level QA benchmarks."""
from __future__ import annotations
from typing import Iterable


def recall_at_k(retrieved: Iterable[str], relevant: Iterable[str], k: int) -> float:
    expected = set(relevant)
    if not expected:
        return 1.0
    return round(len(set(list(retrieved)[:k]) & expected) / len(expected), 4)


def mrr(retrieved: Iterable[str], relevant: Iterable[str]) -> float:
    expected = set(relevant)
    for rank, item in enumerate(retrieved, 1):
        if item in expected:
            return round(1.0 / rank, 4)
    return 0.0


def retrieval_report(cases: Iterable[dict], k: int = 5) -> dict[str, float]:
    rows = list(cases)
    if not rows:
        return {f"recall@{k}": 0.0, "mrr": 0.0}
    return {f"recall@{k}": round(sum(recall_at_k(r.get("retrieved", []), r.get("relevant", []), k) for r in rows) / len(rows), 4),
            "mrr": round(sum(mrr(r.get("retrieved", []), r.get("relevant", [])) for r in rows) / len(rows), 4)}

