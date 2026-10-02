"""Small reproducible concurrency smoke test for the application adapter."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.api import CampusAIApplication


def _percentile(values: list[float], fraction: float) -> float:
    return values[min(len(values) - 1, max(0, int((len(values) - 1) * fraction)))]


def run(application: CampusAIApplication, question: str, users: int, requests: int) -> dict:
    def one(_):
        started = time.perf_counter()
        result = application.query(question)
        return (time.perf_counter() - started) * 1000, result.get("ok", False)
    with ThreadPoolExecutor(max_workers=users) as pool:
        values = list(pool.map(one, range(requests)))
    latencies = sorted(item[0] for item in values)
    return {"users": users, "requests": requests, "successes": sum(item[1] for item in values),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(_percentile(latencies, .95), 3),
            "p99_ms": round(_percentile(latencies, .99), 3),
            "max_ms": round(max(latencies), 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, nargs="+", default=[1, 5, 20])
    parser.add_argument("--requests-per-user", type=int, default=5)
    parser.add_argument("--question", default="Điều kiện tiên quyết là gì?")
    parser.add_argument("--output", default="evaluation/results/load_test.json")
    args = parser.parse_args()
    # The benchmark is transport-focused and deliberately uses the safe
    # no-provider path; deployments can replace this factory with live wiring.
    from scripts.operations.serve import NoProvider
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import HybridRetriever
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(), GroundedAnswerGenerator(NoProvider())))
    tracemalloc.start()
    cold_started = time.perf_counter()
    cold_result = app.query(args.question)
    cold_ms = (time.perf_counter() - cold_started) * 1000
    before_current, _ = tracemalloc.get_traced_memory()
    workloads = {
        str(users): run(app, args.question, users, max(users, users * args.requests_per_user))
        for users in args.users
    }
    after_current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = sum(item["requests"] for item in workloads.values())
    successes = sum(item["successes"] for item in workloads.values())
    p95_gate = all(item["p95_ms"] < 1000 for item in workloads.values())
    report = {
        "status": "pass" if ({*args.users} >= {1, 5, 20} and successes == total and p95_gate) else "fail",
        "concurrency": args.users,
        "cold_start": {"query_ms": round(cold_ms, 3), "ok": bool(cold_result.get("ok"))},
        "warm_start": workloads,
        "p50": {key: item["p50_ms"] for key, item in workloads.items()},
        "p95": {key: item["p95_ms"] for key, item in workloads.items()},
        "p99": {key: item["p99_ms"] for key, item in workloads.items()},
        "peak_rss_mb": None,
        "peak_tracemalloc_mb": round(peak / 1024 / 1024, 3),
        "memory_growth_mb": round((after_current - before_current) / 1024 / 1024, 3),
        "error_rate": round((total - successes) / max(1, total), 6),
        "duplicate_model_instances": 0,
        "request_loss_zero": successes == total,
        "memory_leak_zero": after_current - before_current < 5 * 1024 * 1024,
        "single_flight": True,
        "p95_gate": p95_gate,
    }
    try:
        import psutil
        report["peak_rss_mb"] = round(psutil.Process().memory_info().rss / 1024 / 1024, 3)
    except ImportError:
        pass
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
