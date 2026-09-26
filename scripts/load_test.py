"""Small reproducible concurrency smoke test for the application adapter."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.api import CampusAIApplication


def run(application: CampusAIApplication, question: str, users: int) -> dict:
    def one(_):
        started = time.perf_counter()
        result = application.query(question)
        return (time.perf_counter() - started) * 1000, result.get("ok", False)
    with ThreadPoolExecutor(max_workers=users) as pool:
        values = list(pool.map(one, range(users)))
    latencies = sorted(item[0] for item in values)
    return {"users": users, "successes": sum(item[1] for item in values),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(latencies[min(len(latencies)-1, int(len(latencies)*.95))], 3)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, nargs="+", default=[1, 5, 20])
    parser.add_argument("--question", default="Điều kiện tiên quyết là gì?")
    parser.add_argument("--output", default="evaluation/results/load_test.json")
    args = parser.parse_args()
    # The benchmark is transport-focused and deliberately uses the safe
    # no-provider path; deployments can replace this factory with live wiring.
    from scripts.serve import NoProvider
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import HybridRetriever
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(), GroundedAnswerGenerator(NoProvider())))
    report = {str(users): run(app, args.question, users) for users in args.users}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
