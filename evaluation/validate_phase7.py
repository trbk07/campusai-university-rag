"""Fail-closed Phase 7 release gate; no partial score can masquerade as 10/10."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path, errors: list[str], name: str) -> dict:
    if not path.is_file():
        errors.append(f"missing_{name}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append(f"invalid_{name}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"invalid_{name}")
        return {}
    return value


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _number(value: object, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    result = float(value)
    return result if math.isfinite(result) else default


def validate(args: argparse.Namespace) -> dict:
    errors: list[str] = []
    baseline = _read(args.baseline, errors, "baseline")
    candidate = _read(args.candidate, errors, "candidate")
    route = _read(args.route, errors, "route")
    smoke = _read(args.smoke, errors, "model_smoke")
    calibration = _read(args.calibration, errors, "calibration")
    quality = _read(args.quality, errors, "quality")
    performance = _read(args.performance, errors, "performance")
    grounding = _read(args.grounding, errors, "grounding")
    security = _read(args.security, errors, "security")
    failure_matrix = _read(args.failure_matrix, errors, "failure_matrix")
    rollback = _read(args.rollback, errors, "rollback")
    staging = _read(args.staging, errors, "staging")
    if baseline.get("status") != "pass" or baseline.get("working_tree_clean") is not True:
        errors.append("phase6_baseline_gate")
    if candidate.get("status") != "pass" or candidate.get("index_sha256") != baseline.get("index_sha256"):
        errors.append("candidate_provenance_gate")
    for split, floor in (("test", .99), ("holdout", .97)):
        metrics = _object(_object(_object(_object(candidate.get("splits")).get(split)).get("caps")).get("40"))
        if (_number(metrics.get("candidate_recall"), 0) < floor
                or metrics.get("provenance_errors", 1)
                or metrics.get("scope_errors", 1)
                or metrics.get("duplicate_result_sets", 1)):
            errors.append(f"candidate_{split}_gate")
    route_metrics = _object(route.get("routing_metrics"))
    if (route.get("status") != "pass" or route.get("calibration_split") != "dev"
            or route.get("holdout_used") is not False
            or route.get("index_sha256") != baseline.get("index_sha256")
            or _number(route_metrics.get("hard_recall"), 0) < .95
            or _number(route_metrics.get("easy_unnecessary_rerank_rate"), 1) > .20):
        errors.append("hard_route_gate")
    if smoke.get("status") != "pass" or not smoke.get("model_identity_sha256"):
        errors.append("offline_model_gate")
    if (calibration.get("status") != "pass" or calibration.get("calibration_split") != "dev"
            or calibration.get("holdout_used") is not False
            or calibration.get("index_sha256") != baseline.get("index_sha256")
            or calibration.get("model_identity_sha256") != smoke.get("model_identity_sha256")
            or calibration.get("route_calibration_sha256") != _sha(args.route)
            or calibration.get("training_split_sha256") != route.get("training_split_sha256")
            or calibration.get("candidate_cap") != 40
            or _number(calibration.get("recall"), 0) < .95
            or _number(calibration.get("false_positive_rate"), 1) > .01):
        errors.append("reranker_calibration_gate")
    if quality.get("status") != "pass":
        errors.append("quality_report_gate")
    for split in ("test", "holdout"):
        metrics = _object(quality.get(split))
        if (_number(metrics.get("mrr_improvement_relative"), -1) < .03
                or _number(metrics.get("ndcg5_improvement_relative"), -1) < .03
                or _number(metrics.get("recall5_drop_absolute"), 1) > .005
                or metrics.get("negative_fpr", 1) != 0
                or metrics.get("provenance_leakage", 1) != 0
                or metrics.get("scope_leakage", 1) != 0):
            errors.append(f"quality_{split}_gate")
    statistical = _object(quality.get("paired_statistics"))
    ci95 = statistical.get("mrr_ci95")
    lower_ci = ci95[0] if isinstance(ci95, list) and ci95 else None
    if (_number(statistical.get("bootstrap_resamples"), 0) < 10000
            or _number(lower_ci, -1) <= 0):
        errors.append("statistical_significance_gate")
    if (performance.get("status") != "pass"
            or _number(performance.get("overall_warm_p95_ms"), 10**9) > 500
            or _number(performance.get("hard_query_p95_ms"), 10**9) > 1000
            or _number(performance.get("concurrency_20_p99_ms"), 10**9) > 1000
            or performance.get("errors", 1) or performance.get("timeouts", 1)):
        errors.append("performance_gate")
    peak = _number(performance.get("peak_rss_bytes"), 0)
    if args.deployment_ram_bytes is None or peak <= 0 or peak > .75 * args.deployment_ram_bytes:
        errors.append("deployment_ram_headroom_gate")
    if grounding.get("status") != "pass" or grounding.get("phase4_5_regression") != "pass":
        errors.append("grounding_regression_gate")
    if (security.get("status") != "pass" or _number(security.get("adversarial_cases"), 0) < 50
            or security.get("provenance_leakage", 1) or security.get("scope_leakage", 1)):
        errors.append("security_adversarial_gate")
    for name, report in (("failure_matrix", failure_matrix), ("rollback", rollback),
                         ("staging", staging)):
        if report.get("status") != "pass":
            errors.append(f"{name}_gate")
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    if dirty:
        errors.append("working_tree_dirty")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {"schema_version": 1, "phase": 7,
            "status": "pass" if not errors else "conditional",
            "score": 10.0 if not errors else None,
            "errors": sorted(set(errors)), "commit": commit,
            "working_tree_clean": not dirty,
            "base_release": "phase6-rc3",
            "model_identity_sha256": smoke.get("model_identity_sha256"),
            "index_sha256": baseline.get("index_sha256"),
            "calibration_sha256": _sha(args.calibration),
            "deployment_ram_bytes": args.deployment_ram_bytes}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path("evaluation/results/phase7_baseline_manifest.json"))
    parser.add_argument("--candidate", type=Path, default=Path("evaluation/results/phase7_candidate_recall.json"))
    parser.add_argument("--route", type=Path, default=Path("evaluation/results/phase7_route_calibration.json"))
    parser.add_argument("--smoke", type=Path, default=Path("evaluation/results/phase7_model_smoke.json"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/phase7_reranker_calibration.json"))
    parser.add_argument("--quality", type=Path, default=Path("evaluation/results/phase7_quality_comparison.json"))
    parser.add_argument("--performance", type=Path, default=Path("evaluation/results/phase7_performance.json"))
    parser.add_argument("--grounding", type=Path, default=Path("evaluation/results/phase7_grounding_regression.json"))
    parser.add_argument("--security", type=Path, default=Path("evaluation/results/phase7_security.json"))
    parser.add_argument("--failure-matrix", type=Path, default=Path("evaluation/results/phase7_failure_matrix.json"))
    parser.add_argument("--rollback", type=Path, default=Path("evaluation/results/phase7_rollback.json"))
    parser.add_argument("--staging", type=Path, default=Path("evaluation/results/phase7_staging.json"))
    parser.add_argument("--deployment-ram-bytes", type=int)
    parser.add_argument("--output", type=Path, default=Path(".tmp/phase7-readiness.json"))
    args = parser.parse_args()
    report = validate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
