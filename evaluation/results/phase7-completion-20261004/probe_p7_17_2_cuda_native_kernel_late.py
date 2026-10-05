"""Hold an active provider request on a real CUDA kernel across close/drain."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
import json
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-17-2-current-cuda-native-kernel-late.json"
KERNEL_CYCLES = 2_000_000_000


def outcome(provider, query, candidate):
    from campusai.retrieval.cross_encoder_provider import RerankerUnavailable
    try:
        provider.score(query, [candidate])
        return "unexpected_success"
    except RerankerUnavailable as error:
        return str(error)


def main() -> int:
    import torch
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate,
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
    native_kernel_queued = Event()
    actual_calls = []
    real_model = retrieval_runtime().get_offline_reranker(
        model_dir, device="cuda", max_length=identity.max_length,
        snapshot_sha256=identity.model_sha256, dtype=identity.dtype,
    )

    class SlowNativeCompletion:
        def predict(self, pairs, **kwargs):
            scores = real_model.predict(pairs, **kwargs)
            actual_calls.append(len(pairs))
            torch.cuda._sleep(KERNEL_CYCLES)
            native_kernel_queued.set()
            torch.cuda.synchronize()
            return scores

    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=300,
                                           queue_limit=1, score_cache_size=0,
                                           model_loader=lambda: SlowNativeCompletion())
    candidate = RerankCandidate("candidate-1", "doc-1", "chunk-1", 1,
                                "Course prerequisite and semester record.", 1, 0.5)
    callers = ThreadPoolExecutor(max_workers=2)
    try:
        first_future = callers.submit(outcome, provider, "course prerequisite", candidate)
        if not native_kernel_queued.wait(60):
            raise TimeoutError("CUDA native kernel was not enqueued")
        first_outcome = first_future.result(timeout=10)
        second_future = callers.submit(outcome, provider, "second queued request", candidate)
        deadline = time.monotonic() + 5
        while provider.metrics_snapshot()["queue_depth"] != 1 and time.monotonic() < deadline:
            time.sleep(0.005)
        before_close = provider.metrics_snapshot()
        permits_before_close = provider._permits._value
        close_started = time.perf_counter()
        provider.close()
        closed_before_drain = provider.metrics_snapshot()
        permits_closed_before_drain = provider._permits._value
        second_outcome = second_future.result(timeout=5)
        try:
            provider.score("post-close", [candidate])
            post_close = "unexpected_success"
        except Exception as error:
            post_close = str(error)
        inference_calls_after_reject = provider.metrics_snapshot()["inference_calls"]
        provider.drain(timeout_ms=60000)
        drain_ms = (time.perf_counter() - close_started) * 1000
        after_drain = provider.metrics_snapshot()
        permits_after_drain = provider._permits._value
    finally:
        provider.close()
        callers.shutdown(wait=True, cancel_futures=True)

    checks = {
        "real_model_and_native_cuda_kernel_ran": actual_calls == [1] and after_drain["inference_calls"] == 1,
        "active_request_timed_out": first_outcome == "reranker_timeout",
        "active_and_queued_requests_present_before_close": before_close["active_requests"] == 1 and before_close["queue_depth"] == 1,
        "permit_held_for_running_native_operation": permits_before_close == 0 and permits_closed_before_drain == 1,
        "close_cancelled_only_queued_request": second_outcome == "feature_disabled" and after_drain["cancelled_requests"] == 1,
        "native_operation_completed_after_close": drain_ms > 150 and closed_before_drain["active_requests"] == 1 and after_drain["active_requests"] == 0,
        "no_new_inference_after_close": post_close == "feature_disabled" and inference_calls_after_reject == 1,
        "both_permits_returned_after_drain": permits_after_drain == 2,
        "counters_reconcile": after_drain["submitted_requests"] == after_drain["completed_requests"] + after_drain["cancelled_requests"],
        "snapshot_identity_verified": snapshot_sha256(model_dir) == identity.model_sha256,
    }
    report = {
        "schema_version": 1, "task": "P7-17.2", "status": "PASS_PINNED_CUDA_NATIVE_KERNEL_LATE_COMPLETION" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "pinned CrossEncoder GPU inference followed by an actual CUDA sleep kernel whose synchronization completes after provider close; concurrent queued caller cancelled",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before,
        "source_identity_after": source_identity(ROOT), "model_identity": identity.to_dict(),
        "model_snapshot_sha256": snapshot_sha256(model_dir), "torch_version": torch.__version__,
        "cuda_device": torch.cuda.get_device_name(0), "kernel_cycles": KERNEL_CYCLES,
        "actual_model_predict_batch_sizes": actual_calls, "first_outcome": first_outcome,
        "queued_outcome": second_outcome, "post_close_outcome": post_close,
        "close_to_drain_ms": drain_ms,
        "permit_values": {"before_close": permits_before_close,
                          "after_queue_cancel_while_native_active": permits_closed_before_drain,
                          "after_drain": permits_after_drain},
        "counters_before_close": before_close, "counters_closed_before_drain": closed_before_drain,
        "counters_after_drain": after_drain, "checks": checks,
        "limitations": [
            "This executes a real CUDA sleep kernel after pinned cross-encoder inference to exercise native stream completion; the delay is controlled test work, not a naturally hung model kernel or GPU-driver fault.",
            "No production HTTP server, process rollback, driver reset, or M9 release acceptance is exercised.",
        ],
    }
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "checks": checks,
                      "close_to_drain_ms": drain_ms, "permit_values": report["permit_values"],
                      "cuda_device": report["cuda_device"], "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or report["source_identity_before"] != report["source_identity_after"])


if __name__ == "__main__":
    raise SystemExit(main())
