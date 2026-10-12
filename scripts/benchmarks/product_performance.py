"""Bounded single-process product HTTP measurement; never qualifies local replay.

Prepare and preflight are offline. Collect requires the exact user-approved
packet digest, retains partial failures, and never resumes or retries a run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from wsgiref.simple_server import WSGIRequestHandler, make_server

from campusai.llm.client import LLMResponseError
from campusai.rag.cache import RAGAnswerCache
from campusai.rag.schemas import validate_release_response
from campusai.web import make_wsgi_app
from evaluation.common.artifact_store import entries
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.collect_paired_answers import recording_generate
from evaluation.reranker.measure_reranker_http import _NoAnswerCache, percentile
from scripts.benchmarks.product_quality_pilot import BASE, CONFIG, PROFILE, ROOT, profile_environment
from scripts.operations.serve import build_application
from scripts.benchmarks.product_retry import Budget, load_retry503, validate_retry

CONDITIONS = {"cold_process_cache_off": 18, "warm_process_cache_off": 18,
              "cache_on_first_miss": 18, "cache_on_repeat_hit_1": 18,
              "cache_on_repeat_hit_2": 18, "negative_cache_off": 10}
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"


def available_output(path: Path) -> None:
    """Archived observations still consume their run; missing bytes are not permission."""
    key = path.resolve().relative_to(ROOT.resolve()).as_posix()
    if path.exists() or key in entries():
        raise FileExistsError("measurement already consumed")


def validate_packet(packet: dict) -> None:
    workload = packet["workload"]
    if (packet["profile"] != PROFILE or packet["endpoint"] != ENDPOINT
            or packet["max_provider_calls"] != 54
            or packet["minimum_provider_start_interval_seconds"] != 30
            or len(workload) != 100 or Counter(w["condition"] for w in workload) != CONDITIONS
            or sum(w["planned_provider_call"] for w in workload) != 54
            or [w["ordinal"] for w in workload] != list(range(1, 101))):
        raise ValueError("performance workload or limits changed")
    validate_retry(packet)
    if packet["llm_config"] != read_json_config():
        raise ValueError("LLM configuration changed")
    for row in workload:
        case = packet["cases"][row["qid"]]
        if row["request"] != case["request"] or row["prompt_sha256"] != case["prompt_sha256"]:
            raise ValueError("workload request changed")
        expected_call = row["condition"] in {
            "cold_process_cache_off", "warm_process_cache_off", "cache_on_first_miss"}
        if bool(row["planned_provider_call"]) != expected_call:
            raise ValueError("provider call plan changed")
        if expected_call and not case["provider_body"]:
            raise ValueError("missing exact provider payload")
    for cycle in range(1, 19):
        positive = [w for w in workload if w.get("cycle") == cycle]
        if (len(positive) != 5 or len({w["qid"] for w in positive}) != 1
                or [w["condition"] for w in positive] != ["cold_process_cache_off",
                    "warm_process_cache_off", "cache_on_first_miss",
                    "cache_on_repeat_hit_1", "cache_on_repeat_hit_2"]):
            raise ValueError("cold/warm/cache lifecycle changed")
    if any(w.get("cycle") is not None for w in workload if w["condition"] == "negative_cache_off"):
        raise ValueError("negative tail lifecycle changed")
    if sum(len(packet["cases"][w["qid"]]["prompt"] or "")
           for w in workload if w["planned_provider_call"]) != packet["prompt_chars"]:
        raise ValueError("prompt character budget changed")


def read_json_config():
    from campusai.llm.factory import _read_config
    return _read_config(CONFIG)["llm"]


def prepare(output: Path, workload_path: Path):
    available_output(output)
    workload = read_json(workload_path)
    seed_path = Path(workload["source_packet"]["path"])
    if sha256(seed_path) != workload["source_packet"]["sha256"]:
        raise ValueError("workload seed changed")
    seed = read_json(seed_path)
    # Use the actual serializer, without loading credentials or opening sockets.
    from campusai.llm.client import GeminiClient
    config = read_json_config()
    client = GeminiClient("offline-payload-capture-only", model=config["model"],
                          generation_config=config["generation_config"], max_retries=0, cache=None)
    cases = {}
    for case in seed["cases"]:
        sent = []
        def capture(request, **_kwargs):
            sent.append(json.loads(request.data))
            placeholder = {"answer": "Offline payload capture.", "confidence": "low",
                           "abstained": True, "citations": [], "claims": []}
            return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [
                {"text": json.dumps(placeholder)}]}}]}).encode())
        if case["prompt"]:
            with patch("urllib.request.urlopen", capture):
                client.generate_json(case["prompt"], schema=case["schema"])
            if len(sent) != 1:
                raise ValueError("offline payload capture did not send exactly once")
        cases[case["qid"]] = {k: deepcopy(case[k]) for k in
            ("request", "prompt", "prompt_sha256", "schema", "evidence", "answerable")}
        cases[case["qid"]]["provider_body"] = sent[0] if sent else None
    client.close()
    packet = {"schema_version": 1, "status": "PREPARED_NOT_AUTHORIZED",
        "source_identity": source_identity(ROOT), "profile": PROFILE, "endpoint": ENDPOINT,
        "llm_config": config, "workload": workload["workload"], "cases": cases,
        "max_provider_calls": 54, "max_retries": config["max_retries"], "retry_only_http_status": 503,
        "minimum_provider_start_interval_seconds": 30,
        "prompt_chars": sum(len(cases[w["qid"]]["prompt"] or "")
            for w in workload["workload"] if w["planned_provider_call"]),
        "bindings": {str(p): sha256(p) for p in (workload_path, seed_path, CONFIG,
            Path(PROFILE["CAMPUSAI_INDEX_DIR"]) / "manifest.json",
            Path(PROFILE["CAMPUSAI_RETRIEVAL_CALIBRATION"]))},
        "output_dir": str(BASE / (output.stem.replace("egress-packet", "live"))),
        "quality_or_performance_accepted": False,
        "readiness": "Measure complete startup before HTTP bind, then full first HTTP query; no cache prefill."}
    validate_packet(packet)
    write_json(output, packet)
    print(json.dumps({"packet": str(output), "sha256": sha256(output),
        "requests": 100, "max_provider_calls": 54, "prompt_chars": packet["prompt_chars"],
        "external_calls": 0}))


class ResourceSampler:
    def __init__(self):
        import psutil
        self.process = psutil.Process()
        self.ram_bytes = psutil.virtual_memory().total
        self.peak_rss = self.process.memory_info().rss
        self.samples = 1
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.monitor, daemon=True)

    def monitor(self):
        while not self.stop.wait(.1):
            self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
            self.samples += 1

    def finish(self):
        self.stop.set()
        self.thread.join(5)
        self.peak_rss = max(self.peak_rss, self.process.memory_info().rss)
        import torch
        return {"peak_rss_bytes": self.peak_rss, "physical_ram_bytes": self.ram_bytes,
            "rss_samples": self.samples, "sample_interval_seconds": .1,
            "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
            "cuda_memory_scope": "PyTorch process allocation/reservation; not total driver VRAM"}


def worker(packet_path: Path, output: Path, cycle: int, last_start: float,
           replay_path: Path | None, authorized_digest: str | None):
    available_output(output)
    packet = read_json(packet_path)
    validate_packet(packet)
    if not replay_path and sha256(packet_path) != authorized_digest:
        raise ValueError("worker requires exact packet authorization")
    if source_identity(ROOT) != packet["source_identity"] or any(
            sha256(Path(p)) != d for p, d in packet["bindings"].items()):
        raise ValueError("source or input changed")
    if not replay_path:
        parent = Path(packet["output_dir"])
        if output.resolve() != (parent / f"cycle-{cycle}.json").resolve():
            raise ValueError("worker output must use the consumed parent run")
        lock = read_json(parent / "summary.json")
        if lock.get("packet_sha256") != authorized_digest or lock.get("active_cycle") != cycle:
            raise ValueError("worker not dispatched by the authorized parent")
    rows = [w for w in packet["workload"] if w.get("cycle", 18) == cycle]
    replay = read_json(replay_path) if replay_path else None
    replay_answers = {o["qid"]: o["llm_calls"][0] for o in replay["observations"]
                      if o["llm_calls"]} if replay else {}
    report = {"schema_version": 1, "status": "STARTED_NO_RESTART", "cycle": cycle,
        "pid": os.getpid(), "source_identity": packet["source_identity"],
        "observations": [], "offline_replay": bool(replay), "last_provider_start": last_start,
        "external_provider_calls": 0, "performance_accepted": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf8") as f:
        json.dump(report, f)
    sampler = ResourceSampler()
    sampler.thread.start()
    expected = None
    attempts = 0
    original_urlopen = __import__("urllib.request", fromlist=["urlopen"]).urlopen
    budget = Budget(packet_path, authorized_digest) if not replay and packet["max_retries"] else None
    retry503 = load_retry503()
    attempt_trace = []
    def one_attempt(request, **options):
        nonlocal attempts
        if (expected is None or attempts >= (2 if budget else 1) or not expected["planned_provider_call"]
                or request.full_url != ENDPOINT or request.get_method() != "POST"
                or json.loads(request.data) != packet["cases"][expected["qid"]]["provider_body"]):
            raise LLMResponseError("unapproved payload or repeated provider attempt")
        if not replay and not budget and time.time() - report["last_provider_start"] < 30:
            raise LLMResponseError("provider spacing violation")
        if budget:
            budget.before_attempt(str(expected["ordinal"]), json.loads(request.data), bool(attempts))
        attempts += 1
        report["last_provider_start"] = time.time()
        report["external_provider_calls"] += int(not replay)
        write_json(output, report)  # Durable attempted-call record before egress.
        if replay:
            captured = replay_answers[expected["qid"]]
            return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [
                {"text": captured["response_text"]}]}, "finishReason": "STOP"}],
                "usageMetadata": captured.get("usage") or {}}).encode())
        return original_urlopen(request, **options)
    def guarded_transport(request, **options):
        if attempts:
            raise LLMResponseError("repeated logical provider request")
        if not budget:
            return one_attempt(request, **options)
        return retry503(request, one_attempt, timeout=options["timeout"], attempts=attempt_trace,
            before_retry=lambda: budget.reserve_retry(str(expected["ordinal"])),
            on_change=lambda: write_json(output, report))
    class Quiet(WSGIRequestHandler):
        def log_message(self, *_args):
            pass
    started = time.perf_counter()
    try:
        with ExitStack() as stack:
            stack.enter_context(profile_environment())
            if replay:
                stack.enter_context(patch.dict(os.environ, {"GEMINI_API_KEY": "offline-replay-only"}))
            stack.enter_context(patch("urllib.request.urlopen", guarded_transport))
            import torch
            torch.set_num_threads(8)
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA target unavailable")
            torch.cuda.reset_peak_memory_stats()
            app = build_application()
            stack.callback(app.close)
            report["startup_to_readiness_ms"] = (time.perf_counter() - started) * 1000
            service = app.query_service
            service.cache.close()
            service.cache = _NoAnswerCache()
            service.retriever.query_cache_size = 0
            client = service.answer_generator.llm
            client.max_retries = 0  # Common audited transport owns the one retry.
            client.cache.close()
            client.cache = None
            calls, traces = [], []
            client.generate = recording_generate(client.generate, calls)
            def trace(t):
                t["evidence"] = [e.to_dict() for e in service.last_retrieval]
                traces.append(t)
            with make_server("127.0.0.1", 0, make_wsgi_app(app, telemetry_hook=trace),
                             handler_class=Quiet) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    for row in rows:
                        expected, attempts = row, 0
                        attempt_trace = []
                        report["provider_attempts"] = attempt_trace
                        calls.clear()
                        traces.clear()
                        if row["condition"] == "cache_on_first_miss":
                            service.cache.close()
                            service.cache = RAGAnswerCache()
                        elif row["condition"] == "negative_cache_off":
                            service.cache.close()
                            service.cache = _NoAnswerCache()
                        if row["planned_provider_call"] and not replay:
                            time.sleep(max(0, 30.05 - (time.time() - report["last_provider_start"])))
                        began = time.perf_counter()
                        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=195 if budget else 75)
                        error_type = None
                        status, answer = 0, {}
                        try:
                            connection.request("POST", "/api/query", json.dumps(row["request"], ensure_ascii=False).encode("utf8"),
                                               {"Content-Type": "application/json"})
                            response = connection.getresponse()
                            status, answer = response.status, json.loads(response.read())
                        except Exception as error:
                            error_type = type(error).__name__
                        finally:
                            connection.close()
                        a = answer.get("answer", {})
                        wanted_hit = row["condition"].startswith("cache_on_repeat_hit_")
                        valid = (not error_type and status == 200 and answer.get("ok") and validate_release_response(a)[0]
                            and bool(answer.get("cache_hit")) == wanted_hit
                            and bool(a.get("abstained")) != row["expected_answerable"]
                            and len(calls) == int(row["planned_provider_call"])
                            and int(row["planned_provider_call"]) <= attempts <= int(row["planned_provider_call"]) * (2 if budget else 1)
                            and all(c["provider_status"] == "completed" and not c["cached"] for c in calls)
                            and len(traces) == 1)
                        report["observations"].append({**row, "answer": answer, "http_status": status,
                            "http_ms": (time.perf_counter() - began) * 1000, "calls": deepcopy(calls),
                            "trace": deepcopy(traces[0]) if traces else None,
                            "provider_transport_attempts": attempts, "error_type": error_type, "valid": bool(valid)})
                        report["observations"][-1]["provider_attempts"] = deepcopy(attempt_trace)
                        report["status"] = "PENDING_SOURCE_AND_PERFORMANCE_REVIEW" if valid else "FAILURE_STOPPED"
                        write_json(output, report)
                        if not valid:
                            break
                finally:
                    server.shutdown()
                    thread.join(5)
    except Exception as error:
        report.update(status="HARNESS_OR_HTTP_FAILURE_STOPPED", error_type=type(error).__name__)
    finally:
        report["resources"] = sampler.finish()
        report["source_identity_after"] = source_identity(ROOT)
        if report["source_identity_after"] != packet["source_identity"]:
            report["status"] = "SOURCE_CHANGED_STOPPED"
        if budget and report["status"] != "PENDING_SOURCE_AND_PERFORMANCE_REVIEW":
            budget.stop(report["status"])
        write_json(output, report)
    print(json.dumps({"cycle": cycle, "status": report["status"], "pid": report["pid"],
        "requests": len(report["observations"]), "external_calls": report["external_provider_calls"]}), flush=True)


def collect(packet_path: Path, digest: str | None, output_dir: Path | None = None,
            replay_path: Path | None = None, cycles: list[int] | None = None):
    packet = read_json(packet_path)
    validate_packet(packet)
    if not replay_path and sha256(packet_path) != digest:
        raise ValueError("exact packet authorization mismatch")
    if source_identity(ROOT) != packet["source_identity"] or any(
            sha256(Path(p)) != d for p, d in packet["bindings"].items()):
        raise ValueError("prepared source or input changed")
    budget = Budget(packet_path, digest) if not replay_path and packet["max_retries"] else None
    selected = cycles if replay_path else list(range(1, 19))
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(range(1, 19)):
        raise ValueError("invalid preflight process cycles")
    out = output_dir if replay_path else Path(packet["output_dir"])
    available_output(out / "summary.json")
    out.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "status": "STARTED_NO_RESUME", "packet_sha256": sha256(packet_path),
        "source_identity": packet["source_identity"], "processes": [], "offline_replay": bool(replay_path),
        "external_provider_calls": 0, "performance_accepted": False}
    last_start = 0.0
    for cycle in selected:
        report["active_cycle"] = cycle
        write_json(out / "summary.json", report)
        target = out / f"cycle-{cycle}.json"
        command = [sys.executable, "-m", "scripts.benchmarks.product_performance", "worker",
                   "--packet", str(packet_path), "--output", str(target), "--cycle", str(cycle),
                   "--last-start", str(last_start)]
        if replay_path:
            command += ["--replay", str(replay_path)]
        else:
            command += ["--authorized-packet-sha256", digest]
        run = subprocess.run(command, capture_output=True, text=True, encoding="utf8")
        (out / f"cycle-{cycle}.log").write_text(run.stdout + run.stderr, encoding="utf8")
        if run.returncode or not target.is_file():
            report.update(status="CHILD_FAILURE_STOPPED", failed_cycle=cycle)
            break
        child = read_json(target)
        last_start = child["last_provider_start"]
        report["processes"].append({"path": str(target), "sha256": sha256(target), "pid": child["pid"]})
        report["external_provider_calls"] += child["external_provider_calls"]
        print(run.stdout, end="", flush=True)
        report["status"] = child["status"]
        write_json(out / "summary.json", report)
        if child["status"] != "PENDING_SOURCE_AND_PERFORMANCE_REVIEW":
            break
    children = [read_json(Path(p["path"])) for p in report["processes"]]
    samples = [s for c in children for s in c["observations"]]
    report["http_requests"] = len(samples)
    report["provider_attempts"] = sum(s["provider_transport_attempts"] for s in samples)
    report["conditions"] = dict(Counter(s["condition"] for s in samples))
    report["all_conditions_complete"] = report["conditions"] == CONDITIONS
    report["latency_ms"] = {condition: {"count": len(values), "p95": percentile(values, .95)}
        for condition in CONDITIONS if (values := [s["http_ms"] for s in samples if s["condition"] == condition])}
    report["overall_p95_ms"] = percentile([s["http_ms"] for s in samples], .95) if samples else None
    uncached = [s["http_ms"] for s in samples if s["condition"] in
                {"cold_process_cache_off", "warm_process_cache_off"}]
    report["llm_bearing_cache_off_p95_ms"] = percentile(uncached, .95) if uncached else None
    report["source_stable"] = source_identity(ROOT) == packet["source_identity"]
    report.pop("active_cycle", None)
    if replay_path and len(children) == len(selected) and all(s["valid"] for s in samples):
        report["status"] = "OFFLINE_INTERFACE_PASS_NOT_LIVE_PERFORMANCE"
    elif (not replay_path and len(samples) == 100 and report["all_conditions_complete"]
          and report["source_stable"] and all(s["valid"] for s in samples)
          and 54 <= report["external_provider_calls"] <= 57):
        report["status"] = "PENDING_INDEPENDENT_SOURCE_RESOURCE_AND_PERFORMANCE_REVIEW"
    if budget and report["status"] != "PENDING_INDEPENDENT_SOURCE_RESOURCE_AND_PERFORMANCE_REVIEW":
        budget.stop(report["status"])
    write_json(out / "summary.json", report)
    print(json.dumps({"status": report["status"], "http_requests": len(samples),
                      "external_calls": report["external_provider_calls"]}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_args = commands.add_parser("prepare")
    prepare_args.add_argument("--workload", type=Path, required=True)
    prepare_args.add_argument("--output", type=Path, required=True)
    for name in ("collect", "preflight", "worker"):
        sub = commands.add_parser(name)
        sub.add_argument("--packet", type=Path, required=True)
        if name == "collect":
            sub.add_argument("--authorized-packet-sha256", required=True)
        else:
            sub.add_argument("--replay", type=Path, required=name == "preflight")
        if name == "preflight":
            sub.add_argument("--output-dir", type=Path, required=True)
            sub.add_argument("--cycles", type=int, nargs="+", default=[1, 5])
        if name == "worker":
            sub.add_argument("--authorized-packet-sha256")
            sub.add_argument("--output", type=Path, required=True)
            sub.add_argument("--cycle", type=int, required=True)
            sub.add_argument("--last-start", type=float, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output, args.workload)
    elif args.command == "worker":
        worker(args.packet, args.output, args.cycle, args.last_start, args.replay, args.authorized_packet_sha256)
    elif args.command == "preflight":
        collect(args.packet, None, args.output_dir, args.replay, args.cycles)
    else:
        collect(args.packet, args.authorized_packet_sha256)


if __name__ == "__main__":
    main()
