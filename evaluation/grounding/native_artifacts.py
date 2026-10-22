"""Read immutable native captures and reconcile their measured counters."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from evaluation.grounding.repair_benchmark import load_rows


NATIVE_FILES = {"raw-model.jsonl", "predictions.jsonl", "provider-posts.jsonl"}
RUN_IDENTITY_FIELDS = ("benchmark_sha256", "source_identity", "model", "config_sha256",
                       "index_manifest_sha256", "calibration_artifact_sha256", "document_scope_policy")
BASE_RUN_IDENTITY_FIELDS = tuple(field for field in RUN_IDENTITY_FIELDS
                                 if field != "calibration_artifact_sha256")
CALIBRATION_PROTOCOL = "dev-fit-then-pinned-evaluation-v1"


def _validate_pdf_requests(directory, run, raw, posts):
    try:
        _validate_pdf_request_bindings(directory, run, raw, posts)
    except (KeyError, TypeError, AttributeError, IndexError, OSError) as error:
        raise ValueError('native PDF request bindings malformed') from error


def _validate_pdf_request_bindings(directory, run, raw, posts):
    captures = [c for c in raw if c.get('generation_arguments', {}).get('pdf_documents') is not None]
    if not captures:
        return
    from campusai.llm.pdf_scope import body_hash, pdf_parts
    packet_path = Path(run.get('egress_packet_path', '')).resolve()
    if (not any(packet_path.is_relative_to(root.resolve()) for root in (Path.cwd(), directory.parent))
            or not packet_path.is_file()
            or hashlib.sha256(packet_path.read_bytes()).hexdigest() != run.get('egress_packet_sha256')):
        raise ValueError('native PDF egress packet missing or changed')
    packet = json.loads(packet_path.read_text(encoding='utf-8'))
    permitted = {}
    for case in packet['cases']:
        permitted.setdefault(case['id'], []).extend(case.get('http_requests', []))
    if (run.get('http_body_policy') != 'exact-request-bodies-v1'
            or run.get('egress_requests') != permitted
            or packet.get('max_provider_calls') != run.get('provider_call_cap')):
        raise ValueError('native PDF HTTP permission bindings invalid')
    for post in posts:
        if {'endpoint':post.get('endpoint'), 'body_sha256':post.get('request_body_sha256')} not in permitted.get(post['id'], []):
            raise ValueError('native PDF transport is outside approved HTTP bodies')
    used_posts = set()
    for capture in captures:
        docs = capture['generation_arguments']['pdf_documents']
        pdf_parts(docs)  # Actual hash/format/pages/byte caps, not claimed metadata.
        binaries = {doc['sha256']:doc['data'] for doc in docs}
        if any(packet.get('pdf_sources', {}).get(sha, {}).get('data') != data for sha,data in binaries.items()):
            raise ValueError('native PDF source differs from approved binary')
        reference = capture.get('pdf_request')
        if not isinstance(reference, dict):
            raise ValueError('native PDF request identity missing')
        body = json.loads(json.dumps(reference['body_reference']))
        seen = []
        for content in body['contents']:
            for part in content['parts']:
                if 'inlineData' in part:
                    item = part['inlineData']
                    if set(item) != {'mimeType','sha256'} or item['mimeType'] != 'application/pdf':
                        raise ValueError('native PDF source reference invalid')
                    sha = item['sha256']; seen.append(sha)
                    part['inlineData'] = {'mimeType':'application/pdf','data':binaries[sha]}
        endpoint = reference['endpoint']
        model = reference['model']
        digest = body_hash(body)
        if (len(seen) != len(binaries) or set(seen) != set(binaries)
                or model != run.get('model') or model != packet.get('model')
                or endpoint != f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
                or digest != reference['body_sha256']
                or not any(case['id']==capture['id'] and case['prompt_sha256']==capture['prompt_sha256']
                    and {'endpoint':endpoint,'body_sha256':digest} in case.get('http_requests', []) for case in packet['cases'])):
            raise ValueError('native PDF prompt/body/source binding invalid')
        count_endpoint = endpoint.removesuffix(':generateContent')+':countTokens'
        count_digest = body_hash({'generateContentRequest':{'model':'models/'+model,**body}})
        measurements = capture.get('input_measurements', [])
        if len(measurements) > 1:
            raise ValueError('native PDF measurement unexpectedly repeated')
        if measurements:
            item = measurements[0]; tokens = item.get('response', {}).get('totalTokens')
            if (item.get('endpoint') != count_endpoint or item.get('body_sha256') != count_digest
                    or type(tokens) is not int or not 0 < tokens <= 1_000_000_000):
                raise ValueError('native PDF token measurement binding invalid')
        if capture['success']:
            if capture.get('cached') is not False or len(measurements) != 1:
                raise ValueError('native PDF output has no fresh measured request')
            matched = []
            for target,sha in [(count_endpoint,count_digest),(endpoint,digest)]:
                found = next((i for i,p in enumerate(posts) if i not in used_posts and p['id']==capture['id']
                    and p.get('endpoint')==target and p.get('request_body_sha256')==sha), None)
                if found is None:
                    raise ValueError('native PDF response has no matching HTTP attempt')
                used_posts.add(found); matched.append(found)
            if matched[0] >= matched[1]:
                raise ValueError('native PDF generation preceded token measurement')


def native_calibration_matches(run: dict, predictions: list[dict], benchmark: dict[str, dict],
                               expected_sha256: str | None, protocol: str | None) -> bool:
    """Only uncalibrated training captures may precede the pinned calibrator.

    Split membership comes from physical benchmark annotations at validation,
    never a report-supplied split or a collector's claim about its role.
    """
    actual = run.get("calibration_artifact_sha256")
    if actual == expected_sha256:
        return True
    if (protocol != CALIBRATION_PROTOCOL or not expected_sha256 or actual is not None
            or run.get("calibration_artifact_version") is not None
            or run.get("calibration_artifact_path") is not None):
        return False
    return bool(predictions) and all(
        benchmark.get(prediction["id"], {}).get("split") == "dev"
        for prediction in predictions)


def load_native_run(directory: Path) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Checksums alone do not prove counts, capture ownership or real generation."""
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    if run.get("generation_kind") != "native" or run.get("gold_seeded") is not False:
        raise ValueError("scoring requires a native collector run, never gold fixtures")
    recovery = run.get('http503_recovery_policy')
    if recovery is not None:
        grant = (run.get('http503_recovery_authorization') or {}).get('decision', {})
        budget = grant.get('packet_budgets', {}).get(run.get('egress_packet_sha256'))
        if (recovery != 'http503-once-after-provider-cooldown-v1'
                or grant.get('status') != 'authorized' or grant.get('recover_http503_once') is not True
                or not grant.get('owner_id') or not grant.get('decision_reference')
                or type(budget) is not int or type(run.get('provider_call_cap')) is not int
                or run['provider_call_cap'] > budget):
            raise ValueError('native HTTP503 recovery authority invalid')
    if not isinstance(run.get("artifacts"), dict) or set(run["artifacts"]) != NATIVE_FILES:
        raise ValueError("native capture requires all three raw artifacts")
    for name, expected in run["artifacts"].items():
        path = (directory / name).resolve()
        if (not path.is_relative_to(directory.resolve()) or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError("native raw artifact checksum mismatch")
    predictions = load_rows(directory / "predictions.jsonl")
    raw = load_rows(directory / "raw-model.jsonl")
    posts = load_rows(directory / "provider-posts.jsonl")
    ids = [item["id"] for item in predictions]
    if len(ids) != len(set(ids)) or run.get("completed_ids") != ids:
        raise ValueError("native prediction/case population mismatch")
    used = set()
    for prediction in predictions:
        indices = prediction.get("raw_capture_indices", [])
        if not isinstance(indices, list):
            raise ValueError("native capture indices must be a list")
        for index in indices:
            if type(index) is not int or not 0 <= index < len(raw) or index in used:
                raise ValueError("native capture index invalid or reused")
            used.add(index)
            capture = raw[index]
            if (capture.get("id") != prediction["id"] or not isinstance(capture.get("prompt"), str)
                    or hashlib.sha256(capture["prompt"].encode()).hexdigest() != capture.get("prompt_sha256")
                    or type(capture.get("success")) is not bool):
                raise ValueError("native prompt/case binding mismatch")
            if capture["success"]:
                try:
                    parsed = json.loads(capture["raw_model_text"])
                except (TypeError, ValueError):
                    parsed = None
                if parsed != capture.get("parsed_model_json") or type(capture.get("cached")) is not bool:
                    raise ValueError("native parsed/raw model output mismatch")
        recovered = prediction.get('recovered_http503_capture_indices', [])
        if (not isinstance(recovered, list) or len(recovered) > 1
                or any(type(i) is not int or i not in indices for i in recovered)
                or (recovered and recovery is None)
                or any(raw[i].get('success') is not False or raw[i].get('http_status') != 503 for i in recovered)):
            raise ValueError('native recovered HTTP503 capture invalid')
        if recovered:
            delay = prediction.get('recovered_http503_wait_seconds')
            index = recovered[0]
            following = [i for i in indices if i > index]
            if type(delay) is not int or not 1 <= delay <= 300 or not following:
                raise ValueError('native HTTP503 cooldown evidence missing')
            ended = datetime.fromisoformat(raw[index]['completed_at'])
            resumed = datetime.fromisoformat(raw[min(following)]['started_at'])
            if ended.tzinfo is None or resumed.tzinfo is None or (resumed - ended).total_seconds() < delay - .05:
                raise ValueError('native HTTP503 provider cooldown not respected')
        if not prediction.get('provider_failure') and 'error_type' not in prediction:
            if any(raw[i].get('success') is False for i in indices if i not in recovered):
                raise ValueError('native unrecovered provider failure concealed')
    if used != set(range(len(raw))):
        raise ValueError("native orphan raw capture")
    _validate_pdf_requests(directory, run, raw, posts)
    if any(post.get("id") not in set(ids) for post in posts):
        raise ValueError("native transport/case population mismatch")
    successful = [item for item in raw if item["success"] and item["cached"] is False]
    for identifier in ids:
        if sum(item["id"] == identifier for item in successful) > sum(item["id"] == identifier for item in posts):
            raise ValueError("native successful output has no matching transport attempt")
    counts = {"pipeline_predictions": len(predictions), "provider_posts": len(posts),
        "real_model_outputs_successful": len(successful),
        "real_json_predictions_successful": sum(isinstance(item.get("parsed_model_json"), dict) for item in successful),
        "published_answers": sum(item.get("public_response", {}).get("abstained") is False for item in predictions),
        "local_pipeline_outcomes_without_model": sum(not item.get("raw_capture_indices") for item in predictions)}
    if any(type(run.get(key)) is not int or run[key] != value for key, value in counts.items()):
        raise ValueError("native measured counter mismatch")
    if recovery is not None:
        attempted = sum(bool(p.get('recovered_http503_capture_indices')) for p in predictions)
        completed = sum(bool(p.get('recovered_http503_capture_indices')) and not p.get('provider_failure')
                        and 'error_type' not in p for p in predictions)
        if (type(run.get('http503_recoveries_attempted')) is not int
                or run['http503_recoveries_attempted'] != attempted
                or type(run.get('http503_recoveries_successful')) is not int
                or run['http503_recoveries_successful'] != completed):
            raise ValueError('native HTTP503 recovery counters invalid')
    if type(run.get("official_predictions")) is not int or run["official_predictions"] != 0:
        raise ValueError("native collection cannot manufacture official approval counts")
    if (type(run.get("provider_call_cap")) is not int or run["provider_call_cap"] < 1
            or len(posts) > run["provider_call_cap"] or len(successful) > len(posts)):
        raise ValueError("native provider call cap or successful-output count invalid")
    return run, predictions, raw, posts
