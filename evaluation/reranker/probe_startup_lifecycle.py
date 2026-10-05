"""Real offline model startup/sharing/shutdown probe on known dev candidates.

This is diagnostic evidence, not a replacement for ordered M1-M12 acceptance.
It never reads held-out questions or fits a policy.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from evaluation.common.release_artifacts import sha256, source_identity, write_json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--dtype", default="float16")
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--dev", type=Path, default=Path("data/benchmark/hybrid_retrieval_dev.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase7_startup_lifecycle_probe.json"))
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError("retain previous probes; use a new output path")
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, RerankerUnavailable, snapshot_sha256
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.model_runtime import retrieval_runtime
    from campusai.rag.context import benchmark_retrieval_request
    import psutil
    import torch
    rows = [json.loads(line) for line in args.dev.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(row.get("split") != "dev" for row in rows):
        raise ValueError("startup probe must receive dev data only")
    identity = ModelIdentity(args.model_name, args.model_dir.name, snapshot_sha256(args.model_dir), args.model_dir.name,
                             device=args.device, dtype=args.dtype, batch_size=16)
    docs = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    retriever = HybridRetriever(args.index_dir, query_cache_size=0)
    row = next(row for row in rows if row["answerable"] and row.get("difficulty") == "hard")
    request = benchmark_retrieval_request(row, docs)
    results = retriever.search(**request, top_k=10, mode="auto")
    candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id, item.page, item.content, item.rank,
                                  float(item.fusion_score or 0.0)) for item in results[:8]]
    if not candidates:
        raise ValueError("actual dev candidates required")
    providers = [OfflineCrossEncoderReranker(identity, args.model_dir, require_ready=True) for _ in range(2)]
    observations, errors = [], []
    process = psutil.Process()
    def resource():
        return {"pid": process.pid, "rss_bytes": process.memory_info().rss,
                "vram_allocated_bytes": torch.cuda.memory_allocated(args.device) if args.device.startswith("cuda") else None,
                "at": datetime.now(timezone.utc).isoformat()}
    resources = [resource()]
    try:
        try:
            providers[0].score(request["query"], candidates)
            errors.append("cold_request_was_admitted")
        except RerankerUnavailable as error:
            observations.append({"case": "cold_request", "reason": str(error), "metrics": providers[0].metrics_snapshot()})
        started = time.perf_counter()
        for provider in providers:
            provider.warm_up()
        startup_ms = (time.perf_counter() - started) * 1000
        loaded_after_warm = [model for model in retrieval_runtime().loaded_models() if model["kind"] == "reranker_offline"]
        resources.append(resource())
        scores = []
        for _ in range(3):
            started = time.perf_counter()
            ranked = providers[0].score(request["query"], candidates)
            values = {item.candidate_id: item.reranker_score for item in ranked}
            scores.append(values)
            observations.append({"case": "warm_request", "latency_ms": (time.perf_counter() - started) * 1000,
                                 "scores": values, "call": providers[0].last_call, "metrics": providers[0].metrics_snapshot()})
        delta = max(abs(values[key] - scores[0][key]) for values in scores for key in values)
        if delta > 1e-5:
            errors.append("non_deterministic_scores")
        providers[0].close()
        loaded_after_first_close = [model for model in retrieval_runtime().loaded_models() if model["kind"] == "reranker_offline"]
        try:
            providers[0].score(request["query"], candidates)
            errors.append("closed_request_was_admitted")
        except RerankerUnavailable as error:
            observations.append({"case": "closed_request", "reason": str(error), "metrics": providers[0].metrics_snapshot()})
        providers[1].score(request["query"], candidates)
    finally:
        for provider in providers:
            provider.close()
            provider.drain()
    resources.append(resource())
    remaining = [model for model in retrieval_runtime().loaded_models() if model["kind"] == "reranker_offline"]
    if remaining or len(loaded_after_warm) != 1 or len(loaded_after_first_close) != 1:
        errors.append("model_lease_lifecycle")
    if any(provider.metrics_snapshot()["model_loads"] != 1 for provider in providers):
        errors.append("request_path_model_load")
    report = {"schema_version": 1, "phase": 7, "status": "pass" if not errors else "conditional",
              "release_eligible": False, "evidence_type": "real_offline_dev_startup_probe", "errors": errors,
              "measured_at": datetime.now(timezone.utc).isoformat(), **source_identity(Path(__file__).resolve().parents[2]),
              "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
              "index_sha256": sha256(args.index_dir / "manifest.json"), "dev_sha256": sha256(args.dev),
              "qid": row["qid"], "startup_ms": startup_ms, "max_score_delta": delta,
              "loaded_after_warm": loaded_after_warm, "loaded_after_first_close": loaded_after_first_close,
              "loaded_after_final_close": remaining, "observations": observations, "resources": resources,
              "phase6_models_retained": [model for model in retrieval_runtime().loaded_models() if model["kind"] != "reranker_offline"],
              "candidate_coordinates": [{"doc_id": c.doc_id, "chunk_id": c.chunk_id, "page": c.page,
                                           "content_sha256": __import__('hashlib').sha256(c.content.encode()).hexdigest()} for c in candidates]}
    write_json(args.output, report)
    print(json.dumps({"status": report["status"], "release_eligible": False, "errors": errors,
                      "startup_ms": startup_ms, "max_score_delta": delta}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
