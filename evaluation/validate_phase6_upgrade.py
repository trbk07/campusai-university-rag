"""Fail-closed Phase 6 upgrade gate across generated and human benchmarks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"missing:{path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"invalid_json:{path}")
        return {}


def validate(args) -> dict:
    errors: list[str] = []
    generated = read(args.generated, errors)
    human = read(args.human, errors)
    calibration = read(args.calibration, errors)
    performance = read(args.performance, errors)
    grounding = read(args.grounding, errors)
    generated_failures = read(args.generated_failures, errors)
    human_failures = read(args.human_failures, errors)
    index_hash = sha(args.index_manifest) if args.index_manifest.is_file() else None
    calibration_hash = sha(args.calibration) if args.calibration.is_file() else None
    if index_hash is None:
        errors.append("index_manifest_missing")
    if calibration.get("status") != "pass" or calibration.get("calibration_split") != "dev" or calibration.get("holdout_used") is not False:
        errors.append("calibration_gate")
    confidence = calibration.get("confidence_model", {})
    if confidence.get("kind") != "logistic" or not confidence.get("version") or not confidence.get("feature_schema"):
        errors.append("confidence_model_gate")
    if calibration.get("index_sha256") != index_hash:
        errors.append("calibration_index_mismatch")
    dev_path = Path("data/benchmark/phase6_retrieval_dev.jsonl")
    if calibration.get("training_split_sha256") != sha(dev_path):
        errors.append("calibration_dev_hash_mismatch")
    if generated.get("status") != "pass" or generated.get("benchmark_family") != "regression_generated":
        errors.append("generated_regression_gate")
    if generated.get("index_sha256") != index_hash or generated.get("calibration_sha256") != calibration_hash:
        errors.append("generated_provenance_mismatch")
    for split in ("primary_test", "primary_holdout"):
        metrics = generated.get(split, {})
        if metrics.get("quality", {}).get("answerable_recall", {}).get("5", 0) < .90:
            errors.append(f"{split}_recall")
        if metrics.get("negative", {}).get("false_positive_rate", 1) > .05:
            errors.append(f"{split}_negative_fpr")
        if metrics.get("provenance_loss_rate", 1) or metrics.get("filter_leakage", 1):
            errors.append(f"{split}_provenance_or_filter")
    if human.get("status") != "pass" or human.get("benchmark_family") != "human_natural":
        errors.append("human_natural_gate")
    if human.get("index_sha256") != index_hash or human.get("calibration_sha256") != calibration_hash:
        errors.append("human_provenance_mismatch")
    if not args.human_benchmark.is_file() or human.get("benchmark_sha256") != sha(args.human_benchmark):
        errors.append("human_benchmark_hash_mismatch")
    human_metrics = human.get("human_natural", {})
    auto = human_metrics.get("modes", {}).get("auto", {})
    if auto.get("quality", {}).get("answerable_recall", {}).get("5", 0) < .92:
        errors.append("human_recall")
    if human_metrics.get("hard_answerable_recall_at_5") is None or human_metrics["hard_answerable_recall_at_5"] < .88:
        errors.append("human_hard_recall")
    if human_metrics.get("exact_code_recall_at_5") is None or human_metrics["exact_code_recall_at_5"] < .99:
        errors.append("human_exact_code_recall")
    if auto.get("negative", {}).get("false_positive_rate", 1) > .05:
        errors.append("human_negative_fpr")
    if auto.get("provenance_loss_rate", 1) or auto.get("filter_leakage", 1):
        errors.append("human_provenance_or_filter")
    for name in ("auto_vs_bm25", "auto_vs_dense"):
        if human_metrics.get("paired_bootstrap", {}).get(name, {}).get("ci95", [-1])[0] <= 0:
            errors.append(f"human_paired_bootstrap:{name}")
    if performance.get("status") != "pass" or performance.get("error_rate") != 0 or performance.get("timeout_rate") != 0:
        errors.append("performance_gate")
    if performance.get("latency", {}).get("warm_p95_ms", 10**9) > 300:
        errors.append("warm_p95_above_300ms")
    if performance.get("concurrency", {}).get("20", {}).get("p99_ms", 10**9) > 1000:
        errors.append("concurrent_20_p99")
    peak = performance.get("memory", {}).get("peak_observed_rss_bytes", 0)
    if args.deployment_ram_bytes is None:
        errors.append("deployment_ram_budget_missing")
    elif peak <= 0 or peak > .75 * args.deployment_ram_bytes:
        errors.append("ram_headroom_below_25pct")
    grounding_metrics = grounding.get("metrics", {})
    required_grounding = {
        "unsupported_claim_leakage": 0.0,
        "contradicted_claim_leakage": 0.0,
        "schema_invalid_rate": 0.0,
        "citation_coordinate_validity": 1.0,
        "citation_precision": 1.0,
        "citation_recall": 1.0,
    }
    if not grounding_metrics or any(grounding_metrics.get(key) != expected
                                    for key, expected in required_grounding.items()):
        errors.append("grounding_regression_gate")
    retrieval_scope = grounding.get("phase6_retrieval", {})
    if (not args.grounding_benchmark.is_file()
            or grounding.get("benchmark_sha256") != sha(args.grounding_benchmark)
            or retrieval_scope.get("index_manifest_sha256") != index_hash
            or retrieval_scope.get("calibration_sha256") != calibration_hash):
        errors.append("grounding_provenance_mismatch")
    if not isinstance(generated_failures, list) or not isinstance(human_failures, list):
        errors.append("failure_case_exports_missing")
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    if args.require_clean and dirty:
        errors.append("working_tree_dirty")
    return {"schema_version": 1, "phase": 6, "status": "pass" if not errors else "conditional",
            "errors": sorted(set(errors)), "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "working_tree_clean": not dirty,
            "benchmark_families": {
                "regression_generated": {"report_sha256": sha(args.generated) if args.generated.is_file() else None},
                "human_natural": {"report_sha256": sha(args.human) if args.human.is_file() else None}},
            "confidence_model_sha256": calibration.get("confidence_model_sha256"),
            "deployment_ram_bytes": args.deployment_ram_bytes,
            "failure_cases": {"regression_generated": len(generated_failures) if isinstance(generated_failures, list) else None,
                              "human_natural": len(human_failures) if isinstance(human_failures, list) else None}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path, default=Path("evaluation/results/phase6_holdout_report.json"))
    parser.add_argument("--index-manifest", type=Path, default=Path(".tmp/phase6-index/manifest.json"))
    parser.add_argument("--human-benchmark", type=Path, default=Path("data/benchmark/phase6_human_natural.jsonl"))
    parser.add_argument("--grounding-benchmark", type=Path, default=Path("data/benchmark/phase6_grounding_scoped.jsonl"))
    parser.add_argument("--human", type=Path, default=Path("evaluation/results/phase6_human_natural_report.json"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--performance", type=Path, default=Path("evaluation/results/phase6_performance_report.json"))
    parser.add_argument("--grounding", type=Path, default=Path("evaluation/results/phase6_grounding_regression.json"))
    parser.add_argument("--generated-failures", type=Path, default=Path("evaluation/results/phase6_failure_cases_generated.json"))
    parser.add_argument("--human-failures", type=Path, default=Path("evaluation/results/phase6_failure_cases_human.json"))
    parser.add_argument("--deployment-ram-bytes", type=int)
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase6_upgrade_readiness.json"))
    args = parser.parse_args()
    report = validate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
