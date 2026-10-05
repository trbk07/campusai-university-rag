"""Persist P7-17.4 offline permanent/transient fault evidence and validation."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
RAW_IN = ROOT / ".tmp/phase7-p7-17-4-current/reranker_fault_checks.json"
RAW_OUT = TASK / "p7-17-4-current-fault-matrix-raw.json"
TRANSIENT = TASK / "p7-17-4-current-transient-recovery.json"
FALLBACK = TASK / "p7-17-3-current-phase6-fallback-v2.json"
QUEUE = TASK / "p7-17-2-current-queue-probe-v2.json"
OUT = TASK / "p7-17-4_validation.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if RAW_OUT.exists() or OUT.exists():
        raise FileExistsError("P7-17.4 evidence exists; use a new attempt suffix")
    raw = json.loads(RAW_IN.read_text(encoding="utf-8"))
    transient = json.loads(TRANSIENT.read_text(encoding="utf-8"))
    fallback = json.loads(FALLBACK.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    all_permanent = [item for item in raw["observations"] if item.get("permanent") is True]
    checks = {
        "all_30_fault_matrix_checks_pass": len(raw["checks"]) == 30 and all(raw["checks"].values()),
        "permanent_faults_disable_phase7": bool(all_permanent) and all(item["phase7_enabled_after"] is False for item in all_permanent),
        "permanent_faults_close_provider": bool(all_permanent) and all(item["provider_closed"] is True for item in all_permanent),
        "permanent_faults_have_zero_followup_inference": bool(all_permanent) and all(item["provider_calls_after_followup"] == item["provider_calls_at_fault"] for item in all_permanent),
        "permanent_faults_preserve_phase6": bool(all_permanent) and all(item["baseline_preserved"] for item in all_permanent),
        "transient_provider_recovers": transient["status"] == "PASS_DEV_TRANSIENT_RECOVERY" and all(transient["checks"].values()),
        "phase6_fallback_matches_exactly_on_dev_groups": fallback["status"] == "PASS_DEV_REAL_INDEX_PHASE6_FALLBACK" and fallback["checks"]["all_fallback_outputs_exactly_match_phase6"],
        "queue_shutdown_counters_reconcile": queue["status"] == "PASS_OFFLINE_QUEUE_PROBE" and all(queue["checks"].values()),
    }
    RAW_OUT.write_bytes(RAW_IN.read_bytes())
    report = {
        "schema_version": 1, "task": "P7-17.4", "status": "PASS_OFFLINE_FAULT_SUBTASK" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "permanent fault shutdown, transient recovery, Phase 6 fallback, and queue-drain offline evidence",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
        "permanent_cases": [item["case"] for item in all_permanent],
        "permanent_case_count": len(all_permanent),
        "fault_matrix_raw": {"path": RAW_OUT.relative_to(ROOT).as_posix(), "sha256": sha(RAW_OUT)},
        "transient_recovery": {"path": TRANSIENT.relative_to(ROOT).as_posix(), "sha256": sha(TRANSIENT)},
        "phase6_fallback": {"path": FALLBACK.relative_to(ROOT).as_posix(), "sha256": sha(FALLBACK)},
        "queue_probe": {"path": QUEUE.relative_to(ROOT).as_posix(), "sha256": sha(QUEUE)},
        "limitations": [
            "The full fault matrix uses controlled Python test doubles; active-index probes still use test-double reranker providers.",
            "No permanent or transient fault has yet been induced in the real CUDA/native provider on its target runtime.",
            "Does not establish M9/P7-17 completion, target device permits, or resource leak limits.",
        ],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": checks,
                      "permanent_case_count": len(all_permanent), "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()))


if __name__ == "__main__":
    raise SystemExit(main())
