"""Measure controlled CUDA dtype/batch variants on the identical body/dev pools."""
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
DEV = TASK / "p7-02-dev-replay/human_retrieval_dev.jsonl"
BASE_RAW = TASK / "p7-09-full-dev-reranker-raw-v2.json"
BODY_RAW = TASK / "p7-09-input-ablation-v2-body.json.gz"
SMOKE = TASK / "p7-07-cuda-snapshot-smoke.json"
VARIANTS = (("float32", 1), ("float32", 16), ("float32", 32), ("float32", 64),
            ("float16", 8), ("bfloat16", 8))


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, math.ceil(q * len(ordered))-1)] if ordered else 0.0


def main() -> int:
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from evaluation.common.release_artifacts import sha256, source_identity, write_json
    from evaluation.reranker.optimize_reranker_dev import rank_fusion, summarize
    import torch

    rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    base_raw = json.loads(BASE_RAW.read_text(encoding="utf-8"))
    with gzip.open(BODY_RAW, "rt", encoding="utf-8") as stream:
        body_raw = json.load(stream)
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    base_identity = ModelIdentity(**smoke["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / base_identity.model_revision
    if (len(rows) != 889 or any(row.get("split") != "dev" for row in rows)
            or body_raw.get("dev_sha256") != sha256(DEV)
            or body_raw.get("candidate_raw_sha256") != sha256(BASE_RAW)
            or snapshot_sha256(model_dir) != base_identity.model_sha256):
        raise ValueError("invalid dev, pool, or model binding")
    qrows = {row["qid"]: row for row in rows}
    pool_by_qid = {obs["qid"]: obs for obs in base_raw["observations"]}
    body_by_qid = {obs["qid"]: obs["scores"] for obs in body_raw["observations"]}
    if set(qrows) != set(pool_by_qid) or set(qrows) != set(body_by_qid):
        raise ValueError("variant input must cover exactly the complete dev packet")
    before = source_identity(ROOT)
    results = []
    for dtype, batch_size in VARIANTS:
        label = f"{dtype}-b{batch_size}"
        raw_path = TASK / f"p7-09-device-batch-{label}.json.gz"
        if raw_path.exists():
            raise FileExistsError(f"preserve prior measurement {raw_path.name}")
        identity = replace(base_identity, dtype=dtype, batch_size=batch_size,
                           input_format="body")
        provider = OfflineCrossEncoderReranker(identity, model_dir, timeout_ms=60000,
            candidate_cap=40, score_cache_size=0)
        samples = []
        observations = []
        failure = None
        started = time.perf_counter()
        try:
            provider.warm_up()
            torch.cuda.synchronize()
            for number, pool_obs in enumerate(base_raw["observations"], 1):
                qid = pool_obs["qid"]
                candidates = [RerankCandidate(item["chunk_id"], item["doc_id"], item["chunk_id"],
                    item["page"], item["content"], int(item["rank"]),
                    float(item.get("fusion_score") or 0.0)) for item in pool_obs["pool"]]
                start_call = time.perf_counter()
                ranked = provider.score(qrows[qid]["question"], candidates) if candidates else []
                if candidates:
                    torch.cuda.synchronize()
                latency = (time.perf_counter()-start_call)*1000 if candidates else 0.0
                scores = {item.chunk_id: item.reranker_score for item in ranked}
                observations.append({"qid": qid, "scores": scores,
                    "candidate_count": len(candidates), "latency_ms": latency})
                if number % 200 == 0:
                    samples.append({"query": number, "cuda_allocated_bytes": torch.cuda.memory_allocated(),
                        "cuda_reserved_bytes": torch.cuda.memory_reserved(),
                        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated()})
                if number % 200 == 0:
                    print(f"{label}: {number}/{len(pool_by_qid)}", flush=True)
        except Exception as exc:
            failure = {"type": type(exc).__name__, "message": str(exc)[:500]}
        finally:
            provider.close()
            provider.drain()
        elapsed = time.perf_counter()-started
        stats = provider.metrics_snapshot()
        variant_raw = {"schema_version": 1, "task": "P7-09", "format": "body",
            "dtype": dtype, "batch_size": batch_size, "release_eligible": False,
            "calibration_split": "dev", "test_used": False, "holdout_used": False,
            "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
            "model_snapshot_sha256": identity.model_sha256, "dev_sha256": sha256(DEV),
            "candidate_raw_sha256": sha256(BASE_RAW), "body_score_raw_sha256": sha256(BODY_RAW),
            "observations": observations, "resource_samples": samples, "provider_metrics": stats,
            "failure": failure}
        with gzip.open(raw_path, "wt", encoding="utf-8") as stream:
            json.dump(variant_raw, stream, ensure_ascii=False, allow_nan=False)
        record = {"variant": label, "dtype": dtype, "batch_size": batch_size,
            "raw_path": raw_path.relative_to(ROOT).as_posix(), "raw_sha256": sha256(raw_path),
            "elapsed_seconds": elapsed, "failure": failure,
            "provider_metrics": stats, "resource_samples": samples}
        if failure is None and len(observations) == 889:
            outputs = {}
            for obs in observations:
                pool = pool_by_qid[obs["qid"]]["pool"]
                outputs[obs["qid"]] = rank_fusion(pool, obs["scores"], .5, 40)[:5]
            record["metrics_cap40_weight05"] = summarize(rows, outputs)
            all_latencies = [obs["latency_ms"] for obs in observations if obs["candidate_count"]]
            record["latency_ms"] = {"p50": percentile(all_latencies,.5),
                "p95": percentile(all_latencies,.95), "p99": percentile(all_latencies,.99),
                "max": max(all_latencies,default=0), "mean": statistics.mean(all_latencies) if all_latencies else 0,
                "population": len(all_latencies)}
            ref_deltas = []
            for obs in observations:
                for cid, score in obs["scores"].items():
                    ref_deltas.append(abs(score-body_by_qid[obs["qid"]][cid]))
            record["reference_body_batch8_score_delta"] = {"max_abs": max(ref_deltas,default=0),
                "mean_abs": statistics.mean(ref_deltas) if ref_deltas else 0}
        results.append(record)
        print(json.dumps({"variant": label, "elapsed_seconds": elapsed,
            "failure": failure, "metrics": record.get("metrics_cap40_weight05"),
            "latency_ms": record.get("latency_ms")}, ensure_ascii=False), flush=True)
    after = source_identity(ROOT)
    report = {"schema_version":1,"task":"P7-09","status":"diagnostic",
        "release_eligible":False,"calibration_split":"dev","test_used":False,
        "holdout_used":False,"started_at":datetime.now(timezone.utc).isoformat(),
        "source_stable":before==after,"source_identity_before":before,
        "source_identity_after":after,"dev_sha256":sha256(DEV),
        "candidate_raw_sha256":sha256(BASE_RAW),"body_score_raw_sha256":sha256(BODY_RAW),
        "fixed_candidate_pool":True,"fixed_input_format":"body",
        "fixed_policy":"rank_fusion cap=40, rank_weight=0.5; no evidence threshold",
        "baseline_identity":base_identity.to_dict(),"variants":results,
        "limitations":["All measurements and metric summaries use the same 889-row dev packet; no grouped OOF.",
            "Ranking-only FPR remains 9.39%, and the separate threshold sweep found no feasible policy.",
            "Latency excludes retrieval/HTTP/RAG/LLM; this does not establish M7/S6 or release readiness."]}
    write_json(TASK/"p7-09-dtype-batch-ablation.json",report)
    print(json.dumps({"source_stable":report["source_stable"],"variant_count":len(results),
        "failures":sum(bool(x["failure"]) for x in results)},indent=2))
    return int(not report["source_stable"])


if __name__=="__main__":
    raise SystemExit(main())
