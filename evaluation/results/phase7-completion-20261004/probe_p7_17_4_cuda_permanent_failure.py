"""Exercise Phase 7 permanent-fault rollback with the real pinned CUDA provider."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
OUT = TASK / "p7-17-4-current-cuda-permanent-failure.json"


def digest(items) -> str:
    return hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> int:
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, OfflineCrossEncoderReranker
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.model_runtime import retrieval_runtime
    from campusai.retrieval.rerank_policy import Phase7Policy
    from evaluation.common.release_artifacts import sha256, source_identity, write_json

    if OUT.exists():
        raise FileExistsError(OUT)
    active = json.loads((ROOT / "configs/phase7_release_cycle.json").read_text(encoding="utf-8"))
    bench, results, index = (ROOT / active[key] for key in ("benchmark_dir", "results_dir", "index_dir"))
    phase6_path, dev_path = results / "hybrid_retrieval_calibration.json", bench / "human_retrieval_dev.jsonl"
    rows = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    identity_data = json.loads((TASK / "p7-07-cuda-snapshot-smoke.json").read_text(encoding="utf-8"))
    identity = ModelIdentity(**identity_data["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if identity.device != "cuda":
        raise ValueError("pinned provider identity is not CUDA")
    before = source_identity(ROOT)
    real_model = retrieval_runtime().get_offline_reranker(
        model_dir, device="cuda", max_length=identity.max_length,
        snapshot_sha256=identity.model_sha256, dtype=identity.dtype)
    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=30000,
                                           candidate_cap=40, queue_limit=1,
                                           failure_limit=1, score_cache_size=0,
                                           model_loader=lambda: real_model)
    provider.warm_up()
    calls_after_warmup = provider.metrics_snapshot()["inference_calls"]
    injected_calls = []

    class PermanentFaultAfterCUDA:
        def predict(self, pairs, **kwargs):
            real_model.predict(pairs, **kwargs)
            injected_calls.append(len(pairs))
            raise MemoryError("controlled_permanent_provider_fault")

    provider._model = PermanentFaultAfterCUDA()
    policy6 = RetrievalPolicy.from_report(phase6_path, expected_mode="hybrid_rrf")
    policy7 = Phase7Policy("p7-17-4-cuda-diagnostic", identity.fingerprint,
                           sha256(index / "manifest.json"), sha256(phase6_path), sha256(dev_path),
                           0.0, 0.0, 1.0, 100.0, candidate_cap=40, rerank_candidate_cap=40)
    baseline_retriever = HybridRetriever(index, query_cache_size=0, policies={"hybrid_rrf": policy6})
    fault_retriever = HybridRetriever(index, query_cache_size=0, policies={"hybrid_rrf": policy6},
                                      phase7_provider=provider, phase7_policy=policy7, phase7_enabled=True)
    selected = None
    try:
        for row in rows:
            query = row["question"]
            args = {"doc_ids": row.get("doc_ids") or None, "filters": row.get("filters") or None, "top_k": 5}
            baseline = [item.to_dict() for item in baseline_retriever.search(query, mode="auto", **args)]
            phase7 = [item.to_dict() for item in fault_retriever.search_phase7(query, **args)]
            trace = fault_retriever.last_trace
            if injected_calls:
                after_fault = provider.metrics_snapshot()
                calls_after_fault = after_fault["inference_calls"]
                followup = [item.to_dict() for item in fault_retriever.search_phase7(query, **args)]
                after_followup = provider.metrics_snapshot()
                selected = {
                    "qid": row["qid"], "dev_source_group": row.get("source_group"),
                    "question_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    "phase6_output_sha256": digest(baseline), "fault_fallback_output_sha256": digest(phase7),
                    "followup_output_sha256": digest(followup),
                    "fault_fallback_equals_phase6": phase7 == baseline,
                    "followup_equals_phase6": followup == baseline,
                    "reason": trace.rerank_reason, "provider_calls_after_warmup": calls_after_fault - calls_after_warmup,
                    "provider_calls_after_followup": after_followup["inference_calls"] - calls_after_warmup,
                    "phase7_enabled_after_fault": fault_retriever.phase7_enabled,
                    "provider_closed_after_fault": after_fault["closed"],
                    "failure_count": after_fault["failure_count"],
                }
                break
        if selected is None:
            raise RuntimeError("no active dev query routed into the controlled CUDA provider fault")
        final_metrics = provider.metrics_snapshot()
        checks = {
            "warmup_used_real_cuda_provider": calls_after_warmup == 1,
            "fault_followed_real_cuda_inference": injected_calls == [len(injected_calls) and injected_calls[0]],
            "fault_triggered_permanent_shutdown": selected["reason"] == "reranker_inference_failed" and not selected["phase7_enabled_after_fault"] and selected["provider_closed_after_fault"],
            "followup_started_zero_new_inference": selected["provider_calls_after_followup"] == 1,
            "phase6_output_preserved": selected["fault_fallback_equals_phase6"] and selected["followup_equals_phase6"],
            "failure_recorded_once": selected["failure_count"] == 1,
            "all_active_work_drained": final_metrics["active_requests"] == 0 and final_metrics["queue_depth"] == 0,
        }
    finally:
        provider.close()
    after = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-17.4", "status": "PASS_CUDA_PROVIDER_PERMANENT_FAULT" if all(checks.values()) else "FAIL",
        "release_eligible": False, "scope": "real pinned RTX 4060 CrossEncoder provider and active r18 index; controlled permanent exception injected after actual CUDA predict",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "source_identity_before": before,
        "source_identity_after": after, "active_cycle": {"benchmark_dir": active["benchmark_dir"],
        "results_dir": active["results_dir"], "index_dir": active["index_dir"]},
        "bindings": {"dev_sha256": sha256(dev_path), "index_manifest_sha256": sha256(index / "manifest.json"),
                     "phase6_calibration_sha256": sha256(phase6_path), "model_identity": identity.to_dict()},
        "inference_calls_after_warmup": calls_after_warmup, "injected_cuda_predict_batches": injected_calls,
        "observation": selected, "final_metrics": final_metrics, "checks": checks,
        "limitations": [
            "The CUDA model/provider and index are real; a controlled MemoryError is injected after successful model inference to exercise the permanent-fault transition.",
            "Does not exercise a naturally occurring CUDA OOM/driver fault, production HTTP process, or complete M9 target profile.",
        ],
    }
    write_json(OUT, report)
    print(json.dumps({"status": report["status"], "checks": checks,
                      "observation": selected, "report": OUT.as_posix()}, indent=2))
    return int(not all(checks.values()) or report["source_identity_before"] != report["source_identity_after"])


if __name__ == "__main__":
    raise SystemExit(main())
