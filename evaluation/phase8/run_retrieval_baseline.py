"""Measure a bounded, reviewed Phase 8 retrieval regression cohort.

This runner measures retrieval only. It never sends requests to an LLM provider
and explicitly preserves prior-exposure limitations in its report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.common.metrics import evaluate_retrieval
from evaluation.retrieval.evaluate_hybrid_release import _run_mode


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = Path("data/benchmark/phase7_review_cycles/phase7-release-20261004-r18/human_retrieval.jsonl")
DEFAULT_REVIEW = Path("evaluation/results/phase7-source-context-20261004-r18/human_benchmark_manifest.json")
DEFAULT_INDEX = Path(".tmp/hybrid-index")
DEFAULT_CALIBRATION = Path("evaluation/results/hybrid_retrieval_calibration.json")
DEFAULT_OUTPUT = Path("evaluation/results/phase8-r18-retrieval-baseline-v1.json")
SELECTION_SEED = "phase8-r18-280-v1"
TARGET_PER_SPLIT = 140
BOOTSTRAP_ITERATIONS = 5000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def select_rows(dataset: Path = DEFAULT_DATASET, review_path: Path = DEFAULT_REVIEW) -> tuple[list[dict], dict]:
    review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    if review.get("status") != "pass" or review.get("owner_review_complete") is not True:
        raise ValueError("source benchmark lacks a passing owner-review manifest")
    if review.get("independent_review_complete") is not False:
        raise ValueError("source benchmark review mode is unexpected; audit before reuse")
    all_rows = load_jsonl(dataset)
    if len(all_rows) != review.get("records") or sha256(dataset) != review.get("dataset_sha256"):
        raise ValueError("source benchmark differs from its reviewed manifest")
    selected = []
    for split in ("test", "holdout"):
        split_rows = [row for row in all_rows if row.get("split") == split]
        if len(split_rows) < TARGET_PER_SPLIT:
            raise ValueError(f"source split {split} is below the deterministic sample size")
        ranked = sorted(split_rows, key=lambda row: hashlib.sha256(
            f"{SELECTION_SEED}:{row['qid']}".encode("utf-8")).hexdigest())
        selected.extend(ranked[:TARGET_PER_SPLIT])
    if len(selected) != 280 or len({row["qid"] for row in selected}) != 280:
        raise ValueError("selected cohort must contain exactly 280 unique questions")
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in selected])
    selection = {
        "version": SELECTION_SEED,
        "target_per_split": TARGET_PER_SPLIT,
        "selected_ids_sha256": hashlib.sha256("\n".join(sorted(row["qid"] for row in selected)).encode("utf-8")).hexdigest(),
        "selected_ids": sorted(row["qid"] for row in selected),
        "split_counts": dict(sorted(Counter(row["split"] for row in selected).items())),
        "connected_groups": len(set(groups.values())),
        "largest_connected_group": max(Counter(groups.values()).values(), default=0),
        "group_by_qid": groups,
        "tag_counts": dict(sorted(Counter(tag for row in selected for tag in row.get("tags", [])).items())),
        "source_review_mode": review.get("review_mode"),
        "source_owner_review_complete": review.get("owner_review_complete"),
        "source_independent_review_complete": review.get("independent_review_complete"),
        "prior_phase7_exposure": True,
        "fresh_validation": False,
    }
    return selected, {"review": review, "selection": selection}


def bind_custom_candidate(rows: list[dict]) -> dict:
    if not 100 <= len(rows) <= 300:
        raise ValueError(f"Phase 8 benchmark candidate must have 100..300 rows; got {len(rows)}")
    if len({row.get("qid") for row in rows}) != len(rows):
        raise ValueError("Phase 8 candidate qids must be unique")
    if any(row.get("split") not in {"test", "holdout"} for row in rows):
        raise ValueError("Phase 8 candidate rows must be in test or holdout")
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    split_by_group: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        split_by_group[groups[row["qid"]]].add(row["split"])
    leakage = sorted(group for group, splits in split_by_group.items() if len(splits) > 1)
    if leakage:
        raise ValueError(f"Phase 8 candidate has connected-group split leakage: {leakage[:5]}")
    group_sizes = Counter(groups.values())
    selection = {
        "version": "phase8-reviewed-candidate-v4",
        "selected_ids_sha256": hashlib.sha256(
            "\n".join(sorted(row["qid"] for row in rows)).encode("utf-8")).hexdigest(),
        "selected_ids": sorted(row["qid"] for row in rows),
        "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
        "connected_groups": len(group_sizes),
        "largest_connected_group": max(group_sizes.values(), default=0),
        "group_by_qid": groups,
        "tag_counts": dict(sorted(Counter(tag for row in rows for tag in row.get("tags", [])).items())),
        "source_review_mode": "pending_owner_review",
        "source_owner_review_complete": False,
        "source_independent_review_complete": False,
        "prior_phase7_exposure": True,
        "fresh_validation": False,
    }
    return {"review": {"status": "pending", "review_mode": "owner_review_pending"},
            "selection": selection}


def grouped_ci(values: dict[str, float], group_by_qid: dict[str, str], *,
               iterations: int = BOOTSTRAP_ITERATIONS, seed: int = 20261010) -> dict:
    grouped: dict[str, list[float]] = defaultdict(list)
    for qid, value in values.items():
        grouped[group_by_qid[qid]].append(float(value))
    keys = sorted(grouped)
    if len(keys) < 2:
        return {"status": "not_estimable", "groups": len(keys), "ci95": None,
                "reason": "group bootstrap needs at least two connected groups"}
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        sampled = [keys[rng.randrange(len(keys))] for _ in keys]
        observations = [value for key in sampled for value in grouped[key]]
        estimates.append(statistics.mean(observations))
    estimates.sort()
    return {"status": "measured", "groups": len(keys), "iterations": iterations,
            "seed": seed, "ci95": [round(estimates[int(.025 * iterations)], 6),
                                    round(estimates[min(iterations - 1, int(.975 * iterations))], 6)]}


def split_metrics(rows: list[dict], outputs: dict[str, list], per_query: dict[str, dict],
                  group_by_qid: dict[str, str]) -> dict:
    """Summarize retrieval quality by split with explicit populations and denominators."""
    result = {}
    for split in sorted({row["split"] for row in rows}):
        subset = [row for row in rows if row["split"] == split]
        answerable = [row for row in subset if row.get("answerable") is True]
        unanswerable = [row for row in subset if row.get("answerable") is False]
        split_qids = {row["qid"] for row in subset}
        ci_groups = {qid: group_by_qid[qid] for qid in split_qids}

        def recall_metrics(population: list[dict], label: str) -> dict:
            denominator = len(population)
            return {
                str(k): {
                    "value": (round(sum(per_query[row["qid"]]["recall"][str(k)] for row in population)
                                      / denominator, 6) if denominator else None),
                    "numerator": int(sum(per_query[row["qid"]]["recall"][str(k)]
                                         for row in population)),
                    "denominator": denominator,
                    "population": label,
                    "aggregation": "micro mean of per-query evidence-hit indicator",
                    "status": "measured" if denominator else "not_applicable_empty_population",
                }
                for k in (1, 3, 5, 10)
            }

        mrr_denominator = len(answerable)
        mrr_numerator = sum(per_query[row["qid"]]["mrr"] for row in answerable)
        negative_denominator = len(unanswerable)
        false_positives = sum(bool(outputs[row["qid"]]) for row in unanswerable)
        result[split] = {
            "records": len(subset),
            "answerable_denominator": len(answerable),
            "unanswerable_denominator": negative_denominator,
            "recall_at_k": recall_metrics(subset, f"all {split} queries"),
            "answerable_recall_at_k": recall_metrics(answerable, f"answerable {split} queries"),
            "answerable_mrr": {
                "value": round(mrr_numerator / mrr_denominator, 6) if mrr_denominator else None,
                "numerator": round(mrr_numerator, 6), "denominator": mrr_denominator,
                "population": f"answerable {split} queries",
                "aggregation": "micro mean reciprocal rank over answerable queries",
                "status": "measured" if mrr_denominator else "not_applicable_empty_population",
            },
            "unanswerable_false_positive_rate": {
                "value": round(false_positives / negative_denominator, 6) if negative_denominator else None,
                "numerator": false_positives, "denominator": negative_denominator,
                "population": f"unanswerable {split} queries",
                "aggregation": "micro fraction with at least one retrieved result",
                "status": "measured" if negative_denominator else "not_applicable_empty_population",
            },
            "unanswerable_abstention_rate": {
                "value": round((negative_denominator - false_positives) / negative_denominator, 6)
                         if negative_denominator else None,
                "numerator": negative_denominator - false_positives,
                "denominator": negative_denominator,
                "population": f"unanswerable {split} queries",
                "aggregation": "micro fraction with no retrieved result",
                "status": "measured" if negative_denominator else "not_applicable_empty_population",
            },
            "group_bootstrap_ci95": {
                "answerable_recall_at_5": grouped_ci(
                    {row["qid"]: per_query[row["qid"]]["recall"]["5"] for row in answerable},
                    ci_groups),
                "answerable_mrr": grouped_ci(
                    {row["qid"]: per_query[row["qid"]]["mrr"] for row in answerable}, ci_groups),
            },
        }
    return result


def run(index_dir: Path = DEFAULT_INDEX, calibration_path: Path = DEFAULT_CALIBRATION,
        dataset: Path = DEFAULT_DATASET, review_path: Path = DEFAULT_REVIEW) -> dict:
    dataset = dataset if dataset.is_absolute() else ROOT / dataset
    review_path = review_path if review_path.is_absolute() else ROOT / review_path
    index_dir = index_dir if index_dir.is_absolute() else ROOT / index_dir
    calibration_path = calibration_path if calibration_path.is_absolute() else ROOT / calibration_path
    dataset, review_path = dataset.resolve(), review_path.resolve()
    index_dir, calibration_path = index_dir.resolve(), calibration_path.resolve()
    if dataset == DEFAULT_DATASET.resolve():
        rows, binding = select_rows(dataset, review_path)
        bound_review_path: Path | None = review_path
    else:
        rows = load_jsonl(dataset)
        binding = bind_custom_candidate(rows)
        bound_review_path = None
    process = psutil.Process()
    rss_before = process.memory_info().rss
    manifest_path = index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    doc_ids = list(manifest["documents"])
    evidence_ids: set[tuple[str, str]] = set()
    for doc_id in doc_ids:
        dense = json.loads((index_dir / doc_id / "dense.json").read_text(encoding="utf-8-sig"))
        evidence_ids.update((doc_id, item["chunk_id"]) for item in dense.get("items", []))
    missing = [row["qid"] for row in rows for item in row.get("gold_evidence", [])
               if (item.get("doc_id"), item.get("chunk_id")) not in evidence_ids]
    if missing:
        raise ValueError(f"selected gold evidence missing from index for {len(missing)} rows")
    policy = RetrievalPolicy.from_report(calibration_path, expected_mode="hybrid_rrf")
    retriever = HybridRetriever(index_dir, query_cache_size=0, policies={"hybrid_rrf": policy})
    started = time.perf_counter()
    report, outputs, _traces = _run_mode(rows, retriever, doc_ids, "auto")
    wall_ms = (time.perf_counter() - started) * 1000
    quality = evaluate_retrieval(rows, lambda row: outputs[row["qid"]], k_values=(1, 3, 5, 10))
    answerable = {row["qid"] for row in rows if row.get("answerable")}
    per_query = {row["qid"]: row for row in quality["per_query"]}
    groups = binding["selection"]["group_by_qid"]
    recall_values = {qid: per_query[qid]["recall"]["5"] for qid in answerable}
    mrr_values = {qid: per_query[qid]["mrr"] for qid in answerable}
    tag_metrics = {}
    tags = sorted({tag for row in rows for tag in row.get("tags", [])})
    for tag in tags:
        tagged = [row for row in rows if tag in row.get("tags", [])]
        positives = [row for row in tagged if row["answerable"]]
        negatives = [row for row in tagged if not row["answerable"]]
        false_positives = sum(bool(outputs[row["qid"]]) for row in negatives)
        abstentions = len(negatives) - false_positives
        positive_hits = sum(per_query[row["qid"]]["recall"]["5"] for row in positives)
        tag_metrics[tag] = {
            "records": len(tagged), "answerable": len(positives), "unanswerable": len(negatives),
            "answerable_recall_at_5": {
                "value": round(positive_hits / len(positives), 6) if positives else None,
                "numerator": round(positive_hits, 6), "denominator": len(positives),
                "status": "measured" if positives else "not_applicable_zero_answerable",
            },
            "negative_false_positive_rate": {
                "value": round(false_positives / len(negatives), 6) if negatives else None,
                "numerator": false_positives, "denominator": len(negatives),
                "status": "measured" if negatives else "not_applicable_zero_unanswerable",
            },
            "negative_abstention_rate": {
                "value": round(abstentions / len(negatives), 6) if negatives else None,
                "numerator": abstentions, "denominator": len(negatives),
                "status": "measured" if negatives else "not_applicable_zero_unanswerable",
            },
        }
    peak_rss = getattr(process.memory_info(), "peak_wset", None)
    index_bytes = sum(path.stat().st_size for path in index_dir.rglob("*") if path.is_file())
    review = binding["review"]
    blockers = ["answer_citation_groundedness_and_abstention_quality_not_measured_by_retrieval_runner"]
    if bound_review_path is None:
        blockers.extend([
            "benchmark_owner_review_pending",
            "provider_exposure_logs_not_audited",
            "benchmark_is_historical_or_previously_indexed_regression_only",
        ])
    else:
        blockers.extend([
            "benchmark_is_historical_phase7_exposure",
            "temporal_and_comparison_queries_not_present_in_selected_cohort",
        ])
    all_query_recall = {
        str(k): {"value": round(sum(per_query[row["qid"]]["recall"][str(k)] for row in rows) / len(rows), 6),
                 "numerator": round(sum(per_query[row["qid"]]["recall"][str(k)] for row in rows), 6),
                 "denominator": len(rows)}
        for k in (1, 3, 5, 10)
    }
    answerable_recall = {
        str(k): {"value": round(sum(per_query[qid]["recall"][str(k)] for qid in answerable) / len(answerable), 6),
                 "numerator": round(sum(per_query[qid]["recall"][str(k)] for qid in answerable), 6),
                 "denominator": len(answerable)}
        for k in (1, 3, 5, 10)
    }
    mrr_sum = sum(per_query[qid]["mrr"] for qid in answerable)
    false_positives = sum(bool(outputs[row["qid"]]) for row in rows if not row["answerable"])
    negative_count = len(rows) - len(answerable)
    per_split = split_metrics(rows, outputs, per_query, groups)
    return {
        "schema_version": 1, "phase": 8,
        "status": "retrieval_baseline_measured_phase8_incomplete",
        "gate_eligible": False,
        "benchmark": {
            "path": dataset.as_posix(), "source_sha256": sha256(dataset),
            "review_manifest_path": bound_review_path.as_posix() if bound_review_path else None,
            "review_manifest_sha256": sha256(bound_review_path) if bound_review_path else None,
            "review_status": review.get("status"), "review_mode": review.get("review_mode"),
            **{key: value for key, value in binding["selection"].items() if key != "group_by_qid"},
        },
        "runtime": {"python": sys.version, "platform": platform.platform(),
                    "index_manifest_sha256": sha256(manifest_path),
                    "calibration_sha256": sha256(calibration_path),
                    "model": manifest.get("model_name"), "model_revision": manifest.get("model_revision"),
                    "document_count": len(doc_ids), "index_size_bytes": index_bytes},
        "retrieval": {
            "mode": "auto", "records": len(rows), "answerable_denominator": len(answerable),
            "unanswerable_denominator": len(rows) - len(answerable),
            "recall_at_k": all_query_recall,
            "answerable_recall_at_k": answerable_recall,
            "answerable_mrr": {"value": round(mrr_sum / len(answerable), 6),
                                "numerator": round(mrr_sum, 6), "denominator": len(answerable)},
            "unanswerable_false_positive_rate": {
                "value": round(false_positives / negative_count, 6),
                "numerator": false_positives, "denominator": negative_count},
            "unanswerable_abstention_rate": {
                "value": round((negative_count - false_positives) / negative_count, 6),
                "numerator": negative_count - false_positives, "denominator": negative_count},
            "latency_ms": {**report["latency_ms"], "measured_requests": len(rows), "total_wall_ms": round(wall_ms, 3)},
            "tag_metrics": tag_metrics,
            "split_metrics": per_split,
            "group_bootstrap_ci95": {
                "answerable_recall_at_5": grouped_ci(recall_values, groups),
                "answerable_mrr": grouped_ci(mrr_values, groups),
            },
            "schema_invalid_rate": report["schema_invalid_rate"],
            "provenance_loss_rate": report["provenance_loss_rate"],
            "filter_leakage": report["filter_leakage"],
        },
        "resources": {"rss_before_bytes": rss_before,
                      "rss_after_bytes": process.memory_info().rss,
                      "peak_working_set_bytes": peak_rss,
                      "peak_working_set_status": "measured" if peak_rss is not None else "not_available_from_psutil"},
        "exposure": {"prior_phase7_exposure": True, "fresh_validation": False},
        "phase8_exit_blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    report = run(args.index_dir, args.calibration, args.benchmark, args.review_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "gate_eligible": report["gate_eligible"],
                      "records": report["benchmark"]["split_counts"],
                      "groups": report["benchmark"]["connected_groups"],
                      "retrieval": report["retrieval"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
