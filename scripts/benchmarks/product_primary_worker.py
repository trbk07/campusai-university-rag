"""Isolated paired application worker. Imports each arm from its own source tree.

Preparation intercepts the real serializer without credentials or external I/O.
Live operation accepts only parent-dispatched, exact-packet HTTP observations.
"""
from __future__ import annotations

from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import http.client
import io
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch
from wsgiref.simple_server import WSGIRequestHandler, make_server


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def emit(value):
    print("PRIMARY_RESULT " + json.dumps(value, ensure_ascii=False), flush=True)


def provider_error_diagnostic(error, *, prompt, api_key):
    """Keep only bounded provider error metadata; never persist the raw response body."""
    try:
        payload = json.loads(error.read(16_384).decode("utf8", errors="replace"))
        detail = payload.get("error", {}) if isinstance(payload, dict) else {}
    except Exception:
        return {}
    if not isinstance(detail, dict):
        return {}

    message = detail.get("message")
    if isinstance(message, str):
        for sensitive in (api_key, prompt):
            if sensitive:
                message = message.replace(sensitive, "[REDACTED]")
        message = message[:512]
    reasons = []
    for row in detail.get("details", []):
        if not isinstance(row, dict):
            continue
        reason = row.get("reason")
        if isinstance(reason, str) and reason.replace("_", "").isalnum():
            reasons.append(reason[:64])
    result = {}
    if isinstance(detail.get("status"), str):
        result["provider_error_status"] = detail["status"][:64]
    if message:
        result["provider_error_message"] = message
    if reasons:
        result["provider_error_reasons"] = reasons[:8]
    return result


class NoAnswerCache:
    def lock(self, *_args, **_kwargs):
        return nullcontext()

    def get(self, *_args, **_kwargs):
        return None

    def put(self, *_args, **_kwargs):
        pass

    def close(self):
        pass


