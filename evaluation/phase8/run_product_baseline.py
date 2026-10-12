"""Checkpoint the frozen product baseline within an owner-declared Free Tier.

One immutable preflight/manifest, one daily shard, no resend of completed rows.
No billing APIs, model switching, failure-triggered key rotation or hidden probes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from unittest.mock import patch
import uuid
from zoneinfo import ZoneInfo

import psutil

from campusai.llm.client import GeminiClient
from campusai.llm.factory import _read_config
from campusai.web import make_wsgi_app
from evaluation.common.release_artifacts import source_identity
from evaluation.phase8.prepare_product_run import _NoCache, _request
from evaluation.phase8.repair_reviewed_benchmark import FREEZE, OUT, verify_freeze
from evaluation.phase8.score_temporal_product_outputs import _index_tree_sha256
from evaluation.phase8.validate_automated_review import ROOT, require, sha256

PREFLIGHT = Path("evaluation/results/phase8-product-preflight-v5.json")
MANIFEST = Path("evaluation/results/phase8-product-run-v5.json")
STATE = Path("evaluation/results/phase8-product-execution-v5.json")
PREDICTIONS = Path("evaluation/results/phase8-product-predictions-v5.jsonl")
AMENDMENT = Path("evaluation/results/phase8-product-credential-amendment-v5.json")


class StopRun(BaseException):
    """Abort before any additional request, including provider-client retries."""


@contextmanager
def exclusive_run():
    """A stale lock after a process crash requires audit, never a second worker."""
    lock = (ROOT / STATE).with_suffix(".lock")
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write(path, value):
    path = ROOT / path
    temporary = path.with_name(path.name + ".writing")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def pacific_day(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()


def body_hash(body):
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def serialized_body(case, config):
    captured = []
    client = GeminiClient("offline-only-no-credential", model=config["model"],
                          generation_config=config["generation_config"], cache=None,
                          limiter=None, max_retries=0, timeout=config["timeout_seconds"])
    def capture(request, **_options):
        captured.append(json.loads(request.data))
        raise StopRun()
    with patch("urllib.request.urlopen", side_effect=capture):
        try:
            client.generate_json(case["prompt"], schema=case["schema"])
        except StopRun:
            pass
    require(len(captured) == 1, "serializer did not produce one provider body")
    return captured[0]


def execution_packet(manifest):
    """Retain the original approval; permit a verified reliability-only addendum."""
    original = read(PREFLIGHT)
    if not (ROOT / AMENDMENT).exists():
        return original
    amendment = read(AMENDMENT)
    require(amendment["status"] == "APPROVED_OWNER_RELIABILITY_AMENDMENT", "amendment incomplete")
    require(amendment["manifest_sha256"] == sha256(ROOT / MANIFEST)
            and amendment["original_source_identity"] == original["source_identity"], "amendment binding mismatch")
    replacement = amendment["verified_preflight"]
    require(replacement["sha256"] == sha256(ROOT / replacement["path"]), "amended preflight drift")
    packet = read(replacement["path"])
    for field in ("benchmark", "index", "profile", "provider_call_count_estimate", "prompt_characters"):
        require(packet[field] == original[field], "reliability amendment changed " + field)
    fields = ("qid", "request", "planned_provider_call", "prompt", "schema", "retrieved_evidence")
    require([[case.get(f) for f in fields] for case in packet["cases"]] ==
            [[case.get(f) for f in fields] for case in original["cases"]], "request/evidence drift")
    config = _read_config(ROOT / packet["llm_config"]["path"])["llm"]
    require({c["qid"]: body_hash(serialized_body(c, config)) for c in packet["cases"]
             if c["planned_provider_call"]} == manifest["provider_body_sha256_by_qid"], "provider payload drift")
    return packet


def verify_inputs(manifest, packet):
    verify_freeze()
    require(manifest["freeze_sha256"] == sha256(ROOT / FREEZE), "freeze drift")
    require(manifest["preflight_sha256"] == sha256(ROOT / PREFLIGHT), "preflight drift")
    require(packet["benchmark"]["path"] == OUT.as_posix() and
            packet["benchmark"]["sha256"] == sha256(ROOT / OUT), "benchmark drift")
    require(packet["source_identity"] == source_identity(ROOT), "source/runtime drift; do not resume")
    require(packet["llm_config"]["sha256"] == sha256(ROOT / packet["llm_config"]["path"]), "LLM config drift")
    index = ROOT / packet["index"]["path"]
    require(packet["index"]["manifest_sha256"] == sha256(index / "manifest.json") and
            packet["index"]["tree_sha256"] == _index_tree_sha256(index), "index drift")
    require(manifest["free_tier_only"] is True and manifest["daily_attempt_cap"] == 18
            and manifest["max_attempts"] == packet["provider_call_count_estimate"] + 18
            and manifest["min_start_spacing_seconds"] == 30, "budget policy drift")


def _prepare():
    require(not (ROOT / MANIFEST).exists() and not (ROOT / STATE).exists()
            and not (ROOT / PREDICTIONS).exists(), "run already prepared; do not create another version")
    packet = read(PREFLIGHT)
    config = _read_config(ROOT / packet["llm_config"]["path"])["llm"]
    require(config["provider"] == "gemini" and config["model"] == "gemini-3.8-flash"
            and config["generation_config"]["maxOutputTokens"] == 1024
            and config["timeout_seconds"] == 15, "unexpected product profile")
    calls = {c["qid"]: body_hash(serialized_body(c, config)) for c in packet["cases"]
             if c["planned_provider_call"]}
    manifest = {"schema_version": 1, "phase": 8, "status": "PREPARED_NO_REQUESTS",
                "freeze_sha256": sha256(ROOT / FREEZE), "preflight_sha256": sha256(ROOT / PREFLIGHT),
                "free_tier_only": True, "billing_enabled_by_runner": False,
                "free_tier_basis": "Owner requires Free Tier only; this runner cannot query the project's billing tier.",
                "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                "model": config["model"], "daily_attempt_cap": 18,
                "max_attempts": len(calls) + 18, "planned_calls": len(calls),
                "prompt_characters": packet["prompt_characters"], "max_output_tokens_per_attempt": 1024,
                "max_prompt_characters": packet["prompt_characters"] + 18 * max(
                    (len(c["prompt"]) for c in packet["cases"] if c["planned_provider_call"]), default=0),
                "max_output_tokens_total": (len(calls) + 18) * 1024,
                "min_start_spacing_seconds": 30, "timeout_seconds": 15,
                "immediate_retries": 0, "one_shard_per_pacific_day": True,
                "failure_policy": "Stop at the first provider/response failure; resume the same pending qid on a later Pacific day within the total attempt cap. Completed rows are never resent.",
                "provider_body_sha256_by_qid": calls, "source_identity": packet["source_identity"],
                "authorization_basis": "Active Phase 8 completion goal and prior permission to use project keys with Free Tier only; no billing or paid fallback.",
                "provider_requests_sent": 0}
    verify_inputs(manifest, packet)
    write(MANIFEST, manifest)
    write(STATE, {"schema_version": 1, "status": "prepared", "manifest_sha256": sha256(ROOT / MANIFEST),
                  "predictions": [], "attempts": [], "shards": [], "peak_working_set_bytes": 0})
    return {"status": "PREPARED_NO_REQUESTS", "planned_calls": len(calls),
            "max_attempts": manifest["max_attempts"], "daily_attempt_cap": 18,
            "prompt_characters": packet["prompt_characters"], "manifest_sha256": sha256(ROOT / MANIFEST)}


def prepare():
    with exclusive_run():
        return _prepare()


def claim_day(state, day):
    if day in {s["pacific_day"] for s in state["shards"]}:
        amendment = read(AMENDMENT) if (ROOT / AMENDMENT).exists() else {}
        require(amendment.get("allow_remaining_daily_attempts") is True
                and amendment.get("availability_pacific_day") == day,
                "daily shard already used; wait for Pacific reset")
    require(len(state["attempts"]) < read(MANIFEST)["max_attempts"], "total attempt budget exhausted")
    require(sum(event.get("pacific_day") == day for event in state["attempts"]) < 18,
            "aggregate daily attempt budget exhausted; wait for Pacific reset")


def available_credential(state, credentials, day):
    amendment = read(AMENDMENT)
    order = amendment.get("availability_order") if amendment.get("availability_pacific_day") == day else None
    if not order:
        return None  # Historical six-attempt allocation remains reproducible.
    require(set(order) == {name for name, _ in credentials} and len(order) == len(credentials),
            "invalid availability order")
    blocked = {event.get("credential_name") for event in state["attempts"]
               if event.get("http_status") in {401, 403} or
               (event.get("http_status") == 429 and event.get("pacific_day") == day)}
    keys = dict(credentials)
    for name in order:
        if name not in blocked:
            return name, keys[name]
    raise ValueError("no eligible credential remains; quota reset or owner key replacement required")


def _run(credentials=None):
    manifest, state = read(MANIFEST), read(STATE)
    packet = execution_packet(manifest)
    verify_inputs(manifest, packet)
    require(state["manifest_sha256"] == sha256(ROOT / MANIFEST), "execution manifest binding mismatch")
    require(state["status"] in {"prepared", "waiting_next_pacific_day"},
            "run completed, invalid, exhausted or requires interrupted-shard audit")
    cases = packet["cases"]
    require([r["qid"] for r in state["predictions"]] == [c["qid"] for c in cases[:len(state["predictions"])]],
            "checkpoint is not a unique benchmark prefix")
    day = pacific_day()
    claim_day(state, day)
    require(bool(os.environ.get("GEMINI_API_KEY")), "credential missing")
    credential_fingerprint = hashlib.sha256(os.environ["GEMINI_API_KEY"].encode()).hexdigest()
    require(state.get("credential_fingerprint", credential_fingerprint) == credential_fingerprint,
            "credential changed; key rotation is not part of this run")
    state["credential_fingerprint"] = credential_fingerprint
    selected_credential = None
    if credentials:
        fingerprints = {name: hashlib.sha256(key.encode()).hexdigest() for name, key in credentials}
        require(state.get("credential_pool", fingerprints) == fingerprints, "credential pool changed")
        state["credential_pool"] = fingerprints
        state["credential_amendment_sha256"] = sha256(ROOT / AMENDMENT)
        selected_credential = available_credential(state, credentials, day)
    else:
        require(not state.get("credential_pool"), "use run-pool for the approved credential allocation")
    shard = {"pacific_day": day, "runtime_id": uuid.uuid4().hex,
             "started_at": datetime.now(timezone.utc).isoformat(), "status": "running", "attempts": 0}
    state["shards"].append(shard)
    state["status"] = "running"
    write(STATE, state)
    current = None
    call_count = 0
    previous_starts = [event["started_at"] for event in state["attempts"]
                       if event.get("pacific_day") == day and event.get("started_at")]
    last_start = (time.monotonic() - max(0, (datetime.now(timezone.utc) -
                  datetime.fromisoformat(previous_starts[-1])).total_seconds())) if previous_starts else 0.0
    failure = False
    original_transport = urllib.request.urlopen

    def transport(request, **options):
        nonlocal call_count, last_start, failure
        if failure:
            raise StopRun("provider attempt already failed; no immediate retry")
        if pacific_day() != day:
            raise StopRun("Pacific quota window changed during this shard")
        require(current is not None and current["planned_provider_call"] and call_count == 0,
                "unexpected additional provider request")
        require(request.get_method() == "POST" and request.full_url == manifest["endpoint"] and
                body_hash(json.loads(request.data)) == manifest["provider_body_sha256_by_qid"][current["qid"]],
                "provider payload drift")
        if sum(event.get("pacific_day") == day for event in state["attempts"]) >= 18 or len(state["attempts"]) >= manifest["max_attempts"]:
            raise StopRun("attempt budget reached")
        prompts = {case["qid"]: len(case["prompt"] or "") for case in cases}
        spent_characters = sum(prompts[event["qid"]] for event in state["attempts"])
        if spent_characters + prompts[current["qid"]] > manifest["max_prompt_characters"]:
            raise StopRun("prompt character budget reached")
        require(not last_start or time.monotonic() - last_start >= 30,
                "provider start spacing violated")
        event = {"qid": current["qid"], "pacific_day": day, "status": "attempted",
                 "started_at": datetime.now(timezone.utc).isoformat(),
                 "body_sha256": manifest["provider_body_sha256_by_qid"][current["qid"]]}
        if credentials:
            event["credential_name"] = (selected_credential or credentials[min(shard["attempts"] // 6, len(credentials) - 1)])[0]
        state["attempts"].append(event)
        shard["attempts"] += 1
        call_count += 1
        write(STATE, state)  # Durable reservation before external I/O.
        last_start = time.monotonic()
        transport_started = time.perf_counter()
        try:
            response = original_transport(request, **options)
        except Exception as error:
            failure = True
            event.update(status="failed", error_type=type(error).__name__, http_status=getattr(error, "code", None),
                         transport_latency_ms=round((time.perf_counter() - transport_started) * 1000, 3))
            write(STATE, state)
            raise
        event.update(status="http_response_received", http_status=getattr(response, "status", 200),
                     transport_latency_ms=round((time.perf_counter() - transport_started) * 1000, 3))
        write(STATE, state)
        return response

    from scripts.operations.serve import build_application
    before = source_identity(ROOT)
    startup_ms = 0.0
    shard_requests = 0
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, packet["profile"]))
            stack.enter_context(patch("urllib.request.urlopen", side_effect=transport))
            import torch
            torch.set_num_threads(8)
            started = time.perf_counter()
            application = build_application()
            startup_ms = (time.perf_counter() - started) * 1000
            stack.callback(application.close)
            service = application.query_service
            service.cache.close()
            service.cache = _NoCache()
            service.retriever.query_cache_size = 0
            # Keep the product's generation settings, but prevent an automatic
            # retry from consuming quota after this shard's first failure.
            llm = service.answer_generator.llm
            if llm.cache is not None:
                llm.cache.close()
            llm.cache = None
            provider_outputs = []
            original_generate = llm.generate
            def generate(*args, **options):
                response = original_generate(*args, **options)
                provider_outputs.append({"final_text": response.text, "usage": response.usage,
                    "finish_reason": response.finish_reason, "model_version": response.model_version,
                    "latency_ms": response.latency_ms, "cached": response.cached})
                return response
            llm.generate = generate
            original_generate_json = llm.generate_json
            def generate_json(prompt, schema=None, **options):
                nonlocal failure
                require(current is not None and current["prompt"] == prompt and current["schema"] == schema,
                        "runtime prompt/schema differs from preflight")
                try:
                    return original_generate_json(prompt, schema=schema, **options)
                except Exception:
                    failure = True
                    raise
            llm.generate_json = generate_json
            answers = []
            original_ask = service.ask
            def ask(*args, **options):
                answer = original_ask(*args, **options)
                answers.append(answer.to_dict())
                return answer
            service.ask = ask
            web = make_wsgi_app(application)
            for current in cases[len(state["predictions"]):]:
                if current["planned_provider_call"] and (sum(event.get("pacific_day") == day for event in state["attempts"]) >= 18 or
                        len(state["attempts"]) >= manifest["max_attempts"]):
                    break
                if credentials:
                    # Use an eligible key for missing rows; historical allocation
                    # remains available when no availability policy is approved.
                    # No automatic failover/retry occurs on provider failure.
                    llm.api_key = (selected_credential or credentials[min(shard["attempts"] // 6, len(credentials) - 1)])[1]
                call_count = 0
                answers.clear()
                provider_outputs.clear()
                if current["planned_provider_call"] and last_start:
                    # Quota pacing is outside the user-request latency measurement.
                    wait = max(0, 30 - (time.monotonic() - last_start))
                    if wait:
                        # Roundoff must never make the strict 30s guard fire
                        # after an otherwise sufficient quota-pacing sleep.
                        time.sleep(wait + 0.000001)
                started = time.perf_counter()
                status, result = _request(web, current["request"])
                elapsed_ms = (time.perf_counter() - started) * 1000
                require(status == "200 OK" and result.get("ok") is True and len(answers) == 1,
                        "product HTTP/response capture failed")
                if failure:
                    state["failed_product_response"] = {"qid": current["qid"], "internal": answers[0],
                        "public": result["answer"], "provider_output": provider_outputs[0] if provider_outputs else None,
                        "request_latency_ms": round(elapsed_ms, 3), "cold_start": shard_requests == 0,
                        "startup_ms": round(startup_ms if shard_requests == 0 else 0, 3),
                        "latency_ms": round(elapsed_ms + (startup_ms if shard_requests == 0 else 0), 3)}
                    memory = psutil.Process().memory_info()
                    state["peak_working_set_bytes"] = max(state["peak_working_set_bytes"],
                        getattr(memory, "peak_wset", memory.rss))
                    break
                require(call_count == int(current["planned_provider_call"]), "provider-call count drift")
                require(len(provider_outputs) == call_count, "provider-output capture mismatch")
                state["predictions"].append({"qid": current["qid"], "internal_response": answers[0],
                    "public_response": result["answer"], "retrieved_evidence": [x.to_dict() for x in service.last_retrieval],
                    "provider_output": provider_outputs[0] if provider_outputs else None,
                    "request_latency_ms": round(elapsed_ms, 3), "cold_start": shard_requests == 0,
                    "startup_ms": round(startup_ms if shard_requests == 0 else 0, 3),
                    "latency_ms": round(elapsed_ms + (startup_ms if shard_requests == 0 else 0), 3),
                    "runtime_id": shard["runtime_id"]})
                shard_requests += 1
                state["peak_working_set_bytes"] = max(state["peak_working_set_bytes"],
                    getattr(psutil.Process().memory_info(), "peak_wset", psutil.Process().memory_info().rss))
                write(STATE, state)
    except (Exception, StopRun) as error:
        shard.update(error_type=type(error).__name__)
        failure = True
    finally:
        shard.update(ended_at=datetime.now(timezone.utc).isoformat(), requests_completed=shard_requests,
                     startup_ms=round(startup_ms, 3), status="stopped_on_error" if failure else "daily_shard_complete")
        if source_identity(ROOT) != before:
            state["status"] = "invalid_source_drift"
        else:
            state["status"] = "completed" if len(state["predictions"]) == len(cases) else "waiting_next_pacific_day"
            if state["status"] != "completed" and len(state["attempts"]) >= manifest["max_attempts"]:
                state["status"] = "attempt_budget_exhausted"
        if state["status"] == "completed":
            with (ROOT / PREDICTIONS).open("x", encoding="utf-8", newline="\n") as stream:
                for row in state["predictions"]:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            state["bindings"] = {"benchmark_sha256": packet["benchmark"]["sha256"],
                                 "predictions_sha256": sha256(ROOT / PREDICTIONS),
                                 "index_manifest_sha256": packet["index"]["manifest_sha256"],
                                 "index_tree_sha256": packet["index"]["tree_sha256"]}
            state["measurement_method"] = "Maximum OS process peak_wset across daily worker processes; startup included once in each runtime's cold request; quota pacing between requests excluded, provider latency included."
        write(STATE, state)
    return {"status": state["status"], "rows_completed": len(state["predictions"]),
            "rows_total": len(cases), "attempts": len(state["attempts"]), "shard": shard}


def run():
    with exclusive_run():
        return _run()


def run_pool():
    from scripts.operations.with_gemini_key import read_key
    with exclusive_run():
        amendment = read(AMENDMENT)
        require(amendment["status"] == "APPROVED_OWNER_RELIABILITY_AMENDMENT", "pool not authorized")
        names = amendment["credential_order"]
        require(names == ["key_2", "key_3", "key_1"], "unexpected credential allocation")
        credentials = [(name, read_key(ROOT / "configs/key.yaml", name)) for name in names]
        fingerprints = {name: hashlib.sha256(key.encode()).hexdigest() for name, key in credentials}
        require(len(set(fingerprints.values())) == 3, "duplicate credentials do not supply independent quota")
        require(fingerprints == amendment["credential_fingerprints"], "approved credential changed")
        with patch.dict(os.environ, {"GEMINI_API_KEY": credentials[0][1]}):
            return _run(credentials)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "run-pool", "status"))
    args = parser.parse_args()
    result = prepare() if args.action == "prepare" else run() if args.action == "run" else run_pool() if args.action == "run-pool" else {
        "status": read(STATE)["status"], "rows_completed": len(read(STATE)["predictions"]),
        "attempts": len(read(STATE)["attempts"])}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
