"""Collect real CampusAI inference with a strict benchmark-to-runtime boundary.

Gold and annotation fields stay in the scorer process/artifacts. This collector
never constructs model output from gold, never rotates credentials and stops
on the first provider failure. Captures remain provisional until release validation.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time

from campusai.llm import client as client_module
from campusai.llm.client import LLMError
from campusai.llm.factory import create_llm, _read_config
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.calibration import load_calibration_artifact
from campusai.rag.service import CampusAIQueryService
from campusai.rag.document_scope import DocumentScopeUnavailable, RegisteredDocumentScopeReader
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.common.release_artifacts import source_identity, write_json, verify_index_files
from evaluation.grounding.repair_benchmark import load_rows, stable_hash


def _http_plan(llm, case, pdf_sources=None):
    if not hasattr(llm, 'prepare_json_request'):
        if case.get('generation_arguments', {}).get('pdf_documents'):
            raise ValueError('PDF preflight requires a request-aware provider')
        return None
    arguments = json.loads(json.dumps(case.get('generation_arguments', {})))
    for doc in arguments.get('pdf_documents', []):
        if 'data' not in doc:
            doc['data'] = pdf_sources[doc['sha256']]['data']
    body = llm.prepare_json_request(case['prompt'], case['answer_schema'], **arguments)
    plan = [{'endpoint':llm.endpoint, 'body_sha256':stable_hash(body)}]
    if arguments.get('pdf_documents'):
        plan.insert(0, {'endpoint':llm.endpoint.removesuffix(':generateContent')+':countTokens',
            'body_sha256':stable_hash({'generateContentRequest':{'model':'models/'+llm.model,**body}})})
    return plan


def inference_request(row: dict) -> dict:
    """Only user-provided request semantics may cross into CampusAI."""
    request = {"question": row["question"], "language": row.get("language", "vi")}
    for source, target in (("selected_doc_ids", "doc_ids"), ("context", "history"),
                           ("selected_text", "selected_text"), ("filters", "filters")):
        if source in row:
            request[target] = row[source]
    return request


def pinned_calibrator(path: Path | None, expected_sha256: str | None, benchmark: Path):
    """Verify the calibration input before creating a provider client."""
    if bool(path) != bool(expected_sha256):
        raise ValueError("calibration artifact and pinned payload checksum are required together")
    if path is None:
        return None, None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (payload.get("fit_split") != "dev"
            or payload.get("benchmark_sha256") != hashlib.sha256(benchmark.read_bytes()).hexdigest()):
        raise ValueError("collector calibration must bind this benchmark and declare dev-only fitting")
    return load_calibration_artifact(path, expected_sha256=expected_sha256)


def collect(service, rows: list[dict], llm, *, max_provider_calls: int,
            output: Path, transport=None, egress_prompts: dict | None = None,
            run_metadata: dict | None = None, http503_recovery: dict | None = None,
            egress_requests: dict | None = None) -> dict:
    """Capture final model text and the actual evidence seen by current service."""
    if type(max_provider_calls) is not int or max_provider_calls < 1:
        raise ValueError("max_provider_calls must be positive")
    if egress_requests is not None and (not isinstance(egress_requests, dict) or any(
            not isinstance(identifier, str) or not isinstance(requests, list) or any(
                not isinstance(item, dict) or set(item) != {'endpoint', 'body_sha256'}
                or not all(isinstance(value, str) for value in item.values())
                for item in requests) for identifier, requests in egress_requests.items())):
        raise ValueError('invalid exact HTTP permission map')
    if http503_recovery is not None:
        decision = http503_recovery.get('decision', {})
        packet_hash = (run_metadata or {}).get('egress_packet_sha256')
        budget = decision.get('packet_budgets', {}).get(packet_hash)
        if (decision.get('status') != 'authorized' or decision.get('recover_http503_once') is not True
                or not decision.get('owner_id') or not decision.get('decision_reference')
                or type(budget) is not int or max_provider_calls > budget):
            raise ValueError('explicit scoped HTTP503 recovery authorization required')
    if output.exists() and any(output.iterdir()):
        raise ValueError("native run exists; never overwrite predictions or failures")
    output.mkdir(parents=True, exist_ok=True)
    # Persist before network and before pipeline post-processing. An abrupt
    # process loss must retain spent attempts and returned outputs; absence of
    # a final run.json keeps the interrupted run ineligible for scoring.
    def journal(name, value):
        with (output / name).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    for name in ('raw-model.jsonl', 'predictions.jsonl', 'provider-posts.jsonl'):
        (output / name).touch(exist_ok=False)
    started_metadata = {**(run_metadata or {}),
        'status': 'RUNNING_RELEASE_INELIGIBLE_UNTIL_FINALIZED', 'pid': os.getpid(),
        'started_at': datetime.now(timezone.utc).isoformat(),
        'selected_ids': [row['id'] for row in rows], 'provider_call_cap': max_provider_calls,
        'generation_kind': 'native', 'gold_seeded': False, 'official_predictions': 0,
        'request_boundary': 'question-language-declared-scope-history-only-v1'}
    if egress_requests is not None:
        started_metadata.update(egress_requests=egress_requests,
                                http_body_policy='exact-request-bodies-v1')
    write_json(output / 'run-started.json', started_metadata)
    raw, predictions, posts = [], [], []
    active = {"id": None}
    original_generate = llm.generate
    previous_transport = client_module._request_json
    selected_transport = transport or previous_transport
    stop_reason = None

    def audited_transport(request, *args, **kwargs):
        if len(posts) >= max_provider_calls:
            raise LLMError("native collection provider budget reached")
        body = json.loads(request.data)
        fingerprint = {'endpoint': request.full_url, 'body_sha256': stable_hash(body)}
        pdf_request = ('generateContentRequest' in body or any('inlineData' in part
            for content in body.get('contents', []) for part in content.get('parts', [])))
        if ((egress_requests is not None or pdf_request) and
                fingerprint not in (egress_requests or {}).get(active['id'], [])):
            raise LLMError('egress HTTP body or endpoint changed; no request sent')
        posts.append({"id": active["id"], "started_at": datetime.now(timezone.utc).isoformat(),
                      "endpoint": request.full_url, "request_body_sha256": stable_hash(body)})
        journal('provider-posts.jsonl', posts[-1])
        result = selected_transport(request, *args, **kwargs)
        if request.full_url.endswith(':countTokens'):
            measurement = {**fingerprint, 'response': result}
            raw[-1].setdefault('input_measurements', []).append(measurement)
            journal('model-started.jsonl', {'event':'token_measurement_returned',
                'id':active['id'], 'capture_index':len(raw)-1, **measurement})
        return result

    def audited_generate(prompt, **kwargs):
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        if egress_prompts is not None:
            permitted = egress_prompts.get(active["id"], [])
            if isinstance(permitted, str):
                permitted = [permitted]  # Historical single-prompt packets.
            if prompt_hash not in permitted:
                raise LLMError("egress payload changed; no request sent")
        capture = {"id": active["id"], "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                   "generation_arguments": kwargs, "started_at": datetime.now(timezone.utc).isoformat()}
        if kwargs.get('pdf_documents') is not None:
            import base64
            body = llm.prepare_request(prompt, **kwargs)
            reference = json.loads(json.dumps(body))
            for content in reference['contents']:
                for part in content['parts']:
                    if 'inlineData' in part:
                        data = part['inlineData'].pop('data')
                        part['inlineData']['sha256'] = hashlib.sha256(base64.b64decode(data,validate=True)).hexdigest()
            capture['pdf_request'] = {'model':llm.model, 'endpoint':llm.endpoint,
                'body_reference':reference, 'body_sha256':stable_hash(body)}
        raw.append(capture)
        journal('model-started.jsonl', {**capture, 'capture_index': len(raw)-1})
        try:
            response = original_generate(prompt, **kwargs)
        except Exception as error:
            cause = error.__cause__
            status = getattr(cause, "code", None)
            number = getattr(getattr(cause, "reason", None), "winerror", None)
            capture.update(success=False, error_type=type(error).__name__,
                           completed_at=datetime.now(timezone.utc).isoformat(),
                           cause_type=type(cause).__name__ if cause is not None else None,
                           http_status=status if type(status) is int else None,
                           network_winerror=number if type(number) is int else None)
            journal('raw-model.jsonl', capture)
            raise
        capture.update(success=True, raw_model_text=response.text, usage=response.usage,
            cached=response.cached, finish_reason=response.finish_reason, model_version=response.model_version,
            latency_ms=response.latency_ms)
        try:
            capture["parsed_model_json"] = json.loads(response.text)
        except (TypeError, ValueError):
            capture["parsed_model_json"] = None
        journal('raw-model.jsonl', capture)
        return response

    llm.generate = audited_generate
    client_module._request_json = audited_transport
    try:
        for row in rows:
            if len(posts) >= max_provider_calls:
                stop_reason = "provider_call_cap"
                break
            active["id"] = row["id"]
            request = inference_request(row)
            before = len(raw)
            recovered = []
            started = time.perf_counter()
            try:
                answer = service.ask(**request)
                failed = [i for i in range(before, len(raw)) if raw[i].get('success') is False]
                delay = (answer.provider_failure or {}).get('retry_after_seconds')
                if (http503_recovery is not None and answer.provider_failure and len(failed) == 1
                        and raw[failed[0]].get('http_status') == 503 and len(posts) < max_provider_calls
                        and type(delay) in (int, float) and math.isfinite(delay) and 0 < delay <= 300):
                    recovered = failed
                    started_metadata.setdefault('http503_recoveries', []).append({
                        'id': row['id'], 'failed_capture_indices': failed,
                        'wait_seconds': math.ceil(delay), 'started_at': datetime.now(timezone.utc).isoformat()})
                    write_json(output / 'run-started.json', started_metadata)
                    # Evaluation-only, explicitly authorized, at most once per
                    # case. Normal client quota/circuit admission still applies.
                    for _ in range(math.ceil(delay)):
                        time.sleep(1)
                    answer = service.ask(**request)
                prediction = {"id": row["id"], "request": request,
                    "internal_response": answer.to_dict(), "public_response": answer.to_public_dict(),
                    "retrieved_evidence": [asdict(item) for item in service.last_retrieval],
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                    "provider_failure": answer.provider_failure,
                    "document_scope_audit": getattr(service._request_local, "document_scope_audit", None),
                    "raw_capture_indices": list(range(before, len(raw))),
                    "official_evaluation_eligible": False, "review_status": "review_required"}
                if recovered:
                    prediction['recovered_http503_capture_indices'] = recovered
                    prediction['recovered_http503_wait_seconds'] = math.ceil(delay)
                predictions.append(prediction)
                journal('predictions.jsonl', prediction)
                # An unrecovered provider failure cannot count as a correct
                # negative or trigger unbounded retries/key rotation.
                if answer.provider_failure or any(not raw[i]["success"] for i in range(before, len(raw)) if i not in recovered):
                    stop_reason = "provider_failure"
                    break
            except Exception as error:
                predictions.append({"id": row["id"], "request": request,
                                    "error_type": type(error).__name__, "official_evaluation_eligible": False,
                                    "recovered_http503_capture_indices": recovered,
                                    "raw_capture_indices": list(range(before, len(raw)))})
                journal('predictions.jsonl', predictions[-1])
                stop_reason = "pipeline_failure"
                break
    finally:
        llm.generate = original_generate
        client_module._request_json = previous_transport
    successful = [capture for capture in raw if capture.get("success") and capture.get("cached") is False]
    report = {**(run_metadata or {}), "status": "PROVISIONAL_NATIVE_RUN", "generation_kind": "native", "gold_seeded": False,
        "planned_records": len(rows), "pipeline_predictions": len(predictions),
        "provider_posts": len(posts), "real_model_outputs_successful": len(successful),
        "real_json_predictions_successful": sum(isinstance(capture.get("parsed_model_json"), dict) for capture in successful),
        "published_answers": sum(pred.get("public_response", {}).get("abstained") is False for pred in predictions),
        "local_pipeline_outcomes_without_model": sum(not pred.get("raw_capture_indices") for pred in predictions),
        "official_predictions": 0, "missing_independent_review": True,
        "stop_reason": stop_reason, "request_boundary": "question-language-declared-scope-history-only-v1",
        "selected_ids": [row["id"] for row in rows], "completed_ids": [pred["id"] for pred in predictions],
        "provider_call_cap": max_provider_calls,
        "document_scope_policy": (service.document_scope_reader.policy_identity()
                                  if service.document_scope_reader is not None else None),
        **({'egress_requests':egress_requests, 'http_body_policy':'exact-request-bodies-v1'}
            if egress_requests is not None else {}),
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                      for name in ("raw-model.jsonl", "predictions.jsonl", "provider-posts.jsonl")}}
    if http503_recovery is not None:
        report.update(http503_recovery_policy='http503-once-after-provider-cooldown-v1',
            http503_recovery_authorization=http503_recovery,
            http503_recoveries_attempted=sum(bool(p.get('recovered_http503_capture_indices')) for p in predictions),
            http503_recoveries_successful=sum(bool(p.get('recovered_http503_capture_indices'))
                and not p.get('provider_failure') and 'error_type' not in p for p in predictions))
    write_json(output / "run.json", report)
    return report


def prepare_egress(service, rows: list[dict], llm, output: Path, maximum: int) -> dict:
    if type(maximum) is not int or maximum < 1:
        raise ValueError("max_provider_calls must be positive")
    if output.exists() and any(output.iterdir()):
        raise ValueError("egress packet exists; use a new revision")
    prompts = []
    active = {"id": None, "request": None}
    original = llm.generate_json
    def capture(prompt, schema=None, **kwargs):
        prompts.append({"id": active["id"], "request": active["request"], "prompt": prompt,
                        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "answer_schema": schema,
                        "stage": "initial", **({'generation_arguments':kwargs} if kwargs else {})})
        raise LLMError("egress preflight only; no model inference")
    llm.generate_json = capture
    try:
        for row in rows:
            active.update(id=row["id"], request=inference_request(row))
            before = len(prompts)
            service.ask(**active["request"])
            if len(prompts) > before:
                try:
                    followup = service.prepare_document_scope_prompt()
                except DocumentScopeUnavailable:
                    continue
                prompt = followup.pop("prompt")
                prompts.append({"id": active["id"], "request": active["request"],
                    "stage": "complete_document_scope", "conditional": "initial_model_requests_document_absence",
                    "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), **followup})
    finally:
        llm.generate_json = original
    # A row that can request complete-document review must carry both its
    # initial prompt and the exact conditional follow-up. Reserving initial
    # calls first can leave selected rows without an authorized follow-up,
    # which makes a legitimate absence response fail closed mid-run. Budget
    # whole request paths, counting PDF token measurement and generation.
    selected_prompts = set()
    request_plans = {}
    planned_calls = 0
    for case in prompts:
        plan = _http_plan(llm, case)
        call_count = len(plan) if plan is not None else 1
        request_plans[id(case)] = plan
        case["planned_http_call_count"] = call_count
    initial_by_id = {case["id"]: case for case in prompts if case.get("stage") == "initial"}
    followup_by_id = {case["id"]: case for case in prompts
                      if case.get("stage") == "complete_document_scope"}
    if len(initial_by_id) != sum(case.get("stage") == "initial" for case in prompts):
        raise ValueError("duplicate benchmark question IDs in egress selection")
    for case in prompts:
        if case.get("stage") != "initial":
            continue
        path = [case]
        followup = followup_by_id.get(case["id"])
        if followup is not None:
            path.append(followup)
        call_count = sum(item["planned_http_call_count"] for item in path)
        if planned_calls + call_count > maximum:
            continue
        selected_prompts.update(id(item) for item in path)
        planned_calls += call_count
    bounded_prompts = [case for case in prompts if id(case) in selected_prompts]
    if prompts and not bounded_prompts:
        raise ValueError("no complete request path fits the provider call cap")
    for case in bounded_prompts:
        plan = request_plans[id(case)]
        if plan is not None:
            case["http_requests"] = plan
        case.pop("planned_http_call_count", None)
    prompts = bounded_prompts
    pdf_sources = {}
    for case in prompts:
        documents = case.get('generation_arguments', {}).get('pdf_documents', [])
        for doc in documents:
            pdf_sources[doc['sha256']] = {'data':doc['data']}
        if documents:
            case['generation_arguments']['pdf_documents'] = [{'sha256':doc['sha256']} for doc in documents]
    if planned_calls > maximum:
        raise AssertionError('bounded egress requests exceeded the provider call cap')
    output.mkdir(parents=True, exist_ok=True)
    packet = {"status": "EGRESS_PERMISSION_PENDING", "provider_posts": 0, "model_predictions": 0,
        "not_an_annotation_approval": True, "destination": llm.endpoint,
        "model": llm.model, "max_provider_calls": maximum, "planned_provider_calls": planned_calls,
        "cases": prompts,
        **({'pdf_sources':pdf_sources} if pdf_sources else {}),
        "document_scope_policy": (service.document_scope_reader.policy_identity()
                                  if service.document_scope_reader is not None else None)}
    write_json(output / "egress.json", packet)
    return packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/grounding_reviewed.jsonl"))
    parser.add_argument("--index", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--config", type=Path, default=Path("configs/free_llm.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0,
                        help="Resume a bounded batch by position without changing benchmark rows")
    parser.add_argument("--max-provider-calls", type=int, default=10)
    parser.add_argument("--prepare-egress", action="store_true")
    parser.add_argument("--egress-packet", type=Path)
    parser.add_argument("--source-store", type=Path,
                        help="Registered source store for optional complete-text follow-up")
    parser.add_argument("--source-root", type=Path, action="append",
                        help="Operator-authorized physical source root; repeat for multiple roots")
    parser.add_argument("--calibration-artifact", type=Path)
    parser.add_argument("--calibration-sha256")
    parser.add_argument('--http503-recovery-authorization', type=Path,
                        help='Explicit owner grant for one delayed HTTP503 recovery per case, within the same packet budget')
    args = parser.parse_args()
    if args.limit < 1 or args.max_provider_calls < 1 or args.offset < 0:
        raise SystemExit("positive limits required")
    if args.source_root and not args.source_store:
        raise SystemExit("source roots require an explicit source store")
    if not verify_index_files(args.index):
        raise SystemExit("index failed checksum verification; no inference sent")
    config = _read_config(args.config)
    if (config.get("llm", {}).get("provider") != "gemini"
            or config["llm"].get("model") != "gemini-3.5-flash-lite"
            or config["llm"].get("max_retries") != 0):
        raise SystemExit("collector requires the existing owner-approved Free profile")
    calibrator, calibration_hash = pinned_calibrator(args.calibration_artifact, args.calibration_sha256, args.benchmark)
    from scripts.operations.local import configure_local
    root = Path.cwd()
    os.environ["CAMPUSAI_LLM_CONFIG"] = str(args.config.resolve())
    configure_local(root)
    llm = create_llm(args.config)
    rag = config.get("rag", {})
    service = CampusAIQueryService(HybridRetriever(args.index, dense_device="cpu"),
        GroundedAnswerGenerator(llm, max_context_chars=rag.get("max_context_chars", 12000),
            balanced_context=rag.get("balanced_context", False), source_citations=rag.get("source_citations", False),
            calibrator=calibrator),
        context_candidates=rag.get("context_candidates"), default_mode="auto",
        document_scope_reader=(RegisteredDocumentScopeReader(args.source_store, source_roots=args.source_root,
            allow_pdf_scope=getattr(llm, 'allow_pdf_scope', False))
                               if args.source_store else None))
    before = llm.quota_governor.snapshot() if llm.quota_governor else None
    metadata = dict(benchmark_path=str(args.benchmark), benchmark_sha256=hashlib.sha256(args.benchmark.read_bytes()).hexdigest(),
        source_identity=source_identity(root), model=llm.model,
        config_path=str(args.config), config_sha256=hashlib.sha256(args.config.read_bytes()).hexdigest(),
        index_path=str(args.index), index_manifest_sha256=hashlib.sha256((args.index / 'manifest.json').read_bytes()).hexdigest(),
        quota_before=before, benchmark_population=len(load_rows(args.benchmark)), selection_offset=args.offset,
        calibration_artifact_sha256=calibration_hash, calibration_artifact_version=calibrator.version if calibrator else None,
        calibration_artifact_path=str(args.calibration_artifact) if args.calibration_artifact else None)
    try:
        rows = load_rows(args.benchmark)[args.offset:args.offset + args.limit]
        if args.prepare_egress:
            report = prepare_egress(service, rows, llm, args.output, args.max_provider_calls)
        else:
            if not args.egress_packet:
                raise ValueError("explicit reviewed egress packet required before native collection")
            packet = json.loads(args.egress_packet.read_text(encoding="utf-8"))
            metadata.update(egress_packet_path=str(args.egress_packet),
                            egress_packet_sha256=hashlib.sha256(args.egress_packet.read_bytes()).hexdigest())
            recovery = None
            if args.http503_recovery_authorization:
                authorization_path = args.http503_recovery_authorization.resolve()
                if not authorization_path.is_relative_to(root.resolve()):
                    raise ValueError('recovery authority must be physically bound inside this candidate')
                recovery = {'path': str(args.http503_recovery_authorization),
                    'sha256': hashlib.sha256(authorization_path.read_bytes()).hexdigest(),
                    'decision': json.loads(authorization_path.read_text(encoding='utf-8'))}
            if packet.get("destination") != llm.endpoint or packet.get("model") != llm.model or packet.get("max_provider_calls") != args.max_provider_calls:
                raise ValueError("egress destination/model/budget mismatch")
            policy = service.document_scope_reader.policy_identity() if service.document_scope_reader else None
            if packet.get("document_scope_policy") != policy:
                raise ValueError("egress source scope policy mismatch")
            expected_prompts = {}
            expected_requests = {} if any('http_requests' in c for c in packet['cases']) else None
            for case in packet["cases"]:
                if hashlib.sha256(case["prompt"].encode()).hexdigest() != case["prompt_sha256"]:
                    raise ValueError("egress prompt checksum mismatch")
                expected_prompts.setdefault(case["id"], []).append(case["prompt_sha256"])
                if expected_requests is not None:
                    if _http_plan(llm, case, packet.get('pdf_sources', {})) != case.get('http_requests'):
                        raise ValueError('egress HTTP request checksum or endpoint mismatch')
                    expected_requests.setdefault(case['id'], []).extend(case['http_requests'])
            report = collect(service, rows, llm, max_provider_calls=args.max_provider_calls,
                             output=args.output, egress_prompts=expected_prompts, run_metadata=metadata,
                             http503_recovery=recovery, egress_requests=expected_requests)
        if source_identity(root) != metadata['source_identity']:
            raise ValueError('source changed during collection; preserve interrupted evidence without relabelling its source')
        report.update(metadata, quota_after=llm.quota_governor.snapshot() if llm.quota_governor else None)
        write_json(args.output / ("egress.json" if args.prepare_egress else "run.json"), report)
        if args.prepare_egress:
            print(json.dumps({"status": report["status"], "prepared_prompts": len(report["cases"]),
                              "provider_posts": 0, "destination": report["destination"]}, indent=2))
        else:
            print(json.dumps({key: report[key] for key in ("status", "pipeline_predictions", "provider_posts",
                "real_model_outputs_successful", "real_json_predictions_successful", "official_predictions", "stop_reason")}, indent=2))
    finally:
        service.close()


if __name__ == "__main__":
    main()
