"""Measure per-query CUDA scoring time/resources for the exploratory body config."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import statistics
import time

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
SMOKE = TASK / "p7-07-cuda-snapshot-smoke.json"
OBS_OUT = TASK / "p7-09-body-runtime-observations.json.gz"
REPORT_OUT = TASK / "p7-09-body-runtime-replay.json"


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered)-1, math.ceil(quantile * len(ordered))-1)]


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    import psutil
    import torch

    if OBS_OUT.exists() or REPORT_OUT.exists():
        raise FileExistsError("preserve previous P7-09 body runtime measurement")
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    base = ModelIdentity(**smoke["model_identity"])
    identity = replace(base, input_format="body")
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if identity.device != "cuda" or snapshot_sha256(model_dir) != identity.model_sha256:
        raise ValueError("body runtime measurement requires the pinned CUDA snapshot")
    process = psutil.Process()
    before = source_identity(ROOT)
    provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
        candidate_cap=40, score_cache_size=0)
    observations = []
    resource_samples = []
    started = datetime.now(timezone.utc).isoformat()
    wall_start = time.perf_counter()
    try:
        provider.warm_up()
        torch.cuda.synchronize()
        provider_started = time.perf_counter()
        for number, obs in enumerate(raw["observations"], 1):
            candidates = [RerankCandidate(item["chunk_id"], item["doc_id"], item["chunk_id"],
                item["page"], item["content"], int(item["rank"]),
                float(item.get("fusion_score") or 0.0)) for item in obs["pool"]]
            started_call = time.perf_counter()
            ranked = provider.score(obs["qid"], candidates) if candidates else []
            if candidates:
                torch.cuda.synchronize()
            latency_ms = (time.perf_counter() - started_call) * 1000 if candidates else 0.0
            observations.append({"qid": obs["qid"], "candidate_count": len(candidates),
                "latency_ms": latency_ms, "scored_count": len(ranked)})
            if number % 20 == 0:
                stats = provider.metrics_snapshot()
                resource_samples.append({"sample": number, "utc": datetime.now(timezone.utc).isoformat(),
                    "pid": process.pid, "rss_bytes": process.memory_info().rss,
                    "cpu_percent": process.cpu_percent(None),
                    "cuda_allocated_bytes": torch.cuda.memory_allocated(),
                    "cuda_reserved_bytes": torch.cuda.memory_reserved(),
                    "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                    "pending_queue": stats.get("pending_queue"), "active_requests": stats.get("active_requests")})
        torch.cuda.synchronize()
        provider_elapsed = time.perf_counter() - provider_started
        provider.drain()
        metrics = provider.metrics_snapshot()
    finally:
        provider.close()
        provider.drain()
    after = source_identity(ROOT)
    per_query = [item["latency_ms"] for item in observations if item["candidate_count"]]
    obs_raw = {"schema_version": 1, "task": "P7-09", "release_eligible": False,
        "calibration_split": "dev", "test_used": False, "holdout_used": False,
        "source_identity_before": before, "source_identity_after": after,
        "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
        "model_snapshot_sha256": identity.model_sha256, "candidate_raw_sha256": sha256(RAW),
        "candidate_generation": raw["candidate_generation"],
        "observations": observations, "resource_samples": resource_samples,
        "provider_metrics": metrics}
    with gzip.open(OBS_OUT, "wt", encoding="utf-8") as stream:
        json.dump(obs_raw, stream, ensure_ascii=False, allow_nan=False)
    report = {"schema_version": 1, "task": "P7-09", "status": "diagnostic",
        "release_eligible": False, "started_at": started,
        "ended_at": datetime.now(timezone.utc).isoformat(), "source_stable": before == after,
        "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
        "model_snapshot_sha256": identity.model_sha256, "candidate_raw_sha256": sha256(RAW),
        "observation_path": OBS_OUT.relative_to(ROOT).as_posix(),
        "observation_sha256": sha256(OBS_OUT), "queries": len(observations),
        "eligible_scoring_queries": len(per_query), "empty_pool_queries": len(observations)-len(per_query),
        "candidate_count_total": sum(item["candidate_count"] for item in observations),
        "model_score_latency_ms": {"p50": percentile(per_query,.50), "p95": percentile(per_query,.95),
            "p99": percentile(per_query,.99), "max": max(per_query,default=0.0),
            "mean": statistics.mean(per_query) if per_query else 0.0,
            "scope": "one direct provider.score call per nonempty query; excludes retrieval, HTTP, RAG, LLM and threshold policy"},
        "wall_seconds": time.perf_counter()-wall_start,
        "provider_scoring_seconds": provider_elapsed,
        "provider_successful_requests": metrics.get("completed_requests"),
        "provider_inference_calls": metrics.get("inference_calls"),
        "provider_timeouts": 0, "provider_errors": metrics.get("failure_count"),
        "peak_process_rss_bytes": max((x["rss_bytes"] for x in resource_samples), default=process.memory_info().rss),
        "peak_cuda_allocated_bytes": max((x["cuda_peak_allocated_bytes"] for x in resource_samples), default=torch.cuda.max_memory_allocated()),
        "peak_cuda_reserved_bytes": max((x["cuda_reserved_bytes"] for x in resource_samples), default=torch.cuda.memory_reserved()),
        "resource_samples": len(resource_samples),
        "limitations": ["Measured local RTX 4060 provider component only; not full application HTTP or live LLM latency.",
            "The body ranking-only config has no dev evidence threshold meeting Recall@5>=95% and FPR<=1%; this is not a deployable selected config.",
            "No public deployment profile is claimed."]}
    write_json(REPORT_OUT, report)
    print(json.dumps({"source_stable": report["source_stable"],
        "model_score_latency_ms": report["model_score_latency_ms"],
        "peak_process_rss_bytes": report["peak_process_rss_bytes"],
        "peak_cuda_allocated_bytes": report["peak_cuda_allocated_bytes"],
        "peak_cuda_reserved_bytes": report["peak_cuda_reserved_bytes"],
        "provider_metrics": metrics}, ensure_ascii=False, indent=2))
    return int(not report["source_stable"])


if __name__ == "__main__":
    raise SystemExit(main())
