"""Measure real local RTX 4060 reranker inference over loopback HTTP.

Component telemetry only: it intentionally does not claim RAG/LLM or release S6.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import platform
import subprocess
import threading
import time
import uuid
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "evaluation/results/phase7-completion-20261004/p7-08-local-http-pilot.json"
SMOKE = ROOT / "evaluation/results/phase7-completion-20261004/p7-07-cuda-snapshot-smoke.json"


def main() -> int:
    import psutil
    import torch
    from campusai.retrieval.cross_encoder_provider import (
        ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
    )
    from campusai.retrieval.runtime_provenance import runtime_description
    from evaluation.common.release_artifacts import source_identity, sha256

    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    identity = ModelIdentity(**smoke["model_identity"])
    model_dir = ROOT / ".tmp/phase7-models" / identity.model_revision
    if not torch.cuda.is_available() or snapshot_sha256(model_dir) != identity.model_sha256:
        raise RuntimeError("CUDA device or bound model snapshot is unavailable")
    source_before = source_identity(ROOT)
    process = psutil.Process(os.getpid())
    provider = OfflineCrossEncoderReranker(identity, model_dir, require_ready=True,
        timeout_ms=60000, queue_limit=24, score_cache_size=0)
    baseline_metrics = provider.metrics_snapshot()
    warm_started = time.perf_counter()
    provider.warm_up()
    torch.cuda.synchronize()
    warm_ms = (time.perf_counter() - warm_started) * 1000
    provider_after_warm = provider.metrics_snapshot()
    torch.cuda.reset_peak_memory_stats(0)
    resource_samples = []
    stop = threading.Event()

    def sample_resources():
        while not stop.is_set():
            torch.cuda.synchronize()
            resource_samples.append({
                "at": datetime.now(timezone.utc).isoformat(),
                "monotonic_seconds": time.monotonic(),
                "pid": os.getpid(),
                "rss_bytes": process.memory_info().rss,
                "cpu_percent": process.cpu_percent(None),
                "vram_allocated_bytes": torch.cuda.memory_allocated(0),
                "vram_reserved_bytes": torch.cuda.memory_reserved(0),
                "vram_capacity_bytes": torch.cuda.get_device_properties(0).total_memory,
                "queue_depth": provider.metrics_snapshot()["queue_depth"],
                "active_requests": provider.metrics_snapshot()["active_requests"],
            })
            stop.wait(.1)

    process.cpu_percent(None)
    sampler = threading.Thread(target=sample_resources, name="p7-08-resource-sampler", daemon=True)
    sampler.start()
    request_observations = []
    observations_lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request_id = self.headers.get("X-Request-ID", "")
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            accepted = time.perf_counter()
            outcome = "failed"
            reason = None
            fields = {"route_selected": True, "inference_attempted": False,
                      "inference_completed": False, "ranking_applied": False}
            try:
                payload = json.loads(raw.decode("utf-8"))
                candidates = [RerankCandidate(str(item["candidate_id"]), "telemetry-doc",
                    str(item["candidate_id"]), 1, str(item["content"]), i + 1, 1.0 / (i + 1))
                    for i, item in enumerate(payload["candidates"])]
                fields["inference_attempted"] = True
                result = provider.score(str(payload["query"]), candidates, timeout_ms=60000)
                fields["inference_completed"] = True
                fields["ranking_applied"] = True
                outcome = "completed"
                body = {"request_id": request_id, "results": [
                    {"candidate_id": item.candidate_id, "score": item.reranker_score,
                     "rank": item.final_rank} for item in result]}
                status = 200
            except Exception as error:
                reason = type(error).__name__
                body, status = {"request_id": request_id, "error": reason}, 500
            serialization_started = time.perf_counter()
            encoded = json.dumps(body, allow_nan=False).encode("utf-8")
            serialization_ms = (time.perf_counter() - serialization_started) * 1000
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            finished = time.perf_counter()
            sample = {"request_id": request_id, "pid": os.getpid(), "http_status": status,
                "outcome": outcome, "reason": reason, **fields,
                "accepted_monotonic_seconds": accepted,
                "finished_monotonic_seconds": finished,
                "server_total_ms": (finished - accepted) * 1000,
                "serialization_ms": serialization_ms,
                "provider_trace": provider.last_call,
                "cache_enabled": False, "llm_stage_observed": False}
            with observations_lock:
                request_observations.append(sample)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, name="p7-08-local-http", daemon=True)
    server_thread.start()
    address = f"http://127.0.0.1:{server.server_port}/rerank"
    profiles = []
    try:
        for concurrency in (1, 5, 10, 20):
            requests = 100
            def send(number):
                request_id = str(uuid.uuid4())
                payload = {"query": f"Local telemetry query {number}: course prerequisites",
                    "candidates": [{"candidate_id": f"c{idx}", "content":
                        f"Candidate {idx}: a Vietnamese engineering curriculum course with credits and prerequisites."}
                        for idx in range(20)]}
                started = time.perf_counter()
                status, error = 0, None
                try:
                    req = Request(address, data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json", "X-Request-ID": request_id}, method="POST")
                    with urlopen(req, timeout=90) as response:
                        status = response.status
                        json.loads(response.read())
                except Exception as exc:
                    error = type(exc).__name__
                ended = time.perf_counter()
                return {"request_id": request_id, "started_monotonic_seconds": started,
                    "finished_monotonic_seconds": ended, "client_total_ms": (ended - started) * 1000,
                    "http_status": status, "error": error}
            block_started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                samples = list(pool.map(send, range(requests)))
            block_duration = time.perf_counter() - block_started
            ordered = sorted(s["client_total_ms"] for s in samples)
            summary = {"requests": len(samples), "errors": sum(s["error"] is not None or s["http_status"] != 200 for s in samples),
                "p50_ms": ordered[int(.50 * len(ordered))], "p95_ms": ordered[int(.95 * len(ordered)) - 1],
                "p99_ms": ordered[int(.99 * len(ordered)) - 1],
                "successful_rps": sum(s["error"] is None and s["http_status"] == 200 for s in samples) / block_duration,
                "duration_seconds": block_duration}
            metrics = provider.metrics_snapshot()
            profiles.append({"concurrency": concurrency, "summary": summary,
                "provider_metrics_cumulative": metrics, "samples": samples})
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=10)
        stop.set()
        sampler.join(timeout=5)
        provider.close()
        provider.drain()
        torch.cuda.synchronize()
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader"], text=True, timeout=5).strip()
    source_after = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-08", "status": "component_diagnostic",
        "release_eligible": False,
        "measurement_scope": "real local loopback HTTP -> actual CUDA cross-encoder reranker; no RAG retrieval or LLM provider call",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_before": source_before, "source_after": source_after,
        "source_stable": source_before == source_after,
        "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
        "model_snapshot_sha256": identity.model_sha256, "snapshot_smoke_sha256": sha256(SMOKE),
        "runtime_environment": runtime_description(), "gpu_nvidia_smi": gpu,
        "host_profile": {"os": platform.platform(), "python": platform.python_version(),
            "logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
            "physical_ram_bytes": psutil.virtual_memory().total,
            "vram_capacity_bytes": torch.cuda.get_device_properties(0).total_memory,
            "deployment_scope": "local RTX 4060 laptop; not a public server profile"},
        "http_profile": {"address_scope": "127.0.0.1 loopback only", "concurrency": [1, 5, 10, 20],
            "requests_per_concurrency": 100, "candidates_per_request": 20,
            "candidate_score_cache_enabled": False, "answer_cache_enabled": False,
            "llm_calls": 0, "p95_release_budget_ms": None,
            "profiles": profiles, "request_observations": request_observations},
        "resource_samples": resource_samples,
        "resource_peaks": {"rss_bytes": max((s["rss_bytes"] for s in resource_samples), default=0),
            "cpu_percent": max((s["cpu_percent"] for s in resource_samples), default=0),
            "vram_allocated_bytes": max((s["vram_allocated_bytes"] for s in resource_samples), default=0),
            "vram_reserved_bytes": max((s["vram_reserved_bytes"] for s in resource_samples), default=0)},
        "warmup": {"duration_ms": warm_ms, "model_loads": provider_after_warm["model_loads"],
                   "inference_calls": provider_after_warm["inference_calls"]},
        "baseline_provider_metrics": baseline_metrics,
        "provider_metrics_after_close": provider.metrics_snapshot(),
        "limitations": [
            "Component HTTP pilot does not exercise CampusAI RAG/grounding/LLM or calibrated route policy.",
            "Synthetic candidate text is for runtime load only; no benchmark qids or quality claims are involved.",
            "No public host or external LLM/provider profile was available; LLM duration/cost remains unknown.",
            "This report is not M7 or S6 evidence and cannot satisfy the Phase 7 end-to-end HTTP acceptance gate."
        ]
    }
    report["ended_at"] = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "profiles": [
        {"concurrency": p["concurrency"], **p["summary"]} for p in profiles],
        "resource_peaks": report["resource_peaks"], "samples": len(resource_samples),
        "request_observations": len(request_observations), "source_stable": report["source_stable"],
        "output": OUT.relative_to(ROOT).as_posix()}, indent=2))
    return int(not report["source_stable"] or any(p["summary"]["errors"] for p in profiles))


if __name__ == "__main__":
    raise SystemExit(main())
