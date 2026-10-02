"""Measured latency, concurrency and resource evidence for a deployment profile."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import math
from pathlib import Path
import threading
import time

from evaluation.common.release_artifacts import require_previous_gates, sha256, source_identity, write_json, policy_bindings


def percentile(values: list[float], fraction: float) -> float:
    if not values or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("latency samples must be nonempty, finite and nonnegative")
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def summarize_samples(samples: list[dict]) -> dict:
    if not isinstance(samples, list) or not samples:
        raise ValueError("performance requires actual request samples")
    for sample in samples:
        if not isinstance(sample, dict) or type(sample.get("hard")) is not bool or type(sample.get("error")) is not bool:
            raise ValueError("invalid sample schema")
        percentile([sample["latency_ms"]], 1)
    hard = [s["latency_ms"] for s in samples if s["hard"]]
    if not hard:
        raise ValueError("hard query measurements required")
    return {"requests": len(samples), "hard_requests": len(hard),
            "hard_rerank_requests": sum(s["hard"] and s.get("rerank_selected") is True for s in samples),
            **{f"hard_p{int(p*100)}_ms": percentile(hard, p) for p in (.50, .95, .99)},
            **{f"overall_p{int(p*100)}_ms": percentile([s["latency_ms"] for s in samples], p) for p in (.50, .95, .99)},
            "timeout_rate": sum(s.get("reason") == "reranker_timeout" for s in samples) / len(samples),
            "timeout_fallback_rate": sum(s.get("reason") == "reranker_timeout" and not s.get("error") for s in samples) / len(samples),
            "fallback_rate": sum(s.get("fallback", False) for s in samples) / len(samples),
            "errors": sum(s["error"] for s in samples)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--deployment-ram-bytes", type=int, required=True)
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--profile", default="cpu-small")
    args = parser.parse_args()
    if args.requests < 100 or args.deployment_ram_bytes <= 0:
        raise ValueError(">=100 requests and a positive deployment RAM limit required")
    require_previous_gates("M7", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    import psutil
    from campusai.retrieval.reranker_activation import build_phase7_retriever
    from campusai.retrieval.cross_encoder_provider import RerankCandidate
    from campusai.retrieval.model_runtime import retrieval_runtime
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.calibration import RetrievalPolicy
    retrieval_runtime().clear()
    started = time.perf_counter()
    phase6_path = args.results_dir / "hybrid_retrieval_calibration.json"
    def activate():
        value = build_phase7_retriever(args.index_dir, phase6_path, args.benchmark_dir / "human_retrieval_dev.jsonl")
        if not value.phase7_enabled:
            raise ValueError("activation rejected")
        value.query_cache_size = 0
        return value
    retriever = activate()
    provider = retriever.phase7_provider
    docs = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    rows = [json.loads(line) for line in (args.benchmark_dir / "human_retrieval_test.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    hard_rows = [row for row in rows if row["answerable"] and row["difficulty"] == "hard" and "exact_code" not in row["tags"]]
    if not hard_rows:
        raise ValueError("no hard workload")
    process = psutil.Process()
    peak = [process.memory_info().rss]
    stop = threading.Event()
    def monitor():
        while not stop.wait(.01):
            peak[0] = max(peak[0], process.memory_info().rss)
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    process.cpu_percent()
    cold_ms = (time.perf_counter() - started) * 1000
    def search(row, mode="phase7"):
        begin = time.perf_counter()
        error = False
        selected = False
        try:
            retriever.search(row["question"], row.get("doc_ids", docs), filters=row.get("filters"), top_k=5, mode=mode)
            trace = retriever.last_trace
            reason = trace.rerank_reason
            selected = trace.rerank_selected
            timings = trace.latency_ms or {}
            fallback = mode == "phase7" and not trace.rerank_selected and reason not in {"easy_confident", "exact_or_abstained", "single_candidate"}
        except Exception:
            error, reason, timings, fallback = True, "request_exception", {}, False
        return {"qid": row["qid"], "hard": row["difficulty"] == "hard", "error": error,
                "latency_ms": (time.perf_counter() - begin) * 1000, "reason": reason,
                "fallback": fallback, "rerank_selected": selected, "timings_ms": timings}
    profiles, all_samples = [], []
    try:
        warm_started = time.perf_counter()
        provider.warm_up()
        cold_ms = (time.perf_counter() - started) * 1000
        search(hard_rows[0])
        warm_ms = (time.perf_counter() - warm_started) * 1000
        original_policy = retriever.phase7_policy
        matrix = [(8, 1), (10, 1), (20, 1), (10, 5), (10, 20)]
        if provider.model_identity.device.startswith("cuda"):
            matrix.append((20, 5))
        for concurrency in (1, 5, 10, 20):
            pair = (original_policy.rerank_candidate_cap, concurrency)
            if pair not in matrix:
                matrix.append(pair)
        for cap, concurrency in matrix:
            # Every profile starts with an independently activated provider.
            # A previous circuit rollback cannot silently turn subsequent
            # capacity measurements into Phase 6-only measurements.
            provider.drain()
            provider.close()
            retriever = activate()
            provider = retriever.phase7_provider
            # Capacity experiments don't fit thresholds or replace release policy.
            retriever.phase7_policy = replace(original_policy, rerank_candidate_cap=cap)
            provider.reset_circuit()
            workload = [hard_rows[i % len(hard_rows)] for i in range(args.requests)]
            with ThreadPoolExecutor(max_workers=concurrency) as workers:
                samples = list(workers.map(search, workload))
            # Don't let a timed-out native inference contaminate the next
            # profile. The bounded worker may still be finishing it.
            provider.drain()
            part = {"profile": args.profile, "device": provider.model_identity.device,
                    "resource_limits": provider.resource_limits,
                    "rerank_cap": cap, "concurrency": concurrency, "samples": samples,
                    "provider_metrics": provider.metrics_snapshot(),
                    "phase7_enabled_after": retriever.phase7_enabled,
                    "summary": summarize_samples(samples)}
            profiles.append(part)
        provider.close()
        retriever = activate()
        provider = retriever.phase7_provider
        all_samples = [search(hard_rows[i % len(hard_rows)]) for i in range(args.requests)]
        retrieval_only = [search(row, "auto") for row in hard_rows]
        pool = retriever.search(hard_rows[0]["question"], docs, top_k=40, mode="auto")
        candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id, item.page, item.content,
                                      item.rank, float(item.fusion_score or 0)) for item in pool[:original_policy.rerank_candidate_cap]]
        provider.drain()
        provider.close()
        diagnostic = activate()
        provider = diagnostic.phase7_provider
        reranker_only, reranker_only_observations = [], []
        for _ in range(30):
            t = time.perf_counter()
            reason = None
            try:
                provider.score(hard_rows[0]["question"], candidates)
            except Exception as error:
                reason = type(error).__name__
            elapsed = (time.perf_counter() - t) * 1000
            reranker_only.append(elapsed)
            reranker_only_observations.append({"latency_ms": elapsed, "error_type": reason})
        provider.drain()
    finally:
        stop.set()
        monitor_thread.join(timeout=1)
        provider.close()
    bindings = {**source_identity(Path(__file__).resolve().parents[2]),
                **policy_bindings(args.results_dir),
                "index_sha256": sha256(args.index_dir / "manifest.json"),
                "phase6_calibration_sha256": sha256(phase6_path),
                "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
                "model_identity_sha256": provider.model_identity.fingerprint}
    summary = summarize_samples(all_samples)
    passed = (summary["hard_rerank_requests"] >= 30 and summary["hard_p50_ms"] <= 500 and summary["hard_p95_ms"] <= 1000 and summary["hard_p99_ms"] <= 2000
              and summary["timeout_rate"] <= .005 and not summary["errors"] and peak[0] <= .75 * args.deployment_ram_bytes
              and all(row["error_type"] is None for row in reranker_only_observations))
    status = "pass" if passed else "conditional"
    write_json(args.results_dir / "reranker_performance.json", {"schema_version": 2, "phase": 7, "status": status, **bindings,
               "resource_limits": provider.resource_limits,
               "profile": args.profile, "samples": all_samples, "summary": summary, "cold_start_ms": cold_ms,
               "warmup_ms": warm_ms, "retrieval_only": retrieval_only, "reranker_only_ms": reranker_only,
               "reranker_only_observations": reranker_only_observations,
               "peak_rss_bytes": peak[0], "cpu_utilization_percent": process.cpu_percent()})
    overflow_errors = sum(s["error"] for p in profiles for s in p["samples"] if s["reason"] == "queue_full")
    write_json(args.results_dir / "reranker_capacity.json", {"status": status, **bindings, "profiles": profiles,
               "resource_limits": provider.resource_limits,
               "release_rerank_cap": original_policy.rerank_candidate_cap, "deployment_device": provider.model_identity.device,
               "queue_overflow_request_failures": overflow_errors})
    write_json(args.results_dir / "reranker_resource_budget.json", {"status": status, **bindings,
               "deployment_ram_bytes": args.deployment_ram_bytes, "peak_rss_bytes": peak[0], "ram_fraction": peak[0] / args.deployment_ram_bytes})
    print(json.dumps({"status": status, "summary": summary, "peak_rss_bytes": peak[0]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
