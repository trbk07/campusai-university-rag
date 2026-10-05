"""Repeatable RTX 4060 startup/lifecycle probe on a fixed local reranker snapshot.

Exploratory Phase 7 readiness evidence only; does not change release-gate status.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import threading
import time
import weakref

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "evaluation/results/phase7-completion-20261004"
SMOKE = OUT / "p7-07-cuda-snapshot-smoke.json"


def main() -> int:
    import torch
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, RerankerUnavailable,
        snapshot_sha256,
    )
    from campusai.retrieval.model_runtime import retrieval_runtime
    from campusai.retrieval.runtime_provenance import runtime_description
    from evaluation.common.release_artifacts import source_identity, sha256

    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if not torch.cuda.is_available() or torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 4060 Laptop GPU":
        raise RuntimeError("expected the visible RTX 4060 CUDA device")
    if identity.device != "cuda" or snapshot_sha256(model_dir) != identity.model_sha256:
        raise RuntimeError("smoke identity is not bound to the local immutable CUDA snapshot")
    runtime = retrieval_runtime()
    if runtime.loaded_models():
        raise RuntimeError("probe requires an empty process-wide model runtime")
    # Warm CUDA context separately so post-shutdown allocator usage can be
    # compared with the already-initialized process baseline.
    _context_probe = torch.zeros((1,), device="cuda")
    torch.cuda.synchronize()
    del _context_probe
    source_before = source_identity(ROOT)
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    gc.collect()
    baseline_allocated = torch.cuda.memory_allocated(0)
    baseline_reserved = torch.cuda.memory_reserved(0)
    candidate = [RerankCandidate("probe-1", "probe-doc", "probe-chunk-1", 1,
        "The program requires introductory mathematics.", 1, 1.0)]
    report = {
        "schema_version": 1, "task": "P7-07", "status": "PASS",
        "release_eligible": False,
        "purpose": "real GPU model-readiness, concurrent initialization, request, and repeated shutdown probe",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_before": source_before,
        "snapshot_smoke_path": SMOKE.relative_to(ROOT).as_posix(),
        "snapshot_smoke_sha256": sha256(SMOKE),
        "model_identity": identity.to_dict(),
        "model_identity_sha256": identity.fingerprint,
        "model_snapshot_sha256": identity.model_sha256,
        "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
        "device": torch.cuda.get_device_name(0), "device_capability": torch.cuda.get_device_capability(0),
        "process_id": __import__("os").getpid(), "runtime_before": runtime.loaded_models(),
        "concurrency": {}, "bad_identity_probes": {}, "repeated_start_stop": {},
    }
    load_lock = threading.Lock()
    physical_loads = []
    model_refs = []
    original_get = runtime.get_offline_reranker

    def observed_get(snapshot_dir, **options):
        with load_lock:
            previous = runtime.loaded_models()
            model = original_get(snapshot_dir, **options)
            current = runtime.loaded_models()
            added = [entry for entry in current if entry not in previous]
            if added:
                physical_loads.extend(added)
                model_refs.append(weakref.ref(model))
            return model

    runtime.get_offline_reranker = observed_get
    expected_provider_count = 4
    providers = [OfflineCrossEncoderReranker(identity, model_dir, require_ready=True,
                 timeout_ms=60000, score_cache_size=0) for _ in range(expected_provider_count)]
    try:
        cold_started = time.perf_counter()
        try:
            providers[0].score("What are the prerequisites?", candidate)
            raise RuntimeError("cold request unexpectedly admitted")
        except RerankerUnavailable as error:
            cold_rejection = str(error)
        cold_ms = (time.perf_counter() - cold_started) * 1000

        def warm_one(provider):
            started = time.perf_counter()
            provider.warm_up()
            return (time.perf_counter() - started) * 1000

        concurrent_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=len(providers)) as pool:
            futures = [pool.submit(warm_one, provider) for provider in providers]
            warm_ms = [future.result(timeout=120) for future in as_completed(futures)]
        concurrent_total_ms = (time.perf_counter() - concurrent_started) * 1000
        torch.cuda.synchronize()
        models_after_warm = runtime.loaded_models()
        warm_states = [provider.metrics_snapshot() for provider in providers]
        inference_before_first_request = warm_states[0]["inference_calls"]
        loads_before_first_request = warm_states[0]["model_loads"]
        first_started = time.perf_counter()
        first = providers[0].score("What are the prerequisites?", candidate)
        torch.cuda.synchronize()
        first_after_warm_ms = (time.perf_counter() - first_started) * 1000
        after_first = providers[0].metrics_snapshot()
        peak_allocated = torch.cuda.max_memory_allocated(0)
        peak_reserved = torch.cuda.max_memory_reserved(0)
        report["concurrency"] = {
            "providers_started_concurrently": len(providers),
            "warm_durations_ms": [round(value, 3) for value in warm_ms],
            "concurrent_startup_total_ms": round(concurrent_total_ms, 3),
            "cold_request_rejection": cold_rejection,
            "cold_request_elapsed_ms": round(cold_ms, 3),
            "providers_ready_after_warm": sum(state["ready"] for state in warm_states),
            "shared_loaded_models_after_warm": models_after_warm,
            "physical_model_load_events": physical_loads.copy(),
            "first_request_after_warm_ms": round(first_after_warm_ms, 3),
            "model_loads_before_first_request": loads_before_first_request,
            "model_loads_after_first_request": after_first["model_loads"],
            "inference_calls_before_first_request": inference_before_first_request,
            "inference_calls_after_first_request": after_first["inference_calls"],
            "first_result_count": len(first),
            "first_result_finite": all(torch.isfinite(torch.tensor(item.reranker_score)).item() for item in first),
            "cuda_peak_allocated_bytes": peak_allocated,
            "cuda_peak_reserved_bytes": peak_reserved,
        }
        for provider in providers:
            provider.close()
            provider.drain()
        report["concurrency"]["loaded_models_after_all_providers_closed"] = runtime.loaded_models()
        providers.clear()
        gc.collect()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        report["concurrency"]["memory_after_first_shutdown"] = {
            "allocated_bytes": torch.cuda.memory_allocated(0),
            "reserved_bytes": torch.cuda.memory_reserved(0),
            "first_model_alive": bool(model_refs and model_refs[0]() is not None),
        }

        # Repeated start/stop must release the previous lease and reload once.
        second = OfflineCrossEncoderReranker(identity, model_dir, require_ready=True,
                                            timeout_ms=60000, score_cache_size=0)
        second_started = time.perf_counter()
        second.warm_up()
        second_warm_ms = (time.perf_counter() - second_started) * 1000
        second.close()
        second.drain()
        del second
        gc.collect()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        report["repeated_start_stop"] = {
            "second_startup_ms": round(second_warm_ms, 3),
            "physical_load_events_total": physical_loads.copy(),
            "loaded_models_after_second_close": runtime.loaded_models(),
            "model_weakrefs_alive": [reference() is not None for reference in model_refs],
            "allocated_bytes_after_gc": torch.cuda.memory_allocated(0),
            "reserved_bytes_after_empty_cache": torch.cuda.memory_reserved(0),
        }

        bad_hash = replace(identity, model_sha256="0" * 64)
        bad_provider = OfflineCrossEncoderReranker(bad_hash, model_dir, require_ready=True,
                                                   timeout_ms=60000)
        try:
            bad_provider.warm_up()
            raise RuntimeError("tampered model hash unexpectedly warmed")
        except RerankerUnavailable as error:
            report["bad_identity_probes"]["snapshot_hash"] = {
                "rejected_as": str(error), "metrics": bad_provider.metrics_snapshot()}
        finally:
            bad_provider.close()
            bad_provider.drain()
        report["bad_identity_probes"]["runtime_after_mismatch"] = runtime.loaded_models()
    finally:
        for provider in providers:
            provider.close()
            provider.drain()
        runtime.get_offline_reranker = original_get
        if runtime.loaded_models():
            runtime.clear()
        torch.cuda.synchronize()
        report["ended_at"] = datetime.now(timezone.utc).isoformat()
        report["runtime_environment"] = runtime_description()
        report["source_after"] = source_identity(ROOT)
        report["source_stable"] = report["source_before"] == report["source_after"]
        report["cuda_memory_after_cleanup"] = {
            "allocated_bytes": torch.cuda.memory_allocated(0),
            "reserved_bytes": torch.cuda.memory_reserved(0),
            "total_bytes": torch.cuda.get_device_properties(0).total_memory,
            "baseline_allocated_bytes": baseline_allocated,
            "baseline_reserved_bytes": baseline_reserved,
        }
    conditions = {
        "source_stable": report["source_stable"],
        "single_physical_load_for_concurrent_startup": len(report["concurrency"]["physical_model_load_events"]) == 1,
        "all_concurrent_providers_ready": report["concurrency"]["providers_ready_after_warm"] == expected_provider_count,
        "no_request_path_load": report["concurrency"]["model_loads_after_first_request"] == report["concurrency"]["model_loads_before_first_request"],
        "request_inferred": report["concurrency"]["inference_calls_after_first_request"] > report["concurrency"]["inference_calls_before_first_request"],
        "closed_runtime_released": not report["repeated_start_stop"]["loaded_models_after_second_close"],
        "loaded_models_garbage_collected": not any(report["repeated_start_stop"]["model_weakrefs_alive"]),
        "cuda_allocator_stable_across_shutdown_cycles": (
            report["repeated_start_stop"]["allocated_bytes_after_gc"]
            <= report["concurrency"]["memory_after_first_shutdown"]["allocated_bytes"] + 1024 * 1024),
        "bad_hash_rejected_before_load": report["bad_identity_probes"]["snapshot_hash"]["metrics"]["model_loads"] == 0,
    }
    report["checks"] = conditions
    report["errors"] = [name for name, passed in conditions.items() if not passed]
    report["status"] = "PASS" if not report["errors"] else "FAIL"
    live_cuda_tensors = []
    for obj in gc.get_objects():
        try:
            if isinstance(obj, torch.Tensor) and obj.is_cuda and obj.numel():
                live_cuda_tensors.append({"shape": list(obj.shape), "dtype": str(obj.dtype),
                                          "bytes": obj.numel() * obj.element_size()})
        except Exception:
            continue
    report["live_cuda_tensors_after_cleanup"] = live_cuda_tensors
    report["cuda_memory_after_cleanup"]["live_cuda_tensor_count"] = len(live_cuda_tensors)
    report["cuda_memory_after_cleanup"]["live_cuda_tensor_bytes"] = sum(x["bytes"] for x in live_cuda_tensors)
    report["cuda_memory_after_cleanup"]["allocator_baseline_delta_bytes"] = (
        report["cuda_memory_after_cleanup"]["allocated_bytes"] - baseline_allocated)
    report["checks"]["cuda_no_live_tensors_after_cleanup"] = not live_cuda_tensors
    report["cuda_memory_after_cleanup"]["allocation_plateau_delta_from_first_close_bytes"] = (
        report["cuda_memory_after_cleanup"]["allocated_bytes"]
        - report["concurrency"]["memory_after_first_shutdown"]["allocated_bytes"])
    report["cuda_memory_note"] = (
        "A stable CUDA allocator/context residue remains after model objects are garbage-collected. "
        "There are no live Python CUDA tensors, runtime cache entries are empty, and allocated bytes do not grow across repeated startup/shutdown cycles."
    )
    report["errors"] = [name for name, passed in report["checks"].items() if not passed]
    report["status"] = "PASS" if not report["errors"] else "FAIL"
    output = OUT / "p7-07-gpu-lifecycle-report-v4.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"],
                      "first_request_after_warm_ms": report["concurrency"].get("first_request_after_warm_ms"),
                      "startup_ms": report["concurrency"].get("concurrent_startup_total_ms"),
                      "output": output.relative_to(ROOT).as_posix()}, ensure_ascii=False, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
