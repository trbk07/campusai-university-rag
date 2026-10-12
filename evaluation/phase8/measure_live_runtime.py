"""Bounded real-Gemini product timing and raw-format measurement, no retries.

Reuses the existing WSGI collector. This finite, predeclared workload is separate
from the 300-case recorded-Chat regression and never overwrites its evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
from unittest.mock import patch

from jsonschema import Draft202012Validator

from campusai.llm.factory import _read_config
from campusai.rag.schemas import validate_release_response, validate_response
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.common.release_artifacts import source_identity
from evaluation.phase8 import run_product_baseline as collector
from evaluation.phase8.replay_chat_baseline import ROOT, BENCHMARK, INDEX, read_rows, sha, write_json
from evaluation.phase8.score_temporal_product_outputs import _bootstrap_latency_ci, _index_tree_sha256

OUTPUT = ROOT / 'evaluation/results/phase8-live-runtime-20261012'
PREFLIGHT = ROOT / 'evaluation/results/phase8-post-fix-preflight-20261012.json'
ORIGINAL_MANIFEST = ROOT / 'evaluation/results/phase8-product-run-v5.json'
HISTORY = ROOT / 'evaluation/results/phase8-product-execution-v5.json'
SEED = 'phase8-live-runtime-20261012'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def select_cases(rows, packet, approved):
    """Predeclared stratified workload; one case per connected group, no output input."""
    groups = connected_groups(rows)
    cases = {c['qid']: c for c in packet['cases'] if c['planned_provider_call']
             and c['qid'] in approved['provider_body_sha256_by_qid']}
    by_id = {r['qid']: r for r in rows}
    selected = ['human-p7r18-curriculum-001-credits-1']
    used = {groups[selected[0]]}
    for tag, count in [('multi_hop', 5), ('temporal', 5), ('single_hop', 4), ('table', 3)]:
        eligible = sorted((r for r in rows if r['qid'] in cases and tag in r.get('tags', [])),
            key=lambda r: hashlib.sha256((SEED + r['qid']).encode()).hexdigest())
        for _ in range(count):
            remaining = [r for r in eligible if groups[r['qid']] not in used]
            if not remaining:
                raise ValueError('not enough independently grouped workload cases')
            splits = Counter(by_id[q]['split'] for q in selected)
            row = min(remaining, key=lambda r: (splits[r['split']], eligible.index(r)))
            selected.append(row['qid'])
            used.add(groups[row['qid']])
    return [cases[q] for q in selected]


def prepare(output=OUTPUT):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('measurement output must be a new project directory')
    packet, approved = read(PREFLIGHT), read(ORIGINAL_MANIFEST)
    rows = read_rows(BENCHMARK)
    config_path = ROOT / packet['llm_config']['path']
    config = _read_config(config_path)['llm']
    cases = select_cases(rows, packet, approved)
    selected_rows = [r for r in rows if r['qid'] in {c['qid'] for c in cases}]
    hashes = {c['qid']: collector.body_hash(collector.serialized_body(c, config)) for c in cases}
    if any(hashes[q] != approved['provider_body_sha256_by_qid'][q] for q in hashes):
        raise ValueError('selected payload differs from previously approved body')
    output.mkdir(parents=True)
    subset = dict(packet, cases=cases, source_identity=source_identity(ROOT),
                  provider_call_count_estimate=len(cases), prompt_characters=sum(len(c['prompt']) for c in cases))
    write_json(output / 'preflight.json', subset)
    manifest = {'schema_version': 1, 'purpose': 'LIVE_PRODUCT_LATENCY_AND_RAW_FORMAT',
        'prepared_at': datetime.now(timezone.utc).isoformat(), 'source_identity': subset['source_identity'],
        'authorization_basis': 'Owner explicitly requested measuring latency and format with real Gemini in the application; prior approved payloads and Free Tier only remain in force.',
        'scope': '18 predeclared answerable cases, one per connected group; exploratory measurement, not all 300 live requests or production SLO qualification.',
        'selection': {'seed': SEED, 'rule': 'First pending original Algebra case; then 5 multi_hop, 5 temporal, 4 single_hop and 3 additional table cases. Prefer underrepresented split, deterministic hash order, unique connected groups.',
                      'qids': [c['qid'] for c in cases],
                      'split_counts': dict(Counter(r['split'] for r in selected_rows)),
                      'tag_counts': dict(Counter(t for r in selected_rows for t in r.get('tags', []))),
                      'connected_groups': len(set(connected_groups(selected_rows).values()))},
        'endpoint': approved['endpoint'], 'model': config['model'], 'credential_name': 'key_2',
        'free_tier_only': True, 'billing_changes': False, 'paid_fallback': False,
        'free_tier_basis': 'Owner-declared Free Tier project; runner does not enable billing and cannot inspect account tier. Google lists standard Gemini 3.8 Flash input/output as Free Tier free of charge.',
        'pricing_source': 'https://ai.google.dev/gemini-api/docs/pricing',
        'daily_attempt_cap': 18, 'max_attempts': 18, 'planned_calls': len(cases),
        'max_prompt_characters': subset['prompt_characters'], 'max_output_tokens_per_attempt': 1024,
        'max_output_tokens_total': 18 * 1024, 'timeout_seconds': 15,
        'min_start_spacing_seconds': 30, 'immediate_retries': 0, 'key_rotation': False,
        'failure_policy': 'Stop on first provider/response failure. No resume or automatic new run; retain failed-request timing and raw final output if received.',
        'provider_body_sha256_by_qid': hashes,
        'bindings': {p.relative_to(ROOT).as_posix(): sha(p) for p in (
            PREFLIGHT, ORIGINAL_MANIFEST, HISTORY, BENCHMARK, config_path, output / 'preflight.json')},
        'phase8_pass': False}
    write_json(output / 'manifest.json', manifest)
    write_json(output / 'execution.json', {'schema_version': 1, 'status': 'prepared',
        'manifest_sha256': sha(output / 'manifest.json'), 'predictions': [], 'attempts': [],
        'shards': [], 'peak_working_set_bytes': 0})
    verify(manifest, subset)
    return manifest


def verify(manifest, packet):
    collector.verify_freeze()
    for name, digest in manifest['bindings'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path) != digest:
            raise ValueError('measurement binding drift: ' + name)
    config = _read_config(ROOT / packet['llm_config']['path'])['llm']
    if (source_identity(ROOT) != manifest['source_identity'] or config['provider'] != 'gemini'
            or config['model'] != 'gemini-3.8-flash' or config['max_retries'] != 0
            or config['timeout_seconds'] != 15 or config['generation_config']['maxOutputTokens'] != 1024
            or sha(ROOT / packet['llm_config']['path']) != packet['llm_config']['sha256']
            or _index_tree_sha256(INDEX) != packet['index']['tree_sha256']):
        raise ValueError('runtime/config/index drift')
    if (manifest['free_tier_only'] is not True or manifest['billing_changes'] is not False
            or manifest['max_attempts'] != 18 or manifest['immediate_retries'] != 0
            or manifest['min_start_spacing_seconds'] != 30):
        raise ValueError('measurement budget drift')
    original = read(ORIGINAL_MANIFEST)['provider_body_sha256_by_qid']
    if packet['benchmark']['sha256'] != sha(BENCHMARK):
        raise ValueError('frozen benchmark drift')
    full = {c['qid']: c for c in read(PREFLIGHT)['cases']}
    if len(packet['cases']) != 18 or [c['qid'] for c in packet['cases']] != manifest['selection']['qids']:
        raise ValueError('workload population drift')
    for case in packet['cases']:
        body = collector.body_hash(collector.serialized_body(case, config))
        if (case != full[case['qid']] or body != original[case['qid']]
                or body != manifest['provider_body_sha256_by_qid'][case['qid']]):
            raise ValueError('measurement payload drift')
    history = read(HISTORY)['attempts']
    if (sum(e.get('pacific_day') == collector.pacific_day() for e in history) + 18 > 18
            or len(history) + 18 > 160):
        raise ValueError('shared Phase 8 budget insufficient')


@contextmanager
def collector_paths(output):
    with patch.multiple(collector, PREFLIGHT=output / 'preflight.json', MANIFEST=output / 'manifest.json',
            STATE=output / 'execution.json', PREDICTIONS=output / 'predictions.jsonl',
            AMENDMENT=output / 'unused-amendment.json', verify_inputs=verify):
        yield


def summarize(output=OUTPUT):
    output = Path(output).resolve()
    state, manifest = read(output / 'execution.json'), read(output / 'manifest.json')
    cases = {c['qid']: c for c in read(output / 'preflight.json')['cases']}
    rows = [r for r in read_rows(BENCHMARK) if r['qid'] in cases]
    observations = list(state['predictions'])
    if state.get('failed_product_response'):
        failed = dict(state['failed_product_response'])
        failed['internal_response'], failed['public_response'] = failed.pop('internal'), failed.pop('public')
        observations.append(failed)
    formats = []
    for row in observations:
        provider = row.get('provider_output')
        if not provider:
            continue
        try:
            parsed = json.loads(provider['final_text'])
            valid = Draft202012Validator(cases[row['qid']]['schema']).is_valid(parsed)
            raw_json_valid = True
        except (ValueError, TypeError):
            raw_json_valid, valid = False, False
        formats.append({'qid': row['qid'], 'raw_json_valid': raw_json_valid, 'raw_schema_valid': valid,
            'finish_reason': provider['finish_reason'], 'model_version': provider['model_version'],
            'usage': provider['usage'], 'provider_latency_ms': provider['latency_ms']})
    warm = {r['qid']: r['request_latency_ms'] for r in observations if not r['cold_start']}
    values = sorted(warm.values())
    report = {'status': 'LIVE_RUNTIME_MEASURED' if state['status'] == 'completed' else 'LIVE_RUNTIME_STOPPED_INCOMPLETE',
        'reviewed_at': datetime.now(timezone.utc).isoformat(), 'scope': manifest['scope'],
        'provider_attempts': len(state['attempts']), 'successful_product_requests': len(state['predictions']),
        'planned_requests': 18, 'http_status_counts': dict(Counter(str(e.get('http_status')) for e in state['attempts'])),
        'request_observations': len(observations), 'failed_product_response_observed': bool(state.get('failed_product_response')),
        'cold_start_values_ms': [r['latency_ms'] for r in observations if r['cold_start']],
        'request_latency_values_ms': [r['request_latency_ms'] for r in observations],
        'warm_latency': {'status': 'measured' if values else 'not_measured_no_warm_request',
            'population': 'All observed warm WSGI requests, including failures; startup and inter-request pacing excluded.',
            'denominator': len(values), 'p50_ms': statistics.median(values) if values else None,
            'p95_ms': values[min(len(values)-1, int(.95*len(values)))] if values else None,
            'p99_ms': values[min(len(values)-1, int(.99*len(values)))] if values else None,
            'ci95': _bootstrap_latency_ci(rows, warm, iterations=2000) if values else None},
        'raw_format': {'status': 'measured' if formats else 'not_measured_no_provider_final_text',
            'json_valid': sum(r['raw_json_valid'] for r in formats),
            'schema_valid': sum(r['raw_schema_valid'] for r in formats), 'denominator': len(formats),
            'value': sum(r['raw_schema_valid'] for r in formats) / len(formats) if formats else None,
            'population': 'Actual unmodified provider final texts; HTTP failures have no final text and are separately reported.',
            'cases': formats, 'normalization_or_repair': False},
        'valid_provider_schema_per_attempt': {'numerator': sum(r['raw_schema_valid'] for r in formats),
            'denominator': len(state['attempts']),
            'value': sum(r['raw_schema_valid'] for r in formats) / len(state['attempts']) if state['attempts'] else None,
            'population': 'Every actual provider attempt, including unavailable/timeout; no fallback counted as model output.'},
        'application_schema': {'valid': sum(validate_response(r['internal_response'], include_internal=True)[0]
            and validate_release_response(r['public_response'])[0] for r in observations), 'denominator': len(observations),
            'policy': 'Includes error fallback; valid fallback is not successful Gemini format.'},
        'peak_working_set_bytes': state['peak_working_set_bytes'],
        'phase8_pass': False, 'officially_approved': False,
        'limitations': ['Exposed regression; at most 18 live samples, not the 300-case live baseline.',
            'WSGI application-to-provider timing; excludes browser/TCP transit and 30s inter-request quota pacing.',
            'Cold includes startup; one cold sample cannot establish a cold distribution.',
            'Any HTTP/provider failures remain failures and do not count as valid Gemini format.'],
        'bindings': {p.relative_to(ROOT).as_posix(): sha(p) for p in (
            output / 'manifest.json', output / 'execution.json', output / 'preflight.json', BENCHMARK, Path(__file__))}}
    write_json(output / 'measurement.json', report)
    return report


def run(output=OUTPUT):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('measurement output must stay within project')
    state = read(output / 'execution.json')
    if state['attempts'] or state['shards']:
        raise ValueError('finite measurement already started; no resume or repeated requests')
    with collector_paths(output):
        collector.run()
    return summarize(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'summary'])
    args = parser.parse_args()
    result = prepare() if args.action == 'prepare' else run() if args.action == 'run' else summarize()
    print(json.dumps({k: result[k] for k in ('status', 'planned_calls', 'max_prompt_characters',
        'provider_attempts', 'successful_product_requests', 'raw_format', 'warm_latency') if k in result}, indent=2))
