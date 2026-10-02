"""Run an isolated local staging process and collect actual canary requests.

Healthy observations alone do not grant M11: the separate staging fault
exercises must also be supplied to audit_canary_staging.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import uuid

from evaluation.reranker.canary_telemetry import CanaryWindowRecorder
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.release_artifacts import (
    policy_bindings, require_previous_gates, sha256, source_identity, write_json,
)
from evaluation.reranker.release_workflow import measurement_environment


def collect_windows(service, recorder, rows, *, requests=100, concurrency=1, checkpoint=None):
    if requests < 100 or concurrency < 1:
        raise ValueError("at least 100 requests and positive concurrency required")
    if (not any(not row["answerable"] for row in rows)
            or not any(row["answerable"] and row["difficulty"] == "easy" for row in rows)
            or not any(row["answerable"] and row["difficulty"] == "hard" for row in rows)):
        raise ValueError("reviewed workload needs negative, easy and hard cohorts")
    # Complete cycles retain every cohort, including when it appears after
    # the first hundred rows. Request identities remain unique across windows.
    cycles = max(1, (requests + len(rows) - 1) // len(rows))
    workload = rows * cycles
    run_id = uuid.uuid4().hex
    windows = []
    try:
        for step in (0, 1, 5, 10, 25):
            if service.canary.traffic_percent != step:
                raise ValueError("live service did not reach the expected traffic step")
            for number in range(3):
                recorder.start()
                def request(item):
                    index, row = item
                    return recorder.retrieve(row, request_id=f"{run_id}-{step}-{number}-{index}")
                with ThreadPoolExecutor(max_workers=concurrency) as workers:
                    # Consume results so instrumentation failures cannot be
                    # silently omitted from an otherwise healthy window.
                    list(workers.map(request, enumerate(workload)))
                window = recorder.finish()
                reason = service.observe_canary_window(window)
                window["service_phase7_enabled_after"] = service.retriever.phase7_enabled
                window["observed_rollback_reason"] = reason
                windows.append(window)
                if checkpoint:
                    checkpoint(windows)
                if reason or not service.retriever.phase7_enabled:
                    raise ValueError("live staging rolled back: " + str(reason or service.retriever.phase7_activation_reason))
            if step != 25:
                service.canary.promote()
        return windows
    finally:
        recorder.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--deployment-ram-bytes", type=int)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--environment-id", default="local-staging")
    parser.add_argument("--output", type=Path, default=Path(".release/reranker/staging_observations.json"))
    parser.add_argument("--fault-output", type=Path, default=Path(".release/reranker/staging_fault_observations.json"))
    args = parser.parse_args(argv)
    service = recorder = None
    try:
        require_previous_gates("M11", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
        if args.requests < 100 or args.concurrency < 1 or not args.environment_id.strip():
            raise ValueError("invalid staging identity or workload size")
        if args.output.exists() or args.fault_output.exists() or args.output.resolve() == args.fault_output.resolve():
            raise ValueError("staging output exists; select a new output for a new run")
        import psutil
        physical_ram = psutil.virtual_memory().total
        ram = args.deployment_ram_bytes or physical_ram
        if not 0 < ram <= physical_ram:
            raise ValueError("deployment RAM budget cannot exceed measured host RAM")
        # The CLI itself is a separate process; activation and its model are
        # isolated from the application used by real users.
        os.environ.update(measurement_environment(args))
        from campusai.rag.grounding import GroundedAnswerGenerator
        from campusai.rag.service import CampusAIQueryService
        from campusai.retrieval.calibration import RetrievalPolicy
        from campusai.retrieval.canary_rollout import CanaryController
        from campusai.retrieval.hybrid import HybridRetriever
        from campusai.retrieval.reranker_activation import build_phase7_retriever
        phase6 = args.results_dir / "hybrid_retrieval_calibration.json"
        retriever = build_phase7_retriever(args.index_dir, phase6, args.benchmark_dir / "human_retrieval_dev.jsonl")
        if not retriever.phase7_enabled:
            raise ValueError("staging activation rejected: " + retriever.phase7_activation_reason)
        retriever.query_cache_size = 0
        baseline = HybridRetriever(args.index_dir, query_cache_size=0,
                                   policies={"hybrid_rrf": RetrievalPolicy.from_report(phase6)})
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(), canary=CanaryController())
        recorder = CanaryWindowRecorder(service, baseline, frozen_evidence(args.index_dir), ram_limit_bytes=ram)
        workload = args.benchmark_dir / "human_retrieval_test.jsonl"
        rows = [json.loads(line) for line in workload.read_text(encoding="utf-8").splitlines() if line.strip()]
        metadata = {**source_identity(Path(__file__).resolve().parents[2]), **policy_bindings(args.results_dir),
                    "index_sha256": sha256(args.index_dir / "manifest.json"),
                    "phase6_calibration_sha256": sha256(phase6),
                    "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
                    "model_identity_sha256": retriever.phase7_provider.model_identity.fingerprint,
                    "environment": "staging", "environment_id": args.environment_id,
                    "collector": "campusai.canary_telemetry.v1", "workload_sha256": sha256(workload),
                    "deployment": {"kind": "isolated_local_process", "pid": os.getpid(),
                                   "host": platform.node(), "device": args.device, "physical_ram_bytes": physical_ram,
                                   "ram_budget_bytes": ram, "concurrency": args.concurrency}}
        checkpoint = lambda windows: write_json(args.output, {**metadata, "status": "incomplete", "windows": windows})
        windows = collect_windows(service, recorder, rows, requests=args.requests,
                                  concurrency=args.concurrency, checkpoint=checkpoint)
        write_json(args.output, {**metadata, "status": "healthy_windows_collected", "windows": windows})
        retriever.phase7_provider.close()
        retriever.phase7_provider.drain()
        from evaluation.reranker.staging_fault_exercises import run_fault_exercises
        def activate():
            value = build_phase7_retriever(args.index_dir, phase6, args.benchmark_dir / "human_retrieval_dev.jsonl")
            value.query_cache_size = 0
            return value
        fault_checkpoint = lambda exercises: write_json(args.fault_output, {**metadata, "status": "incomplete", "exercises": exercises})
        exercises = run_fault_exercises(activate, baseline, frozen_evidence(args.index_dir), rows, windows,
                                       ram_limit_bytes=ram, requests=args.requests, checkpoint=fault_checkpoint)
        write_json(args.fault_output, {**metadata, "status": "fault_exercises_collected", "exercises": exercises})
        print(json.dumps({"status": "staging_collected", "windows": len(windows), "fault_exercises": len(exercises),
                          "output": str(args.output), "fault_output": str(args.fault_output)}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 1
    finally:
        if recorder:
            recorder.close()
        if service:
            service.close()
            service.retriever.phase7_provider.close()


if __name__ == "__main__":
    raise SystemExit(main())
