"""Independently recompute local HTTP pilot counters and latency summaries."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "evaluation/results/phase7-completion-20261004/p7-08-local-http-pilot.json"
OUTPUT = ROOT / "evaluation/results/phase7-completion-20261004/p7-08-recomputed.json"


def percentile(values, fraction):
    return sorted(values)[min(len(values) - 1, int(len(values) * fraction))]


def main():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    errors = []
    http = report["http_profile"]
    server = http["request_observations"]
    client = [sample for profile in http["profiles"] for sample in profile["samples"]]
    if len(server) != 400 or len({x["request_id"] for x in server}) != len(server):
        errors.append("server_request_identity_or_count")
    if {x["request_id"] for x in server} != {x["request_id"] for x in client}:
        errors.append("client_server_request_pairing")
    if any(not (x["route_selected"] and x["inference_attempted"] and x["inference_completed"]
                and x["ranking_applied"] and x["http_status"] == 200 and x["outcome"] == "completed")
           for x in server):
        errors.append("server_stage_or_http_outcome")
    for x in server:
        if x["cache_enabled"] or x["llm_stage_observed"]:
            errors.append("pilot_scope_changed")
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in
               (x["server_total_ms"], x["serialization_ms"], x["provider_trace"].get("queue_ms", -1),
                x["provider_trace"].get("inference_observed_ms", -1))):
            errors.append("invalid_stage_duration")
    profiles = []
    for profile in http["profiles"]:
        samples = profile["samples"]
        latencies = [sample["client_total_ms"] for sample in samples]
        successful = sum(sample["http_status"] == 200 and sample["error"] is None for sample in samples)
        ordered_latency = sorted(latencies)
        calculated = {"requests": len(samples), "successful": successful,
            # Match the measurement module's fixed discrete quantile indices exactly.
            "p50_ms": ordered_latency[int(.50 * len(ordered_latency))],
            "p95_ms": ordered_latency[int(.95 * len(ordered_latency)) - 1],
            "p99_ms": ordered_latency[int(.99 * len(ordered_latency)) - 1],
            "successful_rps": successful / profile["summary"]["duration_seconds"],
            "errors": sum(sample["http_status"] != 200 or sample["error"] is not None for sample in samples)}
        for key in ("requests", "errors"):
            if calculated[key] != profile["summary"][key]: errors.append(f"profile_{profile['concurrency']}_{key}_changed")
        for key in ("p50_ms", "p95_ms", "p99_ms", "successful_rps"):
            if not math.isclose(calculated[key], profile["summary"][key], rel_tol=1e-12, abs_tol=1e-9):
                errors.append(f"profile_{profile['concurrency']}_{key}_changed")
        profiles.append({"concurrency": profile["concurrency"], **calculated})
    resources = report["resource_samples"]
    resource_errors = []
    pids = {x["pid"] for x in resources}
    if len(resources) < 2 or len(pids) != 1 or any(type(pid) is not int or pid <= 0 for pid in pids):
        resource_errors.append("resource_pid_or_sample_count")
    for sample in resources:
        if datetime.fromisoformat(sample["at"].replace("Z", "+00:00")).tzinfo is None:
            resource_errors.append("resource_timestamp_timezone")
        for key in ("rss_bytes", "vram_capacity_bytes"):
            if type(sample[key]) is not int or sample[key] <= 0:
                resource_errors.append("resource_missing_" + key)
        if sample["vram_allocated_bytes"] <= 0 or sample["vram_reserved_bytes"] <= 0:
            resource_errors.append("resource_missing_gpu_memory")
    errors.extend(resource_errors)
    result = {"schema_version": 1, "task": "P7-08", "status": "PASS_COMPONENT_RECOMPUTE" if not errors else "FAIL",
        "release_eligible": False, "source_report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
        "request_count": len(server), "profile_count": len(profiles), "resource_sample_count": len(resources),
        "recomputed_profiles": profiles, "resource_errors": resource_errors,
        "server_stage_outcomes": {key: sum(bool(x[key]) for x in server) for key in
            ("route_selected", "inference_attempted", "inference_completed", "ranking_applied")},
        "provider_totals": report["provider_metrics_after_close"],
        "errors": errors, "limitations": report["limitations"],
        "recomputed_at": datetime.now(timezone.utc).isoformat()}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "errors": errors,
        "request_count": len(server), "resource_sample_count": len(resources),
        "p95_by_concurrency": {p["concurrency"]: p["p95_ms"] for p in profiles}}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
