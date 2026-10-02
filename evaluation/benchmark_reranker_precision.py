"""Offline dev-only precision/throughput experiment with raw, uncached scores.

Each precision runs in a separate process. No model/tuning results from this
diagnostic can replace M3/M6/M7 release evidence.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from evaluation.release_artifacts import sha256, source_identity, write_json
from evaluation.reranker_probe_inputs import FORMATS, probe_loader


def worker(args):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.runtime_provenance import runtime_description
    from evaluation.measure_reranker_capacity import percentile
    import torch
    rows = [json.loads(line) for line in args.dev.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise ValueError("precision experiments accept dev only")
    selected = [row for row in rows if row.get("answerable") and row.get("difficulty") == "hard"][:args.questions]
    if len(selected) < 3:
        raise ValueError("at least three hard dev questions are required")
    identity = ModelIdentity(args.model_name, args.model_dir.name,
        snapshot_sha256(args.model_dir), args.model_dir.name, device="cuda:0", dtype=args.worker,
        batch_size=args.batch_size, batch_window_ms=args.batch_window_ms, max_length=args.max_length)
    retriever = HybridRetriever(args.index_dir, query_cache_size=0,
        policies={"hybrid_rrf": RetrievalPolicy.from_report(args.calibration)})
    docs = json.loads((args.index_dir / "manifest.json").read_text())["documents"]
    provider = OfflineCrossEncoderReranker(identity, args.model_dir, timeout_ms=1000,
        candidate_cap=40, queue_limit=19, score_cache_size=0, batch_window_ms=args.batch_window_ms,
        model_loader=probe_loader(args.model_dir,identity,args.input_format))
    report = {"status": "conditional", "release_eligible": False, "evidence_type": "dev_precision_probe",
        **source_identity(Path(__file__).resolve().parents[1]), "runtime_environment": runtime_description(),
        "model_identity": identity.to_dict(), "dev_sha256": sha256(args.dev),
        "input_format":args.input_format,
        "capacity_cap":args.capacity_cap,
        "index_sha256": sha256(args.index_dir / "manifest.json"), "calibration_sha256": sha256(args.calibration),
        "scheduler": {"queue_limit":19,"batch_window_ms":args.batch_window_ms,"max_batch_pairs":200,"score_cache_size":0},
        "observations": [], "capacity": []}
    pools = []
    try:
        started = time.perf_counter()
        provider.warm_up()
        report["warmup_ms"] = (time.perf_counter() - started) * 1000
        for row in selected:
            pool = retriever.search(row["question"], row.get("doc_ids", docs), filters=row.get("filters"), top_k=40, mode="auto")
            candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id, item.page,
                item.content, item.rank, float(item.fusion_score or 0)) for item in pool]
            pools.append((row, candidates))
            for cap in (8, 10, 20):
                for repeat in range(3):
                    started = time.perf_counter()
                    ranking = provider.score(row["question"], candidates[:cap])
                    report["observations"].append({"qid": row["qid"], "cap": cap, "repeat": repeat,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "scores": {item.candidate_id: item.reranker_score for item in ranking},
                        "ranking": [item.candidate_id for item in ranking]})
        report["latency_by_cap"] = {str(cap): {
            f"p{int(p*100)}_ms": percentile([o["latency_ms"] for o in report["observations"] if o["cap"] == cap], p)
            for p in (.5, .95, .99)} for cap in (8, 10, 20)}
        report["max_repeat_delta"] = max(
            abs(o["scores"][key] - next(v for v in report["observations"]
                if v["qid"] == o["qid"] and v["cap"] == o["cap"] and v["repeat"] == 0)["scores"][key])
            for o in report["observations"] for key in o["scores"])
        for concurrency in (1, 5, 20):
            provider.drain()
            provider.close()
            provider = OfflineCrossEncoderReranker(identity, args.model_dir, timeout_ms=1000,
                candidate_cap=40, queue_limit=19, score_cache_size=0, batch_window_ms=args.batch_window_ms,
                model_loader=probe_loader(args.model_dir,identity,args.input_format))
            provider.warm_up()
            def request(number):
                row, candidates = pools[number % len(pools)]
                started = time.perf_counter()
                error = None
                try:
                    result = provider.score(row["question"], candidates[:args.capacity_cap])
                    count = len(result)
                except Exception as exc:
                    error, count = type(exc).__name__ + ":" + str(exc), 0
                return {"id": number, "qid": row["qid"], "latency_ms": (time.perf_counter()-started)*1000,
                    "error": error, "scored_candidates": count}
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                samples = list(executor.map(request, range(args.requests)))
            provider.drain()
            duration = time.perf_counter() - started
            report["capacity"].append({"concurrency": concurrency, "cap": args.capacity_cap, "requests": len(samples),
                "samples": samples, "duration_seconds": duration, "requests_per_second": len(samples)/duration,
                "successful_requests_per_second": sum(s["error"] is None for s in samples)/duration,
                "errors": sum(s["error"] is not None for s in samples),
                **{f"p{int(p*100)}_ms": percentile([s["latency_ms"] for s in samples], p) for p in (.5,.95,.99)},
                "provider_metrics": provider.metrics_snapshot()})
        report["gpu_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        report["gpu_peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
        report["completed"] = True
    finally:
        provider.close()
        provider.drain()
    write_json(args.output / f"{args.worker}-batch{args.batch_size}.json", report)
    print(json.dumps({"dtype": args.worker, "batch_size": args.batch_size,
        "latency_by_cap": report["latency_by_cap"], "max_repeat_delta": report["max_repeat_delta"],
        "capacity": [{k:v for k,v in part.items() if k not in {"samples", "provider_metrics"}} for part in report["capacity"]],
        "gpu_peak_allocated_bytes": report["gpu_peak_allocated_bytes"]}), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--dev", type=Path, default=Path(".release/reranker/studies/ai-benchmark-v1/dev.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--output", type=Path, default=Path(".release/reranker/studies/precision-v1"))
    parser.add_argument("--questions", type=int, default=3)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--batch-window-ms", type=float, default=0)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--capacity-cap", type=int, choices=(8,10,12,16,20), default=10)
    parser.add_argument("--input-format",choices=FORMATS,default="full_chunk")
    parser.add_argument("--worker", choices=("float32","float16","bfloat16"))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if not args.output.resolve().is_relative_to(root / ".release/reranker/studies"):
        raise ValueError("precision output must be isolated from release evidence")
    if args.requests < 100 or args.questions < 3:
        raise ValueError("at least 100 requests and three questions required")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.worker:
        if (args.output / f"{args.worker}-batch{args.batch_size}.json").exists():
            raise ValueError("measured evidence cannot be overwritten")
        worker(args)
    else:
        with (args.output / "attempt.json").open("x", encoding="utf-8") as attempt:
            json.dump({"release_eligible":False}, attempt)
        for dtype in ("float32", "float16", "bfloat16"):
            cmd = [sys.executable, "-m", "evaluation.benchmark_reranker_precision", "--model-dir", str(args.model_dir),
                "--model-name", args.model_name,
                "--dev", str(args.dev), "--index-dir", str(args.index_dir), "--calibration", str(args.calibration),
                "--output", str(args.output), "--worker", dtype, "--batch-size", str(args.batch_size),
                "--requests", str(args.requests), "--questions", str(args.questions),
                "--batch-window-ms", str(args.batch_window_ms), "--max-length", str(args.max_length)]
            cmd += ["--input-format",args.input_format]
            cmd += ["--capacity-cap",str(args.capacity_cap)]
            subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
