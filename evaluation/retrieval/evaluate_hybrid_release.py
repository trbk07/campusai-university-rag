"""Run the locked Phase 6 ablation, holdout and routing evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.contracts import validate_result
from campusai.retrieval.dense_index import HASH_MODEL
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.negative import negative_query_reason
from campusai.retrieval.routing import choose_route, detected_codes
from evaluation.common.metrics import evaluate_retrieval
from evaluation.benchmarks.retrieval_schema import load_jsonl
from evaluation.retrieval.retrieval_failure_cases import failure_cases


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return round(ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * percentile) - 1))], 3)


def _run_mode(rows: list[dict], retriever: HybridRetriever, doc_ids: list[str], mode: str,
              *, apply_filters: bool = True) -> tuple[dict, dict[str, list], list[dict]]:
    outputs: dict[str, list] = {}
    traces: list[dict] = []
    latencies = []
    schema_errors = []
    provenance_errors = 0
    filter_leakage = 0
    for row in rows:
        filters = row.get("filters") if apply_filters else None
        started = time.perf_counter()
        results = retriever.search(row["question"], doc_ids, filters=filters, top_k=10, mode=mode)
        latencies.append((time.perf_counter() - started) * 1000)
        outputs[row["qid"]] = results
        trace = retriever.last_trace.to_dict()
        trace["query_id"] = row["qid"]
        traces.append(trace)
        for result in results:
            valid, errors = validate_result(result)
            if not valid:
                schema_errors.extend(f"{row['qid']}:{error}" for error in errors)
            if not result.metadata.get("page_range"):
                provenance_errors += 1
            if filters and any(str(result.metadata.get(key, "")).casefold() != str(value).casefold()
                               for key, value in filters.items()):
                filter_leakage += 1
    quality = evaluate_retrieval(rows, lambda row: outputs[row["qid"]], k_values=(1, 3, 5, 10))
    negative = [row for row in rows if not row.get("answerable")]
    answerable = [row for row in rows if row.get("answerable")]
    fpr = sum(bool(outputs[row["qid"]]) for row in negative) / max(1, len(negative))
    abstention_precision_denominator = sum(not outputs[row["qid"]] for row in rows)
    abstention_precision = (sum(not outputs[row["qid"]] for row in negative) / abstention_precision_denominator
                            if abstention_precision_denominator else 1.0)
    abstention_recall = sum(not outputs[row["qid"]] for row in negative) / max(1, len(negative))
    by_qid = {item["qid"]: item for item in quality["per_query"]}
    segments = {}
    for field in ("category", "difficulty", "language", "query_type"):
        groups = defaultdict(list)
        for row in rows:
            groups[str(row.get(field, "unknown"))].append(by_qid[row["qid"]])
        segments[field] = {key: {"n": len(values),
                                 "recall_at_5": round(sum(v["recall"]["5"] for v in values) / len(values), 6),
                                 "mrr": round(sum(v["mrr"] for v in values) / len(values), 6)}
                           for key, values in groups.items()}
    warm = latencies[1:] if len(latencies) > 1 else latencies
    return ({
        "mode": mode, "records": len(rows),
        "quality": {key: value for key, value in quality.items() if key != "per_query"},
        "negative": {"count": len(negative), "false_positive_rate": round(fpr, 6),
                     "abstention_precision": round(abstention_precision, 6),
                     "abstention_recall": round(abstention_recall, 6)},
        "latency_ms": {"cold": round(latencies[0], 3), "p50": _percentile(warm, .50),
                       "p95": _percentile(warm, .95), "p99": _percentile(warm, .99)},
        "schema_invalid_rate": len(schema_errors) / max(1, sum(len(v) for v in outputs.values())),
        "schema_errors": schema_errors[:20],
        "provenance_loss_rate": provenance_errors / max(1, sum(len(v) for v in outputs.values())),
        "filter_leakage": filter_leakage, "segments": segments,
        "answerable_count": len(answerable),
    }, outputs, traces)


def _bootstrap(left: list[float], right: list[float], iterations: int = 2000) -> dict:
    randomizer = random.Random(6006)
    differences = []
    for _ in range(iterations):
        indexes = [randomizer.randrange(len(left)) for _ in left]
        differences.append(statistics.mean(left[index] - right[index] for index in indexes))
    differences.sort()
    return {"mean_difference": round(statistics.mean(differences), 6),
            "ci95": [round(differences[int(.025 * iterations)], 6),
                     round(differences[min(iterations - 1, int(.975 * iterations))], 6)],
            "iterations": iterations}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/hybrid_retrieval_calibration.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    policy = RetrievalPolicy.from_report(args.calibration, expected_mode="hybrid_rrf")
    ranking_retriever = HybridRetriever(args.index_dir, query_cache_size=0)
    primary_retriever = HybridRetriever(args.index_dir, query_cache_size=0, policies={"hybrid_rrf": policy})
    doc_ids = sorted(path.name for path in args.index_dir.iterdir()
                     if path.is_dir() and (path / "bm25.json").is_file())
    manifest_path = args.index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split_rows = {split: load_jsonl(Path(f"data/benchmark/hybrid_retrieval_{split}.jsonl"))
                  for split in ("test", "holdout")}
    reports = {}
    outputs = {}
    traces = {}
    for split, rows in split_rows.items():
        for mode in ("bm25", "dense", "hybrid_rrf", "auto"):
            key = f"{split}:{mode}"
            retriever = primary_retriever if mode in {"hybrid_rrf", "auto"} else ranking_retriever
            reports[key], outputs[key], traces[key] = _run_mode(rows, retriever, doc_ids, mode)
    generated_failures = [
        case
        for split, rows in split_rows.items()
        for case in failure_cases(rows, outputs[f"{split}:auto"], traces[f"{split}:auto"],
                                  policy.threshold, family="regression_generated", split=split)
    ]
    (args.output_dir / "hybrid_failure_cases_generated.json").write_text(
        json.dumps(generated_failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for mode, filename in (("bm25", "hybrid_bm25_report.json"),
                           ("dense", "hybrid_dense_report.json"),
                           ("hybrid_rrf", "hybrid_fusion_report.json")):
        value = {"schema_version": 1, "phase": 6, "mode": mode,
                 "test": reports[f"test:{mode}"], "holdout": reports[f"holdout:{mode}"],
                 "model": manifest.get("model_name"), "model_revision": manifest.get("model_revision")}
        (args.output_dir / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    primary_test = reports["test:auto"]
    primary_holdout = reports["holdout:auto"]
    exact_rows = [row for row in split_rows["test"] if row["category"] == "exact_code"]
    exact_recall = statistics.mean(
        1.0 if any(result.chunk_id == row["gold_evidence"][0]["chunk_id"]
                   for result in outputs["test:auto"][row["qid"]][:5]) else 0.0
        for row in exact_rows
    )
    expected_routes = []
    actual_routes = []
    for row, trace in zip(split_rows["test"], traces["test:auto"]):
        if negative_query_reason(row["question"]):
            expected = "abstain"
        else:
            expected = ("exact_code" if detected_codes(row["question"])
                        else choose_route(row["question"], filters=row.get("filters")))
        expected_routes.append(expected)
        actual_routes.append(trace["route"])
    routing_accuracy = sum(left == right for left, right in zip(expected_routes, actual_routes)) / len(expected_routes)
    ablation = {mode: {"recall_at_5": reports[f"test:{mode}"]["quality"]["answerable_recall"]["5"],
                       "mrr": reports[f"test:{mode}"]["quality"]["mrr_answerable"],
                       "ndcg_at_5": reports[f"test:{mode}"]["quality"]["ndcg"]["5"],
                       "fpr": reports[f"test:{mode}"]["negative"]["false_positive_rate"],
                       "p95_ms": reports[f"test:{mode}"]["latency_ms"]["p95"]}
                for mode in ("bm25", "dense", "hybrid_rrf", "auto")}
    test_rows = split_rows["test"]
    # Bootstrap the auditable per-query Recall@5 arrays from stored outputs.
    relevant = lambda result, row: any(result.chunk_id == evidence.get("chunk_id") for evidence in row["gold_evidence"])
    recall_arrays = {mode: [float(any(relevant(item, row) for item in outputs[f"test:{mode}"][row["qid"]][:5]))
                     for row in test_rows if row.get("answerable")]
              for mode in ("bm25", "dense", "auto")}
    mrr_arrays = {}
    for mode in ("bm25", "dense", "auto"):
        values = []
        for row in test_rows:
            if not row.get("answerable"):
                continue
            rank = next((index for index, item in enumerate(outputs[f"test:{mode}"][row["qid"]], 1)
                         if relevant(item, row)), None)
            values.append(0.0 if rank is None else 1.0 / rank)
        mrr_arrays[mode] = values
    statistical = {"tuning_split": "dev", "evaluation_splits": ["test", "holdout"],
                   "holdout_locked": True, "config_locked": True,
                   "paired_comparison": {
                       "hybrid_vs_bm25": {
                           "recall_at_5": _bootstrap(recall_arrays["auto"], recall_arrays["bm25"]),
                           "mrr": _bootstrap(mrr_arrays["auto"], mrr_arrays["bm25"]),
                       },
                       "hybrid_vs_dense": {
                           "recall_at_5": _bootstrap(recall_arrays["auto"], recall_arrays["dense"]),
                           "mrr": _bootstrap(mrr_arrays["auto"], mrr_arrays["dense"]),
                       },
                   }}
    release = {
        "schema_version": 1, "phase": 6, "benchmark_family": "regression_generated",
        "status": "pass", "primary_mode": "auto",
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "model": manifest.get("model_name"), "model_revision": manifest.get("model_revision"),
        "rrf": {"k": ranking_retriever.rrf_k, "bm25_weight": ranking_retriever.rrf_weights[0],
                "dense_weight": ranking_retriever.rrf_weights[1],
                "candidate_limit": ranking_retriever.candidate_limit},
        "index_sha256": _sha(manifest_path), "calibration_sha256": _sha(args.calibration),
        "benchmark_sha256": {split: _sha(Path(f"data/benchmark/hybrid_retrieval_{split}.jsonl"))
                             for split in ("test", "holdout")},
        "ablation": ablation, "primary_test": primary_test, "primary_holdout": primary_holdout,
        "exact_code_recall_at_5": round(exact_recall, 6),
        "routing_accuracy": round(routing_accuracy, 6), "statistical_validation": statistical,
        "failure_case_count": len(generated_failures),
    }
    hybrid_test = ablation["auto"]
    baselines = [ablation["bm25"], ablation["dense"]]
    errors = []
    if manifest.get("model_name") == HASH_MODEL:
        errors.append("release_forbids_hash_embedding_provider")
    if primary_test["quality"]["answerable_recall"]["5"] < .90 or primary_holdout["quality"]["answerable_recall"]["5"] < .90:
        errors.append("primary_recall_at_5")
    if primary_test["negative"]["false_positive_rate"] > .05 or primary_holdout["negative"]["false_positive_rate"] > .05:
        errors.append("negative_false_positive_rate")
    if exact_recall < .99:
        errors.append("exact_code_recall")
    if routing_accuracy < .98:
        errors.append("routing_accuracy")
    if hybrid_test["recall_at_5"] < max(item["recall_at_5"] for item in baselines):
        errors.append("hybrid_below_single_retriever")
    if hybrid_test["recall_at_5"] <= max(item["recall_at_5"] for item in baselines):
        errors.append("hybrid_does_not_strictly_improve_recall")
    if not any(hybrid_test["mrr"] > item["mrr"] or hybrid_test["ndcg_at_5"] > item["ndcg_at_5"] for item in baselines):
        errors.append("hybrid_does_not_improve_ranking")
    if max(primary_test["latency_ms"]["p95"], primary_holdout["latency_ms"]["p95"]) > 500:
        errors.append("warm_p95")
    if max(primary_test["latency_ms"]["p99"], primary_holdout["latency_ms"]["p99"]) > 1000:
        errors.append("warm_p99")
    if any(report["schema_invalid_rate"] or report["provenance_loss_rate"] or report["filter_leakage"]
           for report in reports.values()):
        errors.append("contract_or_filter_failure")
    release["errors"] = errors
    release["status"] = "pass" if not errors else "fail"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "hybrid_ablation_report.json").write_text(json.dumps({"ablation": ablation, **statistical}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "hybrid_holdout_report.json").write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": release["status"], "errors": errors, "ablation": ablation,
                      "test": {"recall_at_5": primary_test["quality"]["answerable_recall"]["5"],
                               "fpr": primary_test["negative"]["false_positive_rate"]},
                      "holdout": {"recall_at_5": primary_holdout["quality"]["answerable_recall"]["5"],
                                  "fpr": primary_holdout["negative"]["false_positive_rate"]},
                      "exact_code_recall_at_5": exact_recall, "routing_accuracy": routing_accuracy}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
