"""Deterministic citation coverage metrics."""
from __future__ import annotations


def citation_precision(predicted: list[str], supported: list[str]) -> float:
    citations, evidence = set(predicted), set(supported)
    return round(len(citations & evidence) / len(citations), 4) if citations else 1.0


def citation_recall(predicted: list[str], supported: list[str]) -> float:
    evidence = set(supported)
    return round(len(set(predicted) & evidence) / len(evidence), 4) if evidence else 1.0


def citation_report(cases: list[dict]) -> dict[str, float]:
    if not cases:
        return {"citation_precision": 0.0, "citation_recall": 0.0}
    p = [citation_precision(r.get("citations", []), r.get("supported", [])) for r in cases]
    q = [citation_recall(r.get("citations", []), r.get("supported", [])) for r in cases]
    return {"citation_precision": round(sum(p) / len(p), 4), "citation_recall": round(sum(q) / len(q), 4)}

