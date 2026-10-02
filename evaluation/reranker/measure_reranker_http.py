"""Measure the complete HTTP -> retrieval -> grounded live-LLM response path.

Run only after M0-M6. The measured server is local, threaded and uses the
exact frozen release policy. Both answer and LLM caches are disabled so every
recorded LLM stage is a provider call. Raw per-request evidence is retained.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
from socketserver import ThreadingMixIn
import subprocess
from threading import Event, Lock, Thread
import time
from urllib.request import Request, urlopen
from wsgiref.simple_server import WSGIServer

from evaluation.common.release_artifacts import (policy_bindings, require_previous_gates,
                                          sha256, source_identity, write_json)

CONCURRENCIES = (1, 5, 10, 20)
MAX_P95_BUDGET_MS = 20_000


class _ThreadedHTTPServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = True


class _NoAnswerCache:
    """The release workload must exercise retrieval and LLM on every request."""
    def get(self, _key):
        return None

    def put(self, _key, _answer):
        return None

    @contextmanager
    def lock(self, _key):
        yield

    def close(self):
        return None


def percentile(values: list[float], fraction: float) -> float:
    if not values or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("invalid HTTP latency samples")
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


def cohort(row: dict) -> dict[str, bool]:
    return {"hard": row.get("difficulty") == "hard", "easy": row.get("difficulty") == "easy",
            "negative": row.get("answerable") is False,
            "scoped": bool(row.get("doc_ids") or row.get("filters"))}


def workload(rows: list[dict], count: int) -> list[dict]:
    if count < 100 or len(rows) < 30 or any(row.get("split") != "test" for row in rows):
        raise ValueError("HTTP workload needs at least 30 frozen test rows and 100 requests")
    if len({row["qid"] for row in rows}) != len(rows):
        raise ValueError("duplicate HTTP workload qid")
    if any(sum(flags[name] for flags in map(cohort, rows)) < 5 for name in ("hard", "easy", "negative", "scoped")):
        raise ValueError("HTTP workload lacks hard/easy/negative/scoped coverage")
    # Stable interleave brings each cohort into even small profiles; the raw
    # qid sequence is stored and the validator recomputes coverage.
    selected, used = [], set()
    for name in ("hard", "easy", "negative", "scoped"):
        for row in rows:
            if cohort(row)[name] and row["qid"] not in used and sum(cohort(r)[name] for r in selected) < 5:
                selected.append(row)
                used.add(row["qid"])
    selected.extend(row for row in rows if row["qid"] not in used)
    return [selected[i % len(selected)] for i in range(count)]


def summarize_http_samples(samples: list[dict], *, p95_budget_ms: int) -> dict:
    if p95_budget_ms <= 0 or p95_budget_ms > MAX_P95_BUDGET_MS or len(samples) < 100:
        raise ValueError("invalid HTTP profile or SLO")
    if len({sample.get("request_id") for sample in samples}) != len(samples):
        raise ValueError("HTTP request ids must be unique")
    for sample in samples:
        if (not isinstance(sample.get("qid"), str) or type(sample.get("http_status")) is not int
                or type(sample.get("error")) is not bool or type(sample.get("cache_hit")) is not bool
                or not isinstance(sample.get("cohort"), dict) or not isinstance(sample.get("stages_ms"), dict)
                or not isinstance(sample.get("stage_calls"), dict)):
            raise ValueError("invalid raw HTTP sample")
        percentile([sample["client_total_ms"], sample["server_total_ms"]], 1)
        for value in sample["stages_ms"].values():
            percentile([value], 1)
    latency = [sample["client_total_ms"] for sample in samples]
    stage_names = ("routing", "retrieval", "retrieval_parse", "bm25", "dense", "fusion",
                   "reranker_wait", "reranker_queue", "reranker_inference_observed",
                   "grounding", "llm", "citation_validation", "serialization", "transport")
    def stage_value(sample, name):
        if name == "transport":
            return max(0.0, sample["client_total_ms"] - sample["server_total_ms"])
        if name in {"retrieval_parse", "bm25", "dense", "fusion"}:
            key = "parse" if name == "retrieval_parse" else name
            return ((sample.get("retrieval_trace") or {}).get("latency_ms") or {}).get(key, 0.0)
        return sample["stages_ms"].get(name, 0.0)
    stages = {name: {"p50_ms": percentile([stage_value(sample, name) for sample in samples], .5),
                     "p95_ms": percentile([stage_value(sample, name) for sample in samples], .95)}
              for name in stage_names}
    counts = {name: sum(sample["cohort"].get(name) is True for sample in samples)
              for name in ("hard", "easy", "negative", "scoped")}
    return {"requests": len(samples), "cohorts": counts, "p50_ms": percentile(latency, .5),
            "p95_ms": percentile(latency, .95), "p99_ms": percentile(latency, .99),
            "successful_rps": sum(not sample["error"] for sample in samples)
            / max(1e-9, (max(sample["finished_at"] for sample in samples)
                         - min(sample["started_at"] for sample in samples))),
            "errors": sum(sample["error"] for sample in samples),
            "cache_hits": sum(sample["cache_hit"] for sample in samples),
            "llm_calls": sum(sample["stage_calls"].get("llm", 0) for sample in samples),
            "grounded_answers": sum(not sample["abstained"] and bool(sample["citations"])
                                    for sample in samples), "stages": stages,
            "passed": (len(samples) >= 100 and all(count >= 5 for count in counts.values())
                       and percentile(latency, .95) <= p95_budget_ms
                       and sum(sample["error"] for sample in samples) == 0
                       and sum(sample["cache_hit"] for sample in samples) == 0
                       and sum(sample["stage_calls"].get("llm", 0) for sample in samples) >= 30
                       and sum(not sample["abstained"] and bool(sample["citations"])
                               for sample in samples) >= 30
                       and all(sample.get("abstention_reason") != "llm_error" for sample in samples))}


def _gpu_memory_bytes() -> int | None:
    try:
        value = subprocess.check_output(["nvidia-smi", "--query-compute-apps=used_gpu_memory",
                                         "--format=csv,noheader,nounits"], text=True, timeout=2)
        return sum(int(line.strip()) for line in value.splitlines() if line.strip()) * 1024**2
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--llm-config", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--p95-budget-ms", type=int, default=10_000)
    parser.add_argument("--deployment-ram-bytes", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.deployment_ram_bytes <= 0 or not 0 < args.p95_budget_ms <= MAX_P95_BUDGET_MS:
        parser.error("invalid deployment RAM or HTTP p95 budget")
    require_previous_gates("M7", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    from campusai.api import CampusAIApplication
    from campusai.llm.client import GeminiClient, OpenAICompatibleClient
    from campusai.llm.factory import create_llm
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.reranker_activation import build_phase7_retriever
    from campusai.web import make_wsgi_app
    import psutil
    from wsgiref.simple_server import WSGIRequestHandler, make_server

    frozen_test = args.benchmark_dir / "human_retrieval_test.jsonl"
    rows = [json.loads(line) for line in frozen_test.read_text(encoding="utf-8").splitlines() if line.strip()]
    requests = workload(rows, args.requests)
    model_identity = json.loads((args.results_dir / "model_snapshot_smoke.json").read_text(encoding="utf-8"))["model_identity"]
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, snapshot_sha256
    identity = ModelIdentity(**model_identity)
    if args.model_dir.name != identity.model_revision or snapshot_sha256(args.model_dir) != identity.model_sha256:
        raise ValueError("physical model snapshot does not match M3")
    from evaluation.reranker.release_workflow import measurement_environment
    from argparse import Namespace
    env = measurement_environment(Namespace(model_dir=args.model_dir, results_dir=args.results_dir,
                                            model_name=identity.model_name, device=identity.device, queue_limit=19))
    llm = create_llm(args.llm_config)
    if type(llm) not in (GeminiClient, OpenAICompatibleClient):
        raise ValueError("HTTP release measurement requires a concrete live LLM client")
    original_cache = llm.cache
    llm.cache = None
    original_cache.close()
    process = psutil.Process()
    peak_rss, peak_gpu = [process.memory_info().rss], [_gpu_memory_bytes()]
    stop = Event()
    process.cpu_percent()
    cpu_percent = [0.0]
    def monitor():
        last_gpu_check = 0.0
        while not stop.wait(.1):
            peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
            cpu_percent[0] = max(cpu_percent[0], process.cpu_percent())
            if identity.device.startswith("cuda") and time.monotonic() - last_gpu_check >= .5:
                gpu = _gpu_memory_bytes()
                if gpu is not None:
                    peak_gpu[0] = max(peak_gpu[0] or 0, gpu)
                last_gpu_check = time.monotonic()
    monitor_thread = Thread(target=monitor, daemon=True)
    monitor_thread.start()
    profiles = []
    cold_start = time.perf_counter()
    try:
        for concurrency in CONCURRENCIES:
            retriever = build_phase7_retriever(args.index_dir,
                args.results_dir / "hybrid_retrieval_calibration.json",
                args.benchmark_dir / "human_retrieval_dev.jsonl", environ=env)
            if not retriever.phase7_enabled or retriever.phase7_policy.rerank_candidate_cap != json.loads(
                    (args.results_dir / "reranker_score_calibration.json").read_text(encoding="utf-8"))["rerank_candidate_cap"]:
                raise ValueError("HTTP runtime activation or release cap mismatch")
            retriever.query_cache_size = 0
            service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm), cache=_NoAnswerCache(),
                                           default_mode="phase7")
            application = CampusAIApplication(service)
            telemetry, telemetry_lock = {}, Lock()
            def observe(trace):
                with telemetry_lock:
                    telemetry[trace["request_id"]] = trace
            class QuietHandler(WSGIRequestHandler):
                def log_message(self, *_args):
                    pass
            server = make_server("127.0.0.1", 0, make_wsgi_app(application, telemetry_hook=observe),
                                 server_class=_ThreadedHTTPServer, handler_class=QuietHandler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            address = f"http://127.0.0.1:{server.server_port}/api/query"
            if concurrency == 1:
                retriever.phase7_provider.warm_up()
                cold_start = (time.perf_counter() - cold_start) * 1000
            def send(row):
                started = time.perf_counter()
                payload = {"question": row["question"], "doc_ids": row.get("doc_ids"),
                           "filters": row.get("filters") or {}, "top_k": 5,
                           "language": row.get("language", "vi")}
                if payload["doc_ids"] is None:
                    payload.pop("doc_ids")
                status, body, request_id, error = 0, {}, None, None
                try:
                    request = Request(address, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                      headers={"Content-Type": "application/json"}, method="POST")
                    with urlopen(request, timeout=90) as response:
                        status, request_id = response.status, response.headers.get("X-Request-ID")
                        body = json.loads(response.read())
                except Exception as exc:
                    error = type(exc).__name__
                finished = time.perf_counter()
                with telemetry_lock:
                    trace = telemetry.pop(request_id, None)
                answer = body.get("answer", {}) if isinstance(body, dict) else {}
                citations = answer.get("citations", []) if isinstance(answer, dict) else []
                invalid_scope = any(c.get("doc_id") not in (row.get("doc_ids") or
                    json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"])
                                    for c in citations if isinstance(c, dict))
                return {"qid": row["qid"], "question_sha256": hashlib.sha256(row["question"].encode()).hexdigest(),
                        "cohort": cohort(row), "scope_doc_ids": row.get("doc_ids"), "started_at": started,
                        "finished_at": finished, "client_total_ms": (finished - started) * 1000,
                        "request_id": request_id, "http_status": status,
                        "error": bool(error or status != 200 or not body.get("ok") or trace is None or invalid_scope),
                        "error_type": error or ("response_or_scope" if status != 200 or not body.get("ok") or invalid_scope else None),
                        "cache_hit": bool(trace and trace["cache_hit"]),
                        "abstained": answer.get("abstained", True), "citations": citations,
                        "abstention_reason": answer.get("abstention_reason"),
                        "server_total_ms": trace["server_total_ms"] if trace else 0.0,
                        "stages_ms": trace["stages_ms"] if trace else {},
                        "stage_calls": trace["stage_calls"] if trace else {},
                        "retrieval_trace": trace["retrieval_trace"] if trace else None}
            try:
                retriever.phase7_provider.warm_up()
                with ThreadPoolExecutor(max_workers=concurrency) as workers:
                    samples = list(workers.map(send, requests))
                retriever.phase7_provider.drain()
                profiles.append({"concurrency": concurrency, "requests": args.requests, "samples": samples,
                                 "summary": summarize_http_samples(samples, p95_budget_ms=args.p95_budget_ms),
                                 "provider_metrics": retriever.phase7_provider.metrics_snapshot()})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                # The LLM client is shared across profiles and is closed last.
                service.answer_generator.llm = None
                application.close()
    finally:
        stop.set()
        monitor_thread.join(timeout=2)
        close = getattr(llm, "close", None)
        if close is not None:
            close()
    bindings = {**source_identity(Path(__file__).resolve().parents[2]), **policy_bindings(args.results_dir),
                "index_sha256": sha256(args.index_dir / "manifest.json"),
                "phase6_calibration_sha256": sha256(args.results_dir / "hybrid_retrieval_calibration.json"),
                "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
                "model_identity_sha256": identity.fingerprint,
                "test_sha256": sha256(frozen_test), "llm_config_sha256": sha256(args.llm_config)}
    status = "pass" if (all(p["summary"]["passed"] for p in profiles)
                          and peak_rss[0] <= .75 * args.deployment_ram_bytes
                          and (not identity.device.startswith("cuda") or peak_gpu[0] is not None)) else "conditional"
    report = {"schema_version": 1, "phase": 7, "status": status, **bindings,
              "llm_provider": llm.provider, "llm_model": llm.model, "llm_cache_enabled": False,
              "answer_cache_enabled": False, "profile": "threaded-wsgi-local-http",
              "release_rerank_cap": json.loads((args.results_dir / "reranker_score_calibration.json").read_text(encoding="utf-8"))["rerank_candidate_cap"],
              "p95_budget_ms": args.p95_budget_ms, "deployment_ram_bytes": args.deployment_ram_bytes,
              "peak_rss_bytes": peak_rss[0], "peak_gpu_memory_bytes": peak_gpu[0],
              "peak_cpu_percent": cpu_percent[0],
              "cold_start_ms": cold_start, "profiles": profiles}
    write_json(args.output or args.results_dir / "reranker_http_end_to_end.json", report)
    print(json.dumps({"status": status, "profiles": [p["summary"] for p in profiles]}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