def main():
    mode, arm, setup_name, output_name = sys.argv[1:5]
    setup = read(setup_name)
    if mode not in {"prepare", "live", "recorded"} or arm not in {"baseline", "current"}:
        raise ValueError("unknown worker mode or arm")
    output = Path(output_name)
    output.open("x", encoding="utf8").close()
    tree = Path(setup["trees"][arm]).resolve()
    sys.path[:0] = [str(tree), str(tree / "src")]
    # All application imports occur after selecting the isolated arm.
    import torch
    from campusai.llm.client import GeminiClient
    from campusai.llm.rate_limiter import RateLimiter
    from campusai.web import make_wsgi_app
    from campusai.rag.context import benchmark_retrieval_request
    from campusai.rag.service import retrieval_query
    from scripts.operations.serve import build_application
    import campusai.retrieval.reranker_activation as activation

    config = setup["llm_config"]
    adapter_path = Path(__file__).resolve().with_name("product_retry.py")
    spec = importlib.util.spec_from_file_location("_product_acceptance_budget", adapter_path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    budget = adapter.Budget(setup_name, digest(setup_name)) if mode == "live" and setup["max_retries"] else None
    retry503 = adapter.load_retry503()
    client = GeminiClient("offline-payload-capture-only" if mode != "live"
        else os.environ["GEMINI_API_KEY"], model=config["model"], max_retries=0,
        cache=None, timeout=config["timeout_seconds"],
        limiter=RateLimiter(config["requests_per_minute"]) if mode == "live" else None)
    generate = client.generate
    calls, sent = [], []
    report = {"mode": mode, "arm": arm, "pid": os.getpid(), "observations": [],
              "external_provider_calls": 0, "quality_accepted": False,
              "status": "STARTED_NO_RESTART", "offline_synthetic_limiter_disabled": mode != "live",
              "measurement_scope": "recorded Chat application processing, not live provider latency" if mode == "recorded" else mode}
    recorded = {}
    if mode == "recorded":
        binding = setup["recorded_chat"]
        if digest(binding["path"]) != binding["sha256"]:
            raise ValueError("recorded Chat input changed")
        for item in read(binding["path"])["responses"]:
            key = (item["arm"], item["qid"])
            if key in recorded:
                raise ValueError("duplicate recorded Chat response")
            recorded[key] = item["response"]
        needed = {(a, qid) for a, cases in setup["cases"].items()
                  for qid, case in cases.items() if case["provider_body"]}
        if set(recorded) != needed:
            raise ValueError("recorded Chat cohort incomplete or contains extra responses")
    expected, attempts, last_start = None, 0, 0.0
    attempt_trace = []
    original_transport = __import__("urllib.request", fromlist=["urlopen"]).urlopen

    def shared_generate(prompt, **options):
        options["generationConfig"] = {**config["generation_config"], **options.get("generationConfig", {})}
        call = {"prompt": prompt, "options": deepcopy(options), "provider_status": "attempted"}
        calls.append(call)
        started = time.perf_counter()
        try:
            response = generate(prompt, **options)
            call.update(provider_status="completed", response_text=response.text,
                        usage=response.usage, cached=response.cached,
                        model_version=getattr(response, "model_version", None))
            return response
        except Exception as error:
            call.update(provider_status="failed", error_type=type(error).__name__)
            raise
        finally:
            call["latency_ms"] = (time.perf_counter() - started) * 1000

    def one_attempt(request, **options):
        nonlocal attempts, last_start
        body = json.loads(request.data)
        if attempts >= (2 if budget else 1) or expected is None or request.get_method() != "POST" or request.full_url != setup["endpoint"]:
            raise RuntimeError("unexpected provider attempt")
        if mode in {"live", "recorded"} and body != expected["provider_body"]:
            raise RuntimeError("recorded or live payload differs from prepared input")
        if mode == "live":
            if body != expected["provider_body"] or (not budget and time.time() - last_start < 30):
                raise RuntimeError("payload or global spacing changed")
            if budget:
                budget.before_attempt(f"{arm}:{expected['qid']}", body, bool(attempts))
        attempts += 1
        sent.append(body)
        if mode == "prepare":
            placeholder = {"answer": "Insufficient evidence.", "citations": [], "claims": [],
                "confidence": "low", "abstained": True, "abstention_reason": "provider_abstained"}
            return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [
                {"text": json.dumps(placeholder)}]}, "finishReason": "STOP"}]}).encode())
        if mode == "recorded":
            return io.BytesIO(json.dumps({"candidates": [{"content": {"parts": [
                {"text": json.dumps(recorded[arm, expected["qid"]], ensure_ascii=False)}]},
                "finishReason": "STOP"}],
                "modelVersion": "owner-mediated-gemini-chat-ui-model-unverified"}, ensure_ascii=False).encode("utf8"))
        last_start = time.time()
        report["external_provider_calls"] += 1
        report["pending_attempt"] = {"qid": expected["qid"], "step": report["active_step"],
                                     "provider_start": last_start, "http_status": None}
        write(output, report)  # Persist before external I/O; never resume partial runs.
        try:
            return original_transport(request, **options)
        except Exception as error:
            report["pending_attempt"].update(error_type=type(error).__name__,
                                              http_status=getattr(error, "code", None))
            if getattr(error, "code", None) is not None and hasattr(error, "read"):
                report["pending_attempt"].update(provider_error_diagnostic(
                    error, prompt=body.get("contents", [{}])[0].get("parts", [{}])[0].get("text", ""),
                    api_key=os.environ.get("GEMINI_API_KEY", "")))
            write(output, report)
            raise

    def transport(request, **options):
        if attempts:
            raise RuntimeError("repeated logical provider request")
        if not budget:
            return one_attempt(request, **options)
        return retry503(request, one_attempt, timeout=options["timeout"], attempts=attempt_trace,
            before_retry=lambda: budget.reserve_retry(f"{arm}:{expected['qid']}"),
            on_change=lambda: write(output, report))

    client.generate = shared_generate
    old_hybrid = activation.HybridRetriever

    def aligned_hybrid(*args, **kwargs):
        return old_hybrid(*args, **kwargs, dense_device="cuda")

    class Quiet(WSGIRequestHandler):
        def log_message(self, *_args):
            pass

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, setup["profile"]))
            stack.enter_context(patch("scripts.operations.serve.create_llm", return_value=client))
            stack.enter_context(patch("urllib.request.urlopen", transport))
            if arm == "baseline":
                stack.enter_context(patch.object(activation, "HybridRetriever", aligned_hybrid))
            torch.set_num_threads(8)
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA target unavailable")
            started = time.perf_counter()
            app = build_application()
            stack.callback(app.close)
            report["startup_ms"] = (time.perf_counter() - started) * 1000
            service = app.query_service
            if service.retriever.phase7_enabled:
                raise RuntimeError("reranker must remain disabled")
            service.cache.close()
            service.cache = NoAnswerCache()
            service.retriever.query_cache_size = 0
            docs = read(Path(setup["profile"]["CAMPUSAI_INDEX_DIR"]) / "manifest.json")["documents"]
            traces = []

            def trace(value):
                value["evidence"] = [v.to_dict() for v in service.last_retrieval]
                traces.append(value)

            with make_server("127.0.0.1", 0, make_wsgi_app(app, telemetry_hook=trace),
                             handler_class=Quiet) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                seen = set()
                try:
                    emit({"ready": True, "arm": arm})
                    commands = ({"qid": r["qid"]} for r in setup["rows"]) if mode in {"prepare", "recorded"} else (
                        json.loads(line) for line in sys.stdin if line.strip())
                    rows = {r["qid"]: r for r in setup["rows"]}
                    for command in commands:
                        if command.get("stop"):
                            break
                        qid = command["qid"]
                        if qid in seen:
                            raise ValueError("repeated paired observation")
                        seen.add(qid)
                        row = rows[qid]
                        expected = row if mode == "prepare" else setup["cases"][arm][qid]
                        if mode == "live":
                            lock = read(Path(setup["output_dir"]) / "summary.json")
                            if (command["digest"] != digest(setup_name)
                                or lock.get("packet_sha256") != command["digest"]
                                or lock.get("active_step") != command["step"]
                                or setup["schedule"][command["step"]] != {"arm": arm, "qid": qid}
                                or output.resolve() != (Path(setup["output_dir"]) / f"{arm}.json").resolve()):
                                raise ValueError("worker not dispatched by consumed parent")
                            last_start = command["last_provider_start"]
                            report["active_step"] = command["step"]
                        attempts = 0
                        attempt_trace = []
                        report["provider_attempts"] = attempt_trace
                        calls.clear()
                        sent.clear()
                        traces.clear()
                        answer, status, error_type = {}, 0, None
                        began = time.perf_counter()
                        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=195 if budget else 75)
                        try:
                            connection.request("POST", "/api/query", json.dumps(row["request"], ensure_ascii=False).encode("utf8"),
                                               {"Content-Type": "application/json"})
                            response = connection.getresponse()
                            status, answer = response.status, json.loads(response.read())
                        except Exception as error:
                            error_type = type(error).__name__
                        finally:
                            connection.close()
                        observation = {"qid": qid, "request": row["request"], "http_status": status,
                            "observed_at": datetime.now(timezone.utc).isoformat(),
                            "answer": answer, "http_ms": (time.perf_counter() - began) * 1000,
                            "error_type": error_type, "calls": deepcopy(calls), "provider_transport_attempts": attempts,
                            "provider_model_version": next((c.get("model_version") for c in calls
                                if c.get("provider_status") == "completed"), None),
                            "provider_attempt": deepcopy(report.get("pending_attempt")),
                            "provider_attempts": deepcopy(attempt_trace),
                            "provider_body": deepcopy(sent[0]) if sent else None,
                            "trace": deepcopy(traces[0]) if traces else None, "last_provider_start": last_start}
                        if mode == "prepare":
                            candidate_request = benchmark_retrieval_request(row["benchmark_row"], docs)
                            candidate_request["query"] = retrieval_query(candidate_request["query"])
                            observation["actual_retrieval_request"] = candidate_request
                            observation["candidates"] = [v.to_dict() for v in service.retriever.generate_candidates(
                                **candidate_request, top_k=40, mode="auto")]
                        valid = (not error_type and status == 200 and answer.get("ok") and len(traces) == 1
                            and len(calls) == int(bool(sent)) and all(c["provider_status"] == "completed" and not c["cached"] for c in calls))
                        if mode in {"live", "recorded"}:
                            planned = int(bool(expected["provider_body"]))
                            valid = valid and (planned <= attempts <= planned * (2 if budget else 1)
                                and observation["trace"]["evidence"] == expected["evidence"]
                                and (mode == "recorded" or not planned or bool(observation["provider_model_version"])))
                        observation["interface_valid"] = bool(valid)
                        report["observations"].append(observation)
                        report.pop("pending_attempt", None)
                        report["status"] = "PENDING_SOURCE_REVIEW" if valid else "FAILURE_STOPPED"
                        write(output, report)
                        if mode == "live":
                            emit({"qid": qid, "valid": bool(valid), "last_provider_start": last_start,
                                  "external_provider_calls": report["external_provider_calls"],
                                  "model_version": observation["provider_model_version"]})
                        if not valid:
                            break
                finally:
                    server.shutdown()
                    thread.join(5)
            modules = {n: str(Path(m.__file__).resolve()) for n, m in sys.modules.items()
                if n.split(".")[0] in {"campusai", "scripts", "evaluation"} and getattr(m, "__file__", None)}
            if not all(Path(p).is_relative_to(tree) for p in modules.values()):
                raise RuntimeError("application import escaped isolated source")
            report["isolated_modules"] = modules
    except Exception as error:
        report.update(status="HARNESS_FAILURE_STOPPED", error_type=type(error).__name__)
    finally:
        if budget and report["status"] != "PENDING_SOURCE_REVIEW":
            budget.stop(report["status"])
        getattr(client, "close", lambda: None)()
        write(output, report)
    return 0 if report["status"] == "PENDING_SOURCE_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
