"""Validate a Phase 5 report without hand-editable pass flags."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.benchmarks.benchmark_schema import validate_release_records


def validate(report: dict) -> list[str]:
    metrics = report.get("metrics", {})
    errors = []
    if report.get("mode") != "runtime":
        errors.append("release_requires_runtime_mode")
    if report.get("schema_version") != 2:
        errors.append("report_schema_version_invalid")
    if not report.get("policy_version"):
        errors.append("policy_version_missing")
    if not report.get("benchmark_sha256"):
        errors.append("benchmark_checksum_missing")
    if not report.get("metadata", {}).get("commit"):
        errors.append("commit_fingerprint_missing")
    if report.get("metadata", {}).get("working_tree") is not False:
        errors.append("working_tree_dirty")
    dataset = report.get("dataset", {})
    if dataset.get("sha256") and report.get("benchmark_sha256") != dataset.get("sha256"):
        errors.append("benchmark_checksum_mismatch")
    if report.get("calibration_artifact_version") and not report.get("calibration_artifact_sha256"):
        errors.append("calibration_checksum_missing")
    if report.get("mode") == "runtime" and not report.get("calibration_artifact_version"):
        errors.append("runtime_calibration_missing")
    if report.get("mode") == "runtime" and not report.get("calibration_artifact_sha256"):
        errors.append("runtime_calibration_checksum_missing")
    if report.get("mode") == "runtime":
        if report.get("calibration_benchmark_sha256") != report.get("benchmark_sha256"):
            errors.append("calibration_benchmark_checksum_mismatch")
        population = report.get("calibration_population") or {}
        for split in ("dev", "test", "holdout"):
            labels = population.get(split, {})
            if labels.get("positive", 0) <= 0 or labels.get("negative", 0) <= 0:
                errors.append(f"calibration_{split}_label_degenerate")
    rows = report.get("rows")
    if report.get("mode") == "runtime":
        if not isinstance(rows, list):
            errors.append("report_rows_missing")
        else:
            errors.extend(f"dataset_{error}" for error in validate_release_records(rows))
            if report.get("dataset_count") != len(rows):
                errors.append("dataset_count_rows_mismatch")
    if metrics.get("unsupported_claim_leakage", 1) != 0:
        errors.append("unsupported_claim_leakage")
    if metrics.get("contradicted_claim_leakage", 0) != 0:
        errors.append("contradicted_claim_leakage")
    if metrics.get("citation_precision", 0) < 0.99:
        errors.append("citation_precision")
    if metrics.get("citation_recall", 0) < 0.98:
        errors.append("citation_recall")
    if metrics.get("citation_completeness", 0) < 0.98:
        errors.append("citation_completeness")
    if metrics.get("citation_coordinate_validity", 0) < 1.0:
        errors.append("citation_coordinate_validity")
    if metrics.get("claim_citation_precision", 0) < 0.95:
        errors.append("claim_citation_precision")
    if metrics.get("claim_citation_recall", 0) < 0.95:
        errors.append("claim_citation_recall")
    if metrics.get("claim_citation_f1", 0) < 0.95:
        errors.append("claim_citation_f1")
    if metrics.get("grounded_claim_precision", 0) < 0.99:
        errors.append("grounded_claim_precision")
    if metrics.get("grounded_claim_recall", 0) < 0.95:
        errors.append("grounded_claim_recall")
    if metrics.get("schema_invalid_rate", 1) != 0:
        errors.append("schema_invalid_rate")
    if metrics.get("abstention_precision", 0) < 0.99:
        errors.append("abstention_precision")
    if metrics.get("abstention_recall", 0) < 0.98:
        errors.append("abstention_recall")
    if metrics.get("reason_accuracy", 0) < 0.95:
        errors.append("reason_accuracy")
    if metrics.get("ece", 1) > 0.05:
        errors.append("ece")
    if metrics.get("brier_score", 1) > 0.08:
        errors.append("brier_score")
    if metrics.get("calibration_count", 0) < 400:
        errors.append("calibration_sample_too_small")
    if report.get("dataset_count", 0) < 400:
        errors.append("dataset_too_small_for_release")
    calibration = report.get("calibration", {})
    if report.get("mode") == "runtime" and report.get("risk_population") != "holdout":
        errors.append("risk_population_must_be_holdout")
    for split in ("dev", "test", "holdout"):
        split_metrics = calibration.get(split, {})
        if split_metrics.get("count", 0) <= 0:
            errors.append(f"calibration_{split}_missing")
        if split not in report.get("split_metrics", {}):
            errors.append(f"split_metrics_{split}_missing")
    if not isinstance(report.get("category_metrics"), dict) or not report.get("category_metrics"):
        errors.append("category_metrics_missing")
    if calibration.get("holdout", {}).get("ece", 1) > 0.05:
        errors.append("holdout_ece")
    if calibration.get("holdout", {}).get("brier_score", 1) > 0.08:
        errors.append("holdout_brier_score")
    for coverage, maximum in ((0.80, 0.01), (0.90, 0.02)):
        risk = report.get("risk_at_coverage", {}).get(str(coverage))
        if risk is None:
            errors.append(f"risk_at_{int(coverage * 100)}_coverage_missing")
        elif risk > maximum:
            errors.append(f"risk_at_{int(coverage * 100)}_coverage")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    errors = validate(report)
    print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
