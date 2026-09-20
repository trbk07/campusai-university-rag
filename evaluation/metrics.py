"""Retrieval metrics used by T8."""

from __future__ import annotations

from collections.abc import Iterable


def _is_relevant(result, gold_evidence: list[dict]) -> bool:
    result_doc = getattr(result, "doc_id", result.get("doc_id") if isinstance(result, dict) else None)
    result_page = getattr(result, "page", result.get("page") if isinstance(result, dict) else None)
    result_chunk = getattr(result, "chunk_id", result.get("chunk_id") if isinstance(result, dict) else None)
    for evidence in gold_evidence:
        if evidence.get("chunk_id") and evidence["chunk_id"] == result_chunk:
            return True
        if evidence.get("doc_id") == result_doc and (not evidence.get("pages") or result_page in evidence["pages"]):
            return True
    return False


def recall_at_k(results: list, gold_evidence: list[dict], k: int) -> float:
    return float(any(_is_relevant(result, gold_evidence) for result in results[:k]))


def reciprocal_rank(results: list, gold_evidence: list[dict]) -> float:
    for rank, result in enumerate(results, start=1):
        if _is_relevant(result, gold_evidence):
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(records: Iterable[dict], retrieve, k_values: tuple[int, ...] = (3, 5)) -> dict:
    rows = []
    for record in records:
        results = retrieve(record)
        evidence = record.get("gold_evidence", [])
        rows.append({"qid": record.get("qid"), "recall": {str(k): recall_at_k(results, evidence, k) for k in k_values}, "mrr": reciprocal_rank(results, evidence)})
    count = len(rows)
    return {
        "n": count,
        "recall": {str(k): sum(row["recall"][str(k)] for row in rows) / count if count else 0.0 for k in k_values},
        "mrr": sum(row["mrr"] for row in rows) / count if count else 0.0,
        "per_query": rows,
    }
