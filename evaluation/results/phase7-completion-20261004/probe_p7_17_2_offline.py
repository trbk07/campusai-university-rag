"""Record queue/counter behavior for an isolated late-completion shutdown probe."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
import json
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "evaluation/results/phase7-completion-20261004/p7-17-2-current-queue-probe-v2.json"


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate,
        RerankerUnavailable, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import source_identity, write_json

    if OUT.exists():
        raise FileExistsError(OUT)
    before_source = source_identity(ROOT)
    entered, release = Event(), Event()
    predict_calls = []

    class SlowModel:
        def predict(self, pairs, **kwargs):
            predict_calls.append(len(pairs))
            entered.set()
            if not release.wait(5):
                raise TimeoutError("probe_release_not_set")
            return [.5] * len(pairs)

    with tempfile.TemporaryDirectory(prefix="p7-17-2-", dir=ROOT / ".tmp") as model_tmp:
        snapshot = Path(model_tmp)
        (snapshot / "config.json").write_text("{}", encoding="utf-8")
        identity = ModelIdentity("fixture/slow-model", snapshot.name, snapshot_sha256(snapshot), snapshot.name)
        provider = OfflineCrossEncoderReranker(identity, snapshot, queue_limit=1,
                                               timeout_ms=5000, model_loader=lambda: SlowModel())
        candidate = [RerankCandidate("a", "doc", "a", 1, "evidence", 1, .2)]
        first_status = second_status = third_status = None
        before_close = after_close_before_release = after_drain = None
        try:
            with ThreadPoolExecutor(max_workers=2) as workers:
                first = workers.submit(provider.score, "first", candidate)
                if not entered.wait(3):
                    raise TimeoutError("model_did_not_enter")
                second = workers.submit(provider.score, "second", candidate)
                deadline = time.monotonic() + 3
                while provider.metrics_snapshot()["queue_depth"] != 1 and time.monotonic() < deadline:
                    time.sleep(.005)
                if provider.metrics_snapshot()["queue_depth"] != 1:
                    raise AssertionError("queued_request_not_observed")
                try:
                    provider.score("third", candidate)
                    third_status = "unexpected_success"
                except RerankerUnavailable as error:
                    third_status = str(error)
                before_close = provider.metrics_snapshot()
                provider.close()
                after_close_before_release = provider.metrics_snapshot()
                release.set()
                for name, future in (("first", first), ("second", second)):
                    try:
                        future.result(timeout=3)
                        status = "unexpected_success"
                    except RerankerUnavailable as error:
                        status = str(error)
                    if name == "first":
                        first_status = status
                    else:
                        second_status = status
                provider.drain()
                after_drain = provider.metrics_snapshot()
        finally:
            release.set()
            provider.close()
            provider.drain()

    checks = {
        "one_native_predict_entered": len(predict_calls) == 1,
        "queue_full_rejected_third": third_status == "queue_full",
        "submitted_is_two_before_close": before_close["submitted_requests"] == 2,
        "rejected_is_one_before_close": before_close["rejected_requests"] == 1,
        "active_and_queued_observed_before_close": before_close["active_requests"] == 1 and before_close["queue_depth"] == 1,
        "active_and_queued_zero_after_drain": after_drain["active_requests"] == 0 and after_drain["queue_depth"] == 0,
        "late_active_result_discarded": first_status == "feature_disabled",
        "queued_request_cancelled_as_disabled": second_status == "feature_disabled",
        "shutdown_cancellation_not_counted_as_provider_failure": after_drain["failure_count"] == 0,
        "no_inference_after_close": len(predict_calls) == 1,
        "completed_plus_cancelled_matches_submitted": after_drain["completed_requests"] + after_drain["cancelled_requests"] == after_drain["submitted_requests"],
    }
    after_source = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-17.2", "status": "PASS_OFFLINE_QUEUE_PROBE" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "isolated Python SlowModel fixture; synthetic late completion and queue pressure",
        "started_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before_source,
        "source_identity_after": after_source, "source_stable": before_source == after_source,
        "predict_batch_sizes": predict_calls, "future_status": {
            "queue_full_request": third_status, "inflight_after_close": first_status,
            "queued_after_close": second_status,
        }, "counters_before_close": before_close,
        "counters_after_close_before_release": after_close_before_release,
        "counters_after_drain": after_drain, "checks": checks,
        "limitations": [
            "The delayed model is a Python test double, not CUDA/native provider inference.",
            "Does not establish target-device permit behavior, real provider recovery, or M9 acceptance.",
        ],
    }
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "source_stable": report["source_stable"],
                      "checks": checks, "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
