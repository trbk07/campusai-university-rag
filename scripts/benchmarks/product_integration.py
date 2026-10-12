"""Exact two-call product integration packet; offline preparation, no retries."""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import time
from unittest.mock import patch
import urllib.request

from evaluation.common.release_artifacts import read_json, sha256, source_identity, write_json
from scripts.benchmarks.product_quality_pilot import ROOT, CONFIG, BASE
from scripts.benchmarks.product_performance import ENDPOINT, available_output, read_json_config
from scripts.benchmarks.product_retry import Budget, load_retry503, validate_retry

TESTS = ['tests/integration/test_gemini.py', 'tests/integration/test_basic_rag_provider.py']


def run(output: Path, packet_path: Path | None = None, digest: str | None = None):
    available_output(output)
    packet = read_json(packet_path) if packet_path else None
    before = source_identity(ROOT)
    if packet and (sha256(packet_path) != digest or packet['source_identity'] != before
        or packet['endpoint'] != ENDPOINT or packet['max_provider_calls'] != 2
        or packet['minimum_provider_start_interval_seconds'] != 30
        or output.resolve() != Path(packet['output_path']).resolve()
        or any(sha256(Path(p)) != d for p, d in packet['bindings'].items())):
        raise ValueError('integration authorization/source/limits changed')
    if packet:
        validate_retry(packet)
    budget = Budget(packet_path, digest) if packet and packet['max_retries'] else None
    retry503 = load_retry503()
    report = {'status': 'STARTED_NO_RESTART', 'source_identity': before, 'observations': [],
        'offline': packet is None, 'external_provider_calls': 0, 'quality_or_performance_accepted': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.open('x', encoding='utf8').close()
    original = urllib.request.urlopen
    last_start = 0.0

    def transport(request, **options):
        nonlocal last_start
        body = json.loads(request.data)
        ordinal = len(report['observations'])
        if (ordinal >= 2 or request.full_url != ENDPOINT or request.get_method() != 'POST'
            or (packet and body != packet['provider_bodies'][ordinal])):
            raise RuntimeError('unapproved integration attempt')
        if packet:
            time.sleep(max(0, 30.05 - (time.time() - last_start)))
        last_start = time.time()
        observed = {'ordinal': ordinal + 1, 'provider_body': body, 'provider_start': last_start,
                    'status': 'attempted'}
        report['observations'].append(observed)
        write_json(output, report)
        started = time.perf_counter()
        try:
            if packet:
                attempts = observed['provider_attempts'] = []
                def one_attempt(req, **opts):
                    nonlocal last_start
                    if budget:
                        budget.before_attempt(str(ordinal), body, bool(attempts and len(attempts) > 1))
                    last_start = time.time()
                    report['external_provider_calls'] += 1
                    write_json(output, report)
                    with original(req, **opts) as response:
                        return io.BytesIO(response.read())
                response = (retry503(request, one_attempt, timeout=options['timeout'], attempts=attempts,
                    before_retry=lambda: budget.reserve_retry(str(ordinal)),
                    on_change=lambda: write_json(output, report)) if budget else one_attempt(request, **options))
                with response:
                    raw = response.read()
            else:
                source = 'Graduation requires 130 credits and completion of an internship.'
                text = 'OK' if ordinal == 0 else json.dumps({'answer': source,
                    'confidence': 'high', 'abstained': False,
                    'claims': [{'claim_id': 'credits', 'text': 'Graduation requires 130 credits.',
                                'citation_ids': ['phase4-live-c1']},
                               {'claim_id': 'internship', 'text': 'Graduation requires completion of an internship.',
                                'citation_ids': ['phase4-live-c1']}],
                    'citations': [{'chunk_id': 'phase4-live-c1', 'page': 1, 'quote': source}]})
                raw = json.dumps({'candidates': [{'content': {'parts': [{'text': text}]},
                    'finishReason': 'STOP'}]}).encode()
            observed.update(status='completed', response=json.loads(raw))
            return io.BytesIO(raw)
        except Exception as error:
            observed.update(status='failed', error_type=type(error).__name__, http_status=getattr(error, 'code', None))
            raise
        finally:
            observed['latency_ms'] = (time.perf_counter() - started) * 1000
            write_json(output, report)

    environment = {'RUN_LLM_INTEGRATION': '1'}
    if not packet:
        environment['GEMINI_API_KEY'] = 'offline-integration-capture-only'
    from campusai.llm.client import GeminiClient
    original_complete = GeminiClient.complete
    def audited_complete(client, *args, **kwargs):
        retries = client.max_retries
        try:
            if budget:
                client.max_retries = 0  # Audited common transport owns retries.
            return original_complete(client, *args, **kwargs)
        finally:
            client.max_retries = retries
    with patch.dict(os.environ, environment), patch('urllib.request.urlopen', transport), patch.object(GeminiClient, 'complete', audited_complete):
        import pytest
        result = pytest.main([*TESTS, '-q', '-x', '--junitxml=' + str(output.with_suffix('.xml'))])
    report['source_stable'] = source_identity(ROOT) == before
    valid = (result == 0 and len(report['observations']) == 2 and report['source_stable']
             and all(o['status'] == 'completed' for o in report['observations']))
    report['status'] = ('LIVE_TWO_INTEGRATIONS_PASS' if packet else 'OFFLINE_TWO_INTEGRATIONS_PASS_NOT_LIVE') if valid else 'FAILURE_STOPPED'
    if budget and not valid:
        budget.stop(report['status'])
    write_json(output, report)
    if not packet and valid:
        target = output.with_name(output.stem.replace('preflight', 'egress-packet') + '.json')
        available_output(target)
        bodies = [o['provider_body'] for o in report['observations']]
        prepared = {'status': 'PREPARED_NOT_AUTHORIZED', 'source_identity': before, 'endpoint': ENDPOINT,
            'provider_bodies': bodies, 'max_provider_calls': 2, 'max_retries': read_json_config()['max_retries'],
            'retry_only_http_status': 503,
            'minimum_provider_start_interval_seconds': 30, 'llm_config': read_json_config(),
            'prompt_chars': sum(len(b['contents'][0]['parts'][0]['text']) for b in bodies),
            'bindings': {str(p): sha256(p) for p in [CONFIG, Path(__file__), *(Path(t) for t in TESTS)]},
            'output_path': str(target.with_name(target.stem.replace('egress-packet', 'live') + '.json')),
            'test_or_holdout_content_sent': False, 'inputs': 'Two synthetic public fixtures only.'}
        write_json(target, prepared)
        print(json.dumps({'packet': str(target), 'sha256': sha256(target), 'max_calls': 2,
                          'prompt_chars': prepared['prompt_chars'], 'external_calls': 0}))
    return 0 if valid else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'collect'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--authorized-packet-sha256')
    args = parser.parse_args()
    if args.command == 'collect' and (not args.packet or not args.authorized_packet_sha256):
        parser.error('collect requires exact packet and authorized digest')
    return run(args.output, args.packet if args.command == 'collect' else None, args.authorized_packet_sha256)


if __name__ == '__main__':
    raise SystemExit(main())
