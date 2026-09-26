"""Validate a Phase 5 report without hand-editable pass flags."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(report: dict) -> list[str]:
    metrics = report.get("metrics", {})
    errors = []
    if report.get("mode") != "runtime":
        errors.append("release_requires_runtime_mode")
    if not report.get("benchmark_sha256"):
        errors.append("benchmark_checksum_missing")
    if not report.get("metadata", {}).get("commit"):
        errors.append("commit_fingerprint_missing")
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
    for split in ("dev", "test", "holdout"):
        split_metrics = calibration.get(split, {})
        if split_metrics.get("count", 0) <= 0:
            errors.append(f"calibration_{split}_missing")
    if calibration.get("holdout", {}).get("ece", 1) > 0.05:
        errors.append("holdout_ece")
    if calibration.get("holdout", {}).get("brier_score", 1) > 0.08:
        errors.append("holdout_brier_score")
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
