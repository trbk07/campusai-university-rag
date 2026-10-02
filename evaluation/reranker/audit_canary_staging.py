"""Audit real staging telemetry and fault windows; never manufacture observations."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from campusai.retrieval.canary_rollout import CanaryController
from evaluation.reranker.canary_telemetry import audit_window
from evaluation.common.release_artifacts import read_json, require_previous_gates, sha256, source_identity, write_json, policy_bindings

ROLLBACK_REASONS = {"provenance_error", "scope_leakage", "citation_error", "timeout_budget",
                    "negative_fpr_budget", "error_rate_regression", "memory_budget", "latency_budget_three_windows"}


def audit_staging(data: dict, faults: dict, *, evidence=None) -> dict:
    if data.get("environment") != "staging" or not data.get("environment_id") or not data.get("collector"):
        raise ValueError("staging environment identity and collector required")
    windows = data.get("windows")
    if not isinstance(windows, list) or len(windows) < 15:
        raise ValueError("at least 15 staging windows required")
    controller = CanaryController()
    last_end = None
    observed_steps = []
    step_counts = Counter()
    for window in windows:
        start = datetime.fromisoformat(window["started_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(window["ended_at"].replace("Z", "+00:00"))
        if start.tzinfo is None or end.tzinfo is None or end <= start or (last_end and start < last_end):
            raise ValueError("staging windows must have nonoverlapping time intervals and timezones")
        last_end = end
        if controller.observe(window):
            raise ValueError("healthy staging observations triggered rollback")
        if (window["p95_ms"] > 1000 or window["p99_ms"] > 2000
                or (window["traffic_percent"] and (window["easy_unnecessary_rerank_rate"] > .25
                                                   or window["hard_query_coverage"] < .90))):
            raise ValueError("every healthy staging window must meet latency and routing budgets")
        audit_window(window, evidence)
        step_counts[window["traffic_percent"]] += 1
        if not observed_steps or observed_steps[-1] != window["traffic_percent"]:
            observed_steps.append(window["traffic_percent"])
    if observed_steps != [0, 1, 5, 10, 25]:
        raise ValueError("all gradual rollout steps required in order")
    if any(step_counts[step] < 3 for step in observed_steps):
        raise ValueError("three healthy windows required at every step, including 25%")
    # Each failure is a separate observed staging exercise, including the
    # service's disabled state and proof of no new inference after rollback.
    exercises = faults.get("exercises", [])
    checks = {}
    for exercise in exercises:
        expected = exercise["expected_reason"]
        if expected not in ROLLBACK_REASONS or expected in checks:
            raise ValueError("invalid or duplicate rollback exercise")
        seen = []
        controlled = CanaryController(rollback=seen.append)
        for window in windows:
            controlled.observe(window)
        reason = None
        for window in exercise["windows"]:
            audit_window(window, evidence)
            reason = controlled.observe(window)
        checks[expected] = (reason == expected and seen == [expected] and controlled.traffic_percent == 0
                            and exercise.get("service_phase7_enabled_after") is False
                            and exercise.get("provider_closed_after") is True
                            and type(exercise.get("provider_calls_before_followup")) is int
                            and exercise["provider_calls_before_followup"] == exercise.get("provider_calls_after_followup")
                            and exercise.get("new_reranker_calls_after") == 0
                            and exercise.get("observed_reason") == expected
                            and type(exercise.get("injected_service_calls")) is int
                            and exercise["injected_service_calls"] >= 100
                            and isinstance(exercise.get("followup_probes"), list) and len(exercise["followup_probes"]) >= 3
                            and all(probe["output"] == probe["baseline"] for probe in exercise["followup_probes"]))
    if set(checks) != ROLLBACK_REASONS or not all(checks.values()):
        raise ValueError("staging auto-rollback exercises incomplete or failed")
    return {"status": "pass", "environment": "staging", "environment_id": data["environment_id"],
            "collector": data["collector"], "rollout_percentages": observed_steps,
            "auto_rollback_tested": True, "auto_rollback_checks": checks,
            "windows": windows, "fault_exercises": exercises}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--fault-observations", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    args = parser.parse_args()
    require_previous_gates("M11", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    data, faults = read_json(args.observations), read_json(args.fault_observations)
    smoke = read_json(args.results_dir / "model_snapshot_smoke.json")
    bindings = {**source_identity(Path(__file__).resolve().parents[2]), "index_sha256": sha256(args.index_dir / "manifest.json"),
                **policy_bindings(args.results_dir),
                "phase6_calibration_sha256": sha256(args.results_dir / "hybrid_retrieval_calibration.json"),
                "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
                "model_identity_sha256": smoke["model_identity_sha256"]}
    if any(data.get(key) != value or faults.get(key) != value for key, value in bindings.items() if key != "commit"):
        raise ValueError("staging telemetry source/model/index/calibration binding mismatch")
    from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
    report = audit_staging(data, faults, evidence=frozen_evidence(args.index_dir))
    report.update(bindings, observations_sha256=sha256(args.observations), faults_sha256=sha256(args.fault_observations))
    write_json(args.results_dir / "reranker_staging.json", report)
    write_json(args.results_dir / "canary_observations.json", {"status": "pass", **bindings,
               "windows": report["windows"], "staging_sha256": sha256(args.results_dir / "reranker_staging.json")})
    print(json.dumps({"status": report["status"], "windows": len(report["windows"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
