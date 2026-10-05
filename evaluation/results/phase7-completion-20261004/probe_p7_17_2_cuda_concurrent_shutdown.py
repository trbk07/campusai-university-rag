"""Run one pinned CUDA inference with a concurrent queued request through close/drain."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
import json
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-17-2-current-cuda-concurrent-shutdown.json"


def score_outcome(provider, query, candidate):
    try:
        provider.score(query, [candidate])
        return "unexpected_success"
    except Exception as error:
        return str(error) if type(error).__name__ == "RerankerUnavailable" else type(error).__name__


def main() -> int:
    import torch
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, RerankerUnavailable,
        snapshot_sha256,
    )
    from campusai.retrieval.model_runtime import retrieval_runtime
    from evaluation.common.release_artifacts import source_identity, write_json

    if OUT.exists():
        raise FileExistsError(OUT)
    smoke = json.loads((TASK / "p7-07-cuda-snapshot-smoke.json").read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    if identity.device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("pinned CUDA identity/device is unavailable")
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if snapshot_sha256(model_dir) != identity.model_sha256:
        raise ValueError("pinned model snapshot hash mismatch")
    before = source_identity(ROOT)
    entered, release = Event(), Event()
    actual_batches = []
    real_model = retrieval_runtime().get_offline_reranker(
        model_dir, device="cuda", max_length=identity.max_length,
        snapshot_sha256=identity.model_sha256, dtype=identity.dtype,
    )

    class WithheldFirstResult:
        def predict(self, pairs, **kwargs):
            values = real_model.predict(pairs, **kwargs)
            torch.cuda.synchronize()
            actual_batches.append(len(pairs))
            entered.set()
            if not release.wait(20):
                raise TimeoutError("late_result_release_not_set")
            return values

    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=300,
                                           queue_limit=1, score_cache_size=0,
                                           model_loader=lambda: WithheldFirstResult())
    candidate = RerankCandidate("candidate-1", "doc-1", "chunk-1", 1,
                                "Course prerequisite and semester record.", 1, 0.5)
    client_pool = ThreadPoolExecutor(max_workers=2)
    first_future = second_future = None
    try:
        first_future = client_pool.submit(score_outcome, provider, "course prerequisite", candidate)
        if not entered.wait(60):
            raise TimeoutError("real CUDA inference did not complete")
        first_outcome = first_future.result(timeout=5)
        if first_outcome != "reranker_timeout":
            raise AssertionError(f"first request did not timeout: {first_outcome}")
        second_future = client_pool.submit(score_outcome, provider, "second concurrent request", candidate)
        deadline = time.monotonic() + 5
        while provider.metrics_snapshot()["queue_depth"] != 1 and time.monotonic() < deadline:
            time.sleep(0.005)
        before_close = provider.metrics_snapshot()
        permits_before_close = provider._permits._value
        provider.close()
        closed_before_release = provider.metrics_snapshot()
        permits_closed_before_release = provider._permits._value
        second_outcome = second_future.result(timeout=5)
        try:
            provider.score("after close", [candidate])
            post_close_outcome = "unexpected_success"
        except RerankerUnavailable as error:
            post_close_outcome = str(error)
        inference_calls_after_rejection = provider.metrics_snapshot()["inference_calls"]
        release.set()
        provider.drain(timeout_ms=60000)
        after_drain = provider.metrics_snapshot()
        permits_after_drain = provider._permits._value
    finally:
        release.set()
        provider.close()
        provider.drain(timeout_ms=60000)
        client_pool.shutdown(wait=True, cancel_futures=True)

    checks = {
        "one_real_pinned_cuda_inference_completed": actual_batches == [1] and after_drain["inference_calls"] == 1,
        "active_request_timed_out_without_early_permit_release": first_outcome == "reranker_timeout" and permits_before_close == 0,
        "one_request_queued_behind_active_work": before_close["active_requests"] == 1 and before_close["queue_depth"] == 1,
        "close_cancelled_queued_request": second_outcome == "feature_disabled" and after_drain["cancelled_requests"] == 1,
        "active_permit_remained_held_after_close": permits_closed_before_release == 1 and closed_before_release["active_requests"] == 1,
        "post_close_admission_rejected_without_new_inference": post_close_outcome == "feature_disabled" and inference_calls_after_rejection == 1,
        "late_active_result_drained": after_drain["active_requests"] == 0 and after_drain["queue_depth"] == 0,
        "all_two_admission_permits_returned_after_drain": permits_after_drain == 2,
        "submitted_completed_cancelled_reconcile": after_drain["submitted_requests"] == after_drain["completed_requests"] + after_drain["cancelled_requests"],
        "model_snapshot_identity_matches": snapshot_sha256(model_dir) == identity.model_sha256,
    }
    report = {
        "schema_version": 1, "task": "P7-17.2", "status": "PASS_PINNED_CUDA_CONCURRENT_SHUTDOWN_PROBE" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "pinned RTX 4060 CrossEncoder inference; two concurrent callers; one actual score result withheld, queued caller cancelled through close/drain",
        "started_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before,
        "source_identity_after": source_identity(ROOT), "model_identity": identity.to_dict(),
        "model_snapshot_sha256": snapshot_sha256(model_dir), "torch_version": torch.__version__,
        "cuda_device": torch.cuda.get_device_name(0), "first_outcome": first_outcome,
        "queued_outcome": second_outcome, "post_close_outcome": post_close_outcome,
        "actual_predict_batch_sizes": actual_batches,
        "permit_values": {"before_close": permits_before_close,
                          "after_queued_cancel_while_active": permits_closed_before_release,
                          "after_drain": permits_after_drain},
        "counters_before_close": before_close, "counters_closed_before_release": closed_before_release,
        "counters_after_drain": after_drain, "checks": checks,
        "limitations": [
            "The pinned CUDA model is real, but a wrapper withholds its returned score after CUDA synchronization; this tests provider queue/permit lifecycle, not a hung/late CUDA kernel or driver fault.",
            "No production service process, public runtime, or M9 release gate is exercised.",
        ],
    }
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "checks": checks,
                      "permit_values": report["permit_values"], "cuda_device": report["cuda_device"],
                      "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or report["source_identity_before"] != report["source_identity_after"])


if __name__ == "__main__":
    raise SystemExit(main())
