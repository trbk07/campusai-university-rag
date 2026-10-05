"""Exercise real pinned CUDA scoring with a withheld result during shutdown."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
import json
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-17-2-current-cuda-late-result-v2.json"


def main() -> int:
    import torch
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate,
        RerankerUnavailable, snapshot_sha256,
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
    call_count = []
    real_model = retrieval_runtime().get_offline_reranker(
        model_dir, device="cuda", max_length=identity.max_length,
        snapshot_sha256=identity.model_sha256, dtype=identity.dtype,
    )

    class WithheldResult:
        def predict(self, pairs, **kwargs):
            # Run actual pinned model inference first, then hold its result so close
            # occurs while the admitted provider request is still outstanding.
            values = real_model.predict(pairs, **kwargs)
            call_count.append(len(pairs))
            torch.cuda.synchronize()
            entered.set()
            if not release.wait(20):
                raise TimeoutError("late_result_release_not_set")
            return values

    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=300,
                                           queue_limit=0, score_cache_size=0,
                                           model_loader=lambda: WithheldResult())
    candidate = [RerankCandidate("candidate-1", "doc-1", "chunk-1", 1,
                                 "Course prerequisite and semester record.", 1, 0.5)]
    started = time.perf_counter()
    score_status = None
    try:
        try:
            provider.score("course prerequisite", candidate)
            score_status = "unexpected_success"
        except RerankerUnavailable as error:
            score_status = str(error)
        if not entered.wait(60):
            raise TimeoutError("CUDA_model_result_not_withheld")
        before_close = provider.metrics_snapshot()
        permit_before_close = provider._permits._value
        provider.close()
        closed_before_release = provider.metrics_snapshot()
        permit_closed_before_release = provider._permits._value
        try:
            provider.score("after close", candidate)
            post_close_status = "unexpected_success"
        except RerankerUnavailable as error:
            post_close_status = str(error)
        inference_calls_after_rejection = provider.metrics_snapshot()["inference_calls"]
        release.set()
        provider.drain(timeout_ms=60000)
        after_drain = provider.metrics_snapshot()
        permit_after_drain = provider._permits._value
    finally:
        release.set()
        provider.close()
        provider.drain(timeout_ms=60000)
    checks = {
        "actual_pinned_cuda_inference_completed": bool(call_count) and sum(call_count) == 1,
        "timed_request_returned_timeout": score_status == "reranker_timeout",
        "permit_held_while_timed_native_result_pending": permit_before_close == 0 and before_close["active_requests"] == 1,
        "close_did_not_free_active_permit_early": permit_closed_before_release == 0 and closed_before_release["active_requests"] == 1,
        "post_close_admission_rejected": post_close_status == "feature_disabled",
        "post_close_rejection_started_no_new_inference": inference_calls_after_rejection == 1,
        "late_result_drained_without_provider_failure": after_drain["active_requests"] == 0 and after_drain["failure_count"] == 1,
        "all_permits_released_after_drain": permit_after_drain == 1,
        "submitted_completed_cancelled_reconcile": after_drain["submitted_requests"] == after_drain["completed_requests"] + after_drain["cancelled_requests"],
        "model_snapshot_identity_matches": snapshot_sha256(model_dir) == identity.model_sha256,
    }
    report = {
        "schema_version": 1, "task": "P7-17.2", "status": "PASS_PINNED_CUDA_LATE_RESULT_PROBE" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "actual pinned sentence-transformers CUDA inference; returned score result withheld in a wrapper until after provider close",
        "started_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before,
        "source_identity_after": source_identity(ROOT), "elapsed_seconds": time.perf_counter() - started,
        "model_identity": identity.to_dict(), "model_snapshot_sha256": snapshot_sha256(model_dir),
        "torch_version": torch.__version__, "cuda_device": torch.cuda.get_device_name(0),
        "score_status": score_status, "post_close_status": post_close_status,
        "actual_predict_pair_counts": call_count, "permit_values": {
            "before_close": permit_before_close, "closed_while_active": permit_closed_before_release,
            "after_drain": permit_after_drain,
        }, "counters_before_close": before_close,
        "counters_closed_before_release": closed_before_release,
        "counters_after_drain": after_drain, "checks": checks,
        "limitations": [
            "The provider and CUDA model are real and snapshot-pinned; a local wrapper deliberately withholds the result after CUDA prediction completes, so this simulates a late provider completion rather than a hung kernel.",
            "Does not validate GPU driver/device loss, native kernel hang, production HTTP shutdown, or full M9 permanent-fault recovery.",
        ],
    }
    from evaluation.common.release_artifacts import write_json
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "checks": checks,
                      "permit_values": report["permit_values"], "cuda_device": report["cuda_device"],
                      "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or report["source_identity_before"] != report["source_identity_after"])


if __name__ == "__main__":
    raise SystemExit(main())
