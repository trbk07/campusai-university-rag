"""Auditable per-query retrieval failures for generated and human benchmarks."""

from __future__ import annotations

from evaluation.metrics import recall_at_k


def failure_cases(rows: list[dict], outputs: dict[str, list], traces: list[dict],
                  threshold: float, *, family: str, split: str) -> list[dict]:
    trace_by_id = {trace["query_id"]: trace for trace in traces}
    failures = []
    for row in rows:
        values = outputs[row["qid"]]
        trace = trace_by_id[row["qid"]]
        hit = bool(recall_at_k(values, row["gold_evidence"], 5)) if row["answerable"] else False
        route_mismatch = bool(row.get("expected_route") and row["expected_route"] != trace["route"])
        if row["answerable"] and hit and not route_mismatch:
            continue
        if not row["answerable"] and not values and not route_mismatch:
            continue
        cause = ("route_mismatch" if route_mismatch else
                 "negative_false_positive" if not row["answerable"] else
                 "unexpected_abstention" if not values else "missing_evidence")
        failures.append({
            "benchmark_family": family, "split": split,
            "qid": row["qid"], "query": row["question"],
            "expected_evidence": row["gold_evidence"],
            "returned_ids": [item.chunk_id for item in values],
            "route": trace["route"],
            "ranks": [{"chunk_id": item.chunk_id, "bm25_rank": (item.retriever_ranks or {}).get("bm25"),
                       "dense_rank": (item.retriever_ranks or {}).get("dense"),
                       "fusion_rank": item.rank, "acceptance_score": item.confidence_score}
                      for item in values],
            "threshold": threshold, "root_cause_category": cause,
        })
    return failures
