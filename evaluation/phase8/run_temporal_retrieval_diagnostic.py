"""Run offline retrieval diagnostics on Phase 8 supplemental draft rows.

The source and questions are historically exposed. This report is diagnostic
regression evidence only; it cannot qualify the Phase 8 benchmark gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from pathlib import Path

import psutil

from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.common.metrics import _is_relevant, evaluate_retrieval
from evaluation.phase8.run_retrieval_baseline import grouped_ci, sha256
from evaluation.retrieval.evaluate_hybrid_release import _run_mode


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / ".tmp/hybrid-index"
DEFAULT_CALIBRATION = ROOT / "evaluation/results/hybrid_retrieval_calibration.json"
DEFAULT_DATASET = ROOT / "evaluation/phase8/temporal_comparison_review_draft_v4.jsonl"
DEFAULT_OUTPUT = ROOT / "evaluation/results/phase8-temporal-retrieval-diagnostic-v1.json"


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def run(index_dir: Path = DEFAULT_INDEX, calibration: Path = DEFAULT_CALIBRATION,
        dataset: Path = DEFAULT_DATASET) -> dict:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    index_dir = index_dir if index_dir.is_absolute() else ROOT / index_dir
    calibration = calibration if calibration.is_absolute() else ROOT / calibration
    dataset = dataset if dataset.is_absolute() else ROOT / dataset
    index_dir, calibration, dataset = index_dir.resolve(), calibration.resolve(), dataset.resolve()
    rows = load_rows(dataset)
    if not rows or len(rows) > 300 or any(row.get("answerable") is not True for row in rows):
        raise ValueError("expected 1..300 answerable supplemental draft rows")
    ids = [row.get("qid") for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("draft qids must be unique")

    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.hybrid import HybridRetriever

    process = psutil.Process()
    rss_before = process.memory_info().rss
    index_manifest_path = index_dir / "manifest.json"
    index_manifest = json.loads(index_manifest_path.read_text(encoding="utf-8-sig"))
    doc_ids = list(index_manifest["documents"])
    valid_chunks = set()
    for doc_id in doc_ids:
        dense = json.loads((index_dir / doc_id / "dense.json").read_text(encoding="utf-8-sig"))
        valid_chunks.update((doc_id, item["chunk_id"]) for item in dense.get("items", []))
    missing = [row["qid"] for row in rows for evidence in row.get("gold_evidence", [])
               if (evidence.get("doc_id"), evidence.get("chunk_id")) not in valid_chunks]
    if missing:
        raise ValueError(f"draft evidence is absent from the bound index: {missing}")

    policy = RetrievalPolicy.from_report(calibration, expected_mode="hybrid_rrf")
    retriever = HybridRetriever(index_dir, query_cache_size=0, policies={"hybrid_rrf": policy})
    started = time.perf_counter()
    run_report, outputs, _traces = _run_mode(rows, retriever, doc_ids, "auto")
    wall_ms = (time.perf_counter() - started) * 1000
    quality = evaluate_retrieval(rows, lambda row: outputs[row["qid"]], k_values=(1, 3, 5, 10))
    per_query = {row["qid"]: row for row in quality["per_query"]}
    values = {row["qid"]: per_query[row["qid"]]["recall"]["5"] for row in rows}
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    recall_at_k = {}
    for k in (1, 3, 5, 10):
        numerator = sum(per_query[row["qid"]]["recall"][str(k)] for row in rows)
        recall_at_k[str(k)] = {"value": round(numerator / len(rows), 6),
                               "numerator": int(numerator), "denominator": len(rows)}
    rank_sum = sum(per_query[row["qid"]]["mrr"] for row in rows)
    per_query_diagnostic = []
    for row in rows:
        retrieved = outputs[row["qid"]]
        first_relevant_rank = next((rank for rank, item in enumerate(retrieved, start=1)
                                    if _is_relevant(item, row["gold_evidence"])), None)
        per_query_diagnostic.append({
            "qid": row["qid"],
            "tags": row["tags"],
            "first_relevant_rank": first_relevant_rank,
            "retrieved_top3": [{
                "doc_id": item.doc_id,
                "chunk_id": item.chunk_id,
                "page": item.page,
                "score": round(float(item.score), 6),
            } for item in retrieved[:3]],
        })
    index_size = sum(path.stat().st_size for path in index_dir.rglob("*") if path.is_file())
    return {
        "schema_version": 1,
        "phase": 8,
        "status": "diagnostic_supplemental_retrieval_regression_only",
        "gate_eligible": False,
        "provider_requests": 0,
        "benchmark": {
            "path": dataset.relative_to(ROOT).as_posix(),
            "file_sha256": sha256(dataset),
            "rows": len(rows),
            "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
            "tags": dict(sorted(Counter(tag for row in rows for tag in row["tags"]).items())),
            "owner_review_status": "pending",
            "exposure": "historical benchmark code overlap; source was in prior index",
            "fresh_validation": False,
        },
        "retrieval": {
            "mode": "auto",
            "answerable_recall_at_k": recall_at_k,
            "answerable_mrr": {"value": round(rank_sum / len(rows), 6),
                                "numerator": round(rank_sum, 6), "denominator": len(rows)},
            "group_bootstrap_ci95_recall_at_5": grouped_ci(values, groups),
            "connected_groups": len(set(groups.values())),
            "largest_group_size": max(Counter(groups.values()).values(), default=0),
            "per_query_diagnostic": per_query_diagnostic,
            "latency_ms": {**run_report["latency_ms"], "measured_requests": len(rows),
                           "total_wall_ms": round(wall_ms, 3)},
            "schema_invalid_rate": run_report["schema_invalid_rate"],
            "provenance_loss_rate": run_report["provenance_loss_rate"],
        },
        "runtime": {
            "model": index_manifest.get("model_name"),
            "model_revision": index_manifest.get("model_revision"),
            "index_manifest_sha256": sha256(index_manifest_path),
            "calibration_sha256": sha256(calibration),
            "index_size_bytes": index_size,
        },
        "resources": {
            "rss_before_bytes": rss_before,
            "rss_after_bytes": process.memory_info().rss,
            "peak_working_set_bytes": getattr(process.memory_info(), "peak_wset", None),
        },
        "unmeasured": {
            "answer_quality": "not_measured_no_provider_outputs_bound_to_this_draft",
            "citation_quality": "not_measured_no_provider_outputs_bound_to_this_draft",
            "groundedness": "not_measured_no_provider_outputs_bound_to_this_draft",
            "answer_abstention": f"not_applicable_all_{len(rows)}_draft_queries_are_answerable",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.index_dir, args.calibration, args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "gate_eligible": report["gate_eligible"],
        "recall_at_5": report["retrieval"]["answerable_recall_at_k"]["5"],
        "recall_at_1": report["retrieval"]["answerable_recall_at_k"]["1"],
        "recall_at_3": report["retrieval"]["answerable_recall_at_k"]["3"],
        "recall_at_1_failures": [item["qid"] for item in report["retrieval"]["per_query_diagnostic"]
                                 if item["first_relevant_rank"] != 1],
        "groups": report["retrieval"]["connected_groups"],
        "latency_ms": report["retrieval"]["latency_ms"],
        "provider_requests": report["provider_requests"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
