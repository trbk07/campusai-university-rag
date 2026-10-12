"""Prepare/collect one current-product dev pilot, with no reranker or retries.

Preparation uses public, previously reviewed dev/source fixtures and performs no
external request. Collection requires the exact prepared packet digest; consent
must come from the user, not from a repository file. This is not heldout quality
or performance acceptance.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import time
from unittest.mock import patch
from urllib.request import Request, urlopen
from wsgiref.simple_server import WSGIRequestHandler, make_server

from campusai.llm.client import LLMResponseError
from campusai.llm.factory import _read_config
from campusai.rag.context import benchmark_request
from campusai.web import make_wsgi_app
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from evaluation.reranker.collect_paired_answers import recording_generate
from evaluation.reranker.measure_reranker_http import _NoAnswerCache
from scripts.operations.serve import build_application

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('evaluation/results/phase7-completion-20261004')
DEV = Path('data/benchmark/phase7_review_cycles/phase7-successor-20261005-r19b/human_retrieval_dev.jsonl')
RUBRIC = BASE / 'p7-06-dev-source-rubric-20261007-v2.json'
CONFIG = Path('configs/product_llm.yaml')
QIDS = tuple(f'human-candidate-{n:04d}' for n in (156, 159, 165, 178, 63, 64, 1, 45))
PROFILE = {
    'RERANKER_ENABLED': 'false', 'CAMPUSAI_DEVICE': 'cuda',
    'CAMPUSAI_INDEX_DIR': '.tmp/phase7-curated-source-20261005-v2/index',
    'CAMPUSAI_RETRIEVAL_CALIBRATION': '.release/reranker/studies/phase7-successor-r19b-phase6-dev-qualification-v1/hybrid_retrieval_calibration.json',
    'CAMPUSAI_LLM_CONFIG': CONFIG.as_posix(), 'CAMPUSAI_INGESTION_WORKERS': '1',
    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
    'OMP_NUM_THREADS': '8', 'MKL_NUM_THREADS': '8',
}


@contextmanager
def profile_environment():
    with patch.dict(os.environ, PROFILE):
        yield


def disable_answer_cache(application):
    application.query_service.cache.close()
    application.query_service.cache = _NoAnswerCache()
    application.query_service.retriever.query_cache_size = 0


def wsgi_request(web, payload):
    data = json.dumps(payload, ensure_ascii=False).encode('utf8')
    response = {}
    body = web({'PATH_INFO': '/api/query', 'REQUEST_METHOD': 'POST', 'CONTENT_LENGTH': str(len(data)),
                'wsgi.input': io.BytesIO(data)}, lambda status, headers: response.update(status=status))
    response['body'] = json.loads(b''.join(body))
    return response


def validate_packet(packet):
    if (packet['profile'] != PROFILE or packet['endpoint_host'] != 'generativelanguage.googleapis.com'
            or packet['release_eligible'] or packet['test_or_holdout_read']
            or packet['max_provider_calls'] > 6 or packet['max_retries'] != 0
            or packet['minimum_call_start_interval_seconds'] != 30):
        raise ValueError('product pilot protocol changed')
    case_limit = packet.get('case_limit', 8)
    if case_limit not in (1, 8) or tuple(case['qid'] for case in packet['cases']) != QIDS[:case_limit]:
        raise ValueError('pilot must use the declared dev prefix, either one availability probe or eight cases')
    for case in packet['cases']:
        if case['split'] != 'dev' or case['arm'] != 'current_product_reranker_disabled':
            raise ValueError('not the current-product dev arm')
        prompt = case['prompt']
        if bool(prompt) != case['planned_provider_call']:
            raise ValueError('provider plan differs from prepared prompt')
        if prompt and hashlib.sha256(prompt.encode('utf8')).hexdigest() != case['prompt_sha256']:
            raise ValueError('prompt digest mismatch')
    if sum(case['planned_provider_call'] for case in packet['cases']) != packet['max_provider_calls']:
        raise ValueError('provider-call denominator mismatch')
    if packet['llm_config'] != _read_config(CONFIG)['llm']:
        raise ValueError('provider settings changed')
    if packet['llm_config']['model'] != 'gemini-3.8-flash' or packet['llm_config']['max_retries'] != 0:
        raise ValueError('provider identity or retries changed')


def prepare(output, case_limit=8):
    if output.exists():
        raise FileExistsError(output)
    config = _read_config(CONFIG)['llm']
    rows = {row['qid']: row for row in rows_at(DEV)}
    rubric = read_json(RUBRIC)
    assert all(rows[qid]['split'] == 'dev' and qid in rubric['claims'] for qid in QIDS)
    before = source_identity(ROOT)

    class Preflight:
        model = config['model']
        generation_config = deepcopy(config['generation_config'])

        def __init__(self):
            self.prompts = []

        def generate_json(self, prompt, **options):
            self.prompts.append({'prompt': prompt, 'schema': deepcopy(options['schema'])})
            raise LLMResponseError('offline preflight; no provider response')

    preflight = Preflight()
    cases = []
    with profile_environment(), patch('scripts.operations.serve.create_llm', return_value=preflight):
        import torch
        torch.set_num_threads(8)
        application = build_application()
        disable_answer_cache(application)
        docs = read_json(Path(PROFILE['CAMPUSAI_INDEX_DIR']) / 'manifest.json')['documents']
        web = make_wsgi_app(application)
        try:
            assert not application.query_service.retriever.phase7_enabled
            for qid in QIDS[:case_limit]:
                preflight.prompts.clear()
                row = rows[qid]
                request = benchmark_request(row, docs)
                response = wsgi_request(web, request)
                if response['status'] != '200 OK' or not response['body']['ok'] or len(preflight.prompts) > 1:
                    raise ValueError(f"application preflight failed: {qid}, status={response['status']}, "
                                     f"prompts={len(preflight.prompts)}, error={response['body'].get('error_code')}")
                observed = preflight.prompts[0] if preflight.prompts else {}
                if not row['answerable'] and observed:
                    raise ValueError('negative unexpectedly sends evidence to provider')
                prompt = observed.get('prompt')
                cases.append({'qid': qid, 'split': 'dev', 'arm': 'current_product_reranker_disabled',
                              'request': request, 'answerable': row['answerable'], 'tags': row['tags'],
                              'gold_claims': rubric['claims'][qid],
                              'evidence': [item.to_dict() for item in application.query_service.last_retrieval],
                              'planned_provider_call': bool(prompt), 'prompt': prompt,
                              'schema': observed.get('schema'),
                              'prompt_sha256': hashlib.sha256(prompt.encode('utf8')).hexdigest() if prompt else None,
                              'preflight_answer': response['body']['answer']})
        finally:
            application.close()
    if source_identity(ROOT) != before:
        raise ValueError('source changed during preflight')
    packet = {'schema_version': 1, 'status': 'PREPARED_AWAITING_EXACT_PACKET_USER_AUTHORIZATION',
              'endpoint_host': 'generativelanguage.googleapis.com', 'profile': PROFILE, 'llm_config': config,
              'case_limit': case_limit,
              'max_provider_calls': sum(case['planned_provider_call'] for case in cases), 'max_retries': 0,
              'minimum_call_start_interval_seconds': 30, 'cases': cases,
              'prompt_chars': sum(len(case['prompt'] or '') for case in cases),
              'prepared_source_identity': before, 'prepared_at': datetime.now(timezone.utc).isoformat(),
              'bindings': {str(path): sha256(path) for path in (DEV, RUBRIC, CONFIG,
                  Path(PROFILE['CAMPUSAI_INDEX_DIR']) / 'manifest.json', Path(PROFILE['CAMPUSAI_RETRIEVAL_CALIBRATION']))},
              'output_path': str(BASE / (output.stem.replace('egress-packet', 'live') +
                                        ('' if 'egress-packet' in output.stem else '-live') + '.json')),
              'release_eligible': False, 'test_or_holdout_read': False, 'new_provider_calls': 0,
              'limitations': [f'{case_limit} dev question(s) only; not primary quality or p95 acceptance.',
                              'Rubric is owner-authorized AI source review, not independent human review.',
                              'Model availability does not prove this credential/network will succeed.'],
              'model_reference': 'https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash'}
    validate_packet(packet)
    write_json(output, packet)
    print(json.dumps({'path': str(output), 'sha256': sha256(output), 'provider_calls_sent': 0,
                      'maximum_calls': packet['max_provider_calls'], 'prompt_chars': packet['prompt_chars']}))


def collect(packet_path, authorized_digest):
    if sha256(packet_path) != authorized_digest:
        raise ValueError('exact packet authorization mismatch')
    packet = read_json(packet_path)
    validate_packet(packet)
    if source_identity(ROOT) != packet['prepared_source_identity']:
        raise ValueError('prepared source changed; prepare/review a new packet')
    if any(sha256(Path(path)) != digest for path, digest in packet['bindings'].items()):
        raise ValueError('prepared inputs changed')
    output = Path(packet['output_path'])
    with output.open('x', encoding='utf8') as stream:
        json.dump({'status': 'STARTED_NO_RESTART_ALLOWED', 'packet_sha256': authorized_digest}, stream)
    record = {'schema_version': 1, 'status': 'IN_PROGRESS', 'packet_sha256': authorized_digest,
              'source_identity': packet['prepared_source_identity'], 'observations': [],
              'release_eligible': False, 'answer_cache_enabled': False, 'llm_cache_enabled': False,
              'max_retries': 0, 'test_or_holdout_read': False}
    traces, calls = [], []
    with profile_environment():
        import torch
        torch.set_num_threads(8)
        application = build_application()
        disable_answer_cache(application)
        client = application.query_service.answer_generator.llm
        client.cache.close()
        client.cache = None
        client.generate = recording_generate(client.generate, calls)
        original = client.generate_json
        expected = None
        last_provider_start = None

        def guarded(prompt, **options):
            nonlocal last_provider_start
            if (expected is None or not expected['planned_provider_call'] or calls
                    or prompt != expected['prompt'] or options.get('schema') != expected['schema']):
                raise LLMResponseError('unapproved prompt or duplicate provider attempt')
            if last_provider_start is not None and time.monotonic() - last_provider_start < 30:
                raise LLMResponseError('provider call spacing violated')
            last_provider_start = time.monotonic()
            return original(prompt, **options)

        client.generate_json = guarded
        def capture_trace(trace):
            # Retrieval is request-local and therefore must be captured on the
            # WSGI worker thread, not read from the HTTP client's thread.
            trace['evidence'] = [item.to_dict() for item in application.query_service.last_retrieval]
            traces.append(trace)

        class Quiet(WSGIRequestHandler):
            def log_message(self, *_args):
                pass
        try:
            with make_server('127.0.0.1', 0, make_wsgi_app(application, telemetry_hook=capture_trace),
                             handler_class=Quiet) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    for case in packet['cases']:
                        expected = case
                        calls.clear()
                        if case['planned_provider_call'] and last_provider_start is not None:
                            time.sleep(max(0, 30.05 - (time.monotonic() - last_provider_start)))
                        record['current_attempt'] = case['qid']
                        write_json(output, record)
                        started = time.perf_counter()
                        request = Request(f'http://127.0.0.1:{server.server_port}/api/query',
                            data=json.dumps(case['request'], ensure_ascii=False).encode('utf8'),
                            headers={'Content-Type': 'application/json'})
                        with urlopen(request, timeout=75) as response:
                            answer = json.loads(response.read())
                        record['observations'].append({'qid': case['qid'], 'answer': answer,
                            'latency_ms': (time.perf_counter() - started) * 1000,
                            'evidence': deepcopy(traces[-1]['evidence']) if traces else [],
                            'llm_calls': deepcopy(calls), 'trace': traces[-1] if traces else None,
                            'review_status': 'pending'})
                        failed = (len(calls) != int(case['planned_provider_call']) or not answer.get('ok')
                                  or any(call['provider_status'] != 'completed' or call.get('cached')
                                         for call in calls))
                        record['status'] = 'PROVIDER_FAILURE_STOPPED' if failed else 'PENDING_SOURCE_REVIEW'
                        write_json(output, record)
                        if failed:
                            break
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
        finally:
            application.close()
    record.pop('current_attempt', None)
    record['source_identity_after'] = source_identity(ROOT)
    if record['source_identity_after'] != packet['prepared_source_identity']:
        record['status'] = 'SOURCE_CHANGED_NOT_ACCEPTABLE'
    write_json(output, record)
    print(json.dumps({'status': record['status'], 'observations': len(record['observations']),
                      'provider_calls': sum(len(o['llm_calls']) for o in record['observations'])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preparation = commands.add_parser('prepare')
    preparation.add_argument('--output', type=Path, required=True)
    preparation.add_argument('--case-limit', type=int, choices=(1, 8), default=8)
    run = commands.add_parser('collect')
    run.add_argument('--packet', type=Path, required=True)
    run.add_argument('--authorized-packet-sha256', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output, args.case_limit)
    else:
        collect(args.packet, args.authorized_packet_sha256)


if __name__ == '__main__':
    main()
