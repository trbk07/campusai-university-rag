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
import subprocess
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
FOLLOWUP = ROOT / 'evaluation/results/phase8-live-unattempted-20261012'
REMAINING = ROOT / 'evaluation/results/phase8-live-remaining-20261013'
CURRENT_REGRESSION = ROOT / '.local_artifacts/experiment_runs/phase8-current-runtime-20261013'
OTHER_LEDGER_PATHS = (
    ROOT / 'evaluation/results/phase7-live-integration-20261013/verified-live.json',
    ROOT / '.local_artifacts/experiment_runs/phase7-free-tier-performance-20261013/live/cycle-1.json',
)
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


def unattempted_cases(packet, state):
    """Keep the failed case terminal; never resend any previous provider attempt."""
    attempts = [event['qid'] for event in state['attempts']]
    completed = [row['qid'] for row in state['predictions']]
    population = [case['qid'] for case in packet['cases']]
    if (len(attempts) != len(set(attempts)) or len(completed) != len(set(completed))
            or not set(completed) <= set(attempts) <= set(population)
            or attempts != population[:len(attempts)]):
        raise ValueError('previous measurement is not a unique attempted prefix')
    if state['status'] != 'waiting_next_pacific_day' or not attempts:
        raise ValueError('previous measurement is not a stopped cohort')
    return [case for case in packet['cases'] if case['qid'] not in set(attempts)]


def check_shared_allowance(events, planned, day):
    if (not 0 < planned <= 18
            or sum(e.get('pacific_day') == day for e in events) + planned > 18
            or len(events) + planned > 160):
        raise ValueError('shared Phase 8 allowance insufficient; wait without sending')


def remaining_inputs():
    """Keep both terminal cohorts immutable and exclude every prior attempt."""
    original_packet = read(OUTPUT / 'preflight.json')
    original_state = read(OUTPUT / 'execution.json')
    first_remaining = unattempted_cases(original_packet, original_state)
    followup_packet = read(FOLLOWUP / 'preflight.json')
    followup_state = read(FOLLOWUP / 'execution.json')
    if followup_packet['cases'] != first_remaining:
        raise ValueError('historical cohorts overlap or change workload order')
    cases = unattempted_cases(followup_packet, followup_state)
    for directory, packet, state in ((OUTPUT, original_packet, original_state),
                                      (FOLLOWUP, followup_packet, followup_state)):
        manifest = read(directory / 'manifest.json')
        if state['manifest_sha256'] != sha(directory / 'manifest.json'):
            raise ValueError('historical execution manifest drift')
        for name, digest in manifest['bindings'].items():
            if sha(ROOT / name) != digest:
                raise ValueError('historical measurement input drift: ' + name)
        if packet['benchmark']['sha256'] != sha(BENCHMARK):
            raise ValueError('historical benchmark drift')
    events = read(HISTORY)['attempts'] + original_state['attempts'] + followup_state['attempts']
    for path in OTHER_LEDGER_PATHS:
        ledger = read(path)
        if 'provider_starts' in ledger:
            starts = ledger['provider_starts']
        else:
            if ledger.get('offline') is not False:
                raise ValueError('shared history is not live')
            starts = [o['provider_start'] for o in ledger['observations']]
        if len(starts) != ledger['external_provider_calls']:
            raise ValueError('shared provider start ledger incomplete')
        events += [{'pacific_day': collector.pacific_day(datetime.fromtimestamp(s, timezone.utc))}
                   for s in starts]
    return original_packet, cases, events, followup_state


def verify_current_regression():
    """An actual 300-request replay binds current product code, index and prompts."""
    receipt = read(CURRENT_REGRESSION / 'execution.json')
    review = read(CURRENT_REGRESSION / 'baseline-review.json')
    if (receipt['status'] != 'completed' or receipt['provider_requests_sent'] != 0
            or receipt['requests'] != 300 or receipt['chat_replay_requests'] != 145
            or receipt['local_requests'] != 155 or receipt['network_disabled'] is not True
            or receipt['source_identity']['runtime_sha256'] != source_identity(ROOT)['runtime_sha256']
            or receipt['bindings']['original_preflight_sha256'] != sha(PREFLIGHT)
            or receipt['bindings']['index_tree_sha256'] != _index_tree_sha256(INDEX)
            or review['exit']['content_and_local_regression_pass'] is not True):
        raise ValueError('current product regression does not qualify this measurement')
    for name, digest in review['bindings'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('current regression binding drift: ' + name)
    # Reconstruct the replay's full source tree. Only the two measurement
    # dispatchers and their tests may differ; serving, index/model logic and
    # configuration must still be byte-identical to the tested product.
    overrides = {
        'evaluation/phase8/measure_live_runtime.py': FOLLOWUP / 'measure_live_runtime.snapshot.py.txt',
        'tests/test_phase8_live_runtime.py': FOLLOWUP / 'test_phase8_live_runtime.snapshot.py.txt',
        'scripts/benchmarks/product_performance.py': None,
        'tests/test_product_performance.py': None,
    }
    paths = set()
    for directory in ('src', 'evaluation', 'scripts', 'tests'):
        paths.update(p for p in (ROOT / directory).rglob('*.py')
                     if p.is_file() and '__pycache__' not in p.parts)
    paths.update(p for p in (ROOT / 'configs').rglob('*') if p.is_file()
                 and p.suffix.lower() in {'.json', '.toml', '.yaml', '.yml'}
                 and p.name not in {'gemini.yaml', 'key.yaml'})
    paths.update(ROOT / n for n in ('pyproject.toml', 'requirements.txt', 'requirements-dev.txt', 'uv.lock', 'poetry.lock')
                 if (ROOT / n).is_file())
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: p.relative_to(ROOT).as_posix()):
        name = path.relative_to(ROOT).as_posix()
        if name in overrides:
            snapshot = overrides[name]
            content = (snapshot.read_bytes() if snapshot else subprocess.check_output(
                ['git', 'show', receipt['source_identity']['commit'] + ':' + name], cwd=ROOT))
        else:
            content = path.read_bytes()
        encoded = name.encode()
        digest.update(len(encoded).to_bytes(4, 'big'))
        digest.update(encoded)
        digest.update(hashlib.sha256(content).digest())
    if digest.hexdigest() != receipt['source_identity']['source_sha256']:
        raise ValueError('product source changed outside measurement dispatchers/tests')


def prepare_remaining(output=REMAINING):
    """One finite remaining cohort on the accepted current product runtime."""
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('remaining output must be a new project directory')
    parent_packet, cases, events, _state = remaining_inputs()
    verify_current_regression()
    if not cases:
        raise ValueError('no unattempted cases remain')
    check_shared_allowance(events, len(cases), collector.pacific_day())
    subset = dict(parent_packet, cases=cases, source_identity=source_identity(ROOT),
                  provider_call_count_estimate=len(cases), prompt_characters=sum(len(c['prompt']) for c in cases))
    parent = read(OUTPUT / 'manifest.json')
    by_id = {r['qid']: r for r in read_rows(BENCHMARK)}
    selected = [by_id[c['qid']] for c in cases]
    output.mkdir(parents=True)
    write_json(output / 'preflight.json', subset)
    bound = [PREFLIGHT, ORIGINAL_MANIFEST, HISTORY, BENCHMARK, ROOT / subset['llm_config']['path'],
             output / 'preflight.json', CURRENT_REGRESSION / 'execution.json',
             CURRENT_REGRESSION / 'baseline-review.json', *OTHER_LEDGER_PATHS,
             FOLLOWUP / 'measure_live_runtime.snapshot.py.txt', FOLLOWUP / 'test_phase8_live_runtime.snapshot.py.txt']
    for directory in (OUTPUT, FOLLOWUP):
        bound += [directory / name for name in ('manifest.json', 'preflight.json', 'execution.json', 'measurement.json')]
    manifest = dict(parent, purpose='LIVE_REMAINING_CURRENT_RUNTIME',
        prepared_at=datetime.now(timezone.utc).isoformat(), source_identity=subset['source_identity'],
        authorization_basis='Active owner goal: finish the 13 never-attempted Phase 8 live cases, Free Tier only, unchanged payloads and budgets. This does not reopen terminal runs.',
        scope=f'{len(cases)} never-attempted cases from the fixed 18-group workload on current runtime; retain five historical observations separately with their original runtime identity. Not a single-runtime 18-case SLO claim.',
        selection={'seed': SEED, 'rule': 'Original order excluding all attempts in both terminal cohorts.',
            'qids': [c['qid'] for c in cases], 'connected_groups': len(cases),
            'split_counts': dict(Counter(r['split'] for r in selected)),
            'tag_counts': dict(Counter(t for r in selected for t in r.get('tags', [])))},
        planned_calls=len(cases), max_attempts=len(cases),
        max_prompt_characters=subset['prompt_characters'], max_output_tokens_total=len(cases) * 1024,
        provider_body_sha256_by_qid={c['qid']: parent['provider_body_sha256_by_qid'][c['qid']] for c in cases},
        failure_policy='Stop on first provider/response failure; no retries, resume, key rotation, or automatically created successor run.',
        bindings={p.relative_to(ROOT).as_posix(): sha(p) for p in bound})
    write_json(output / 'manifest.json', manifest)
    write_json(output / 'execution.json', {'schema_version': 1, 'status': 'prepared',
        'manifest_sha256': sha(output / 'manifest.json'), 'predictions': [], 'attempts': [],
        'shards': [], 'peak_working_set_bytes': 0})
    verify(manifest, subset)
    return manifest


def prepare_followup(output=FOLLOWUP):
    """Prepare one finite cohort of unattempted bodies, without reopening the parent."""
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('followup output must be a new project directory')
    parent = read(OUTPUT / 'manifest.json')
    parent_packet, parent_state = read(OUTPUT / 'preflight.json'), read(OUTPUT / 'execution.json')
    for name, digest in parent['bindings'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('previous measurement binding drift: ' + name)
    cases = unattempted_cases(parent_packet, parent_state)
    if not cases:
        raise ValueError('no unattempted cases remain')
    current = source_identity(ROOT)
    if current['runtime_sha256'] != parent['source_identity']['runtime_sha256']:
        raise ValueError('product runtime changed; cannot combine these cohorts')
    # Check shared daily/total allowance before creating any execution state.
    events = read(HISTORY)['attempts'] + parent_state['attempts']
    check_shared_allowance(events, len(cases), collector.pacific_day())
    output.mkdir(parents=True)
    subset = dict(parent_packet, cases=cases, source_identity=current,
                  provider_call_count_estimate=len(cases), prompt_characters=sum(len(c['prompt']) for c in cases))
    write_json(output / 'preflight.json', subset)
    manifest = dict(parent, purpose='LIVE_UNATTEMPTED_FINITE_COHORT',
        prepared_at=datetime.now(timezone.utc).isoformat(), source_identity=current,
        authorization_basis='Owner requested continuing Phase 8 after the closed measurement. Only previously approved bodies never attempted in that cohort; existing Free Tier, daily and total ceilings remain in force.',
        scope=f'{len(cases)} previously unattempted cases of the fixed 18-group live workload; prior successes and the failed case are never resent. Separate finite execution, no resume.',
        selection=dict(parent['selection'], qids=[c['qid'] for c in cases],
                       connected_groups=len(cases), rule='Original fixed workload order, excluding every previous provider attempt.'),
        planned_calls=len(cases), max_attempts=len(cases),
        max_prompt_characters=subset['prompt_characters'], max_output_tokens_total=len(cases) * 1024,
        provider_body_sha256_by_qid={c['qid']: parent['provider_body_sha256_by_qid'][c['qid']] for c in cases},
        parent_output=OUTPUT.relative_to(ROOT).as_posix(),
        failure_policy='Stop at first provider/response failure. No retries, resume, key rotation, or third cohort authorized by this manifest.',
        bindings={p.relative_to(ROOT).as_posix(): sha(p) for p in (
            PREFLIGHT, ORIGINAL_MANIFEST, HISTORY, BENCHMARK, ROOT / subset['llm_config']['path'],
            OUTPUT / 'manifest.json', OUTPUT / 'preflight.json', OUTPUT / 'execution.json',
            OUTPUT / 'measurement.json', OUTPUT / 'measurement-review.json', output / 'preflight.json')})
    # Selection counts refer to this cohort, not the original 18-case population.
    by_id = {r['qid']: r for r in read_rows(BENCHMARK)}
    selected_rows = [by_id[c['qid']] for c in cases]
    manifest['selection']['split_counts'] = dict(Counter(r['split'] for r in selected_rows))
    manifest['selection']['tag_counts'] = dict(Counter(t for r in selected_rows for t in r.get('tags', [])))
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
    remaining = manifest.get('purpose') == 'LIVE_REMAINING_CURRENT_RUNTIME'
    followup = manifest.get('purpose') == 'LIVE_UNATTEMPTED_FINITE_COHORT'
    planned = len(packet['cases'])
    if (manifest['free_tier_only'] is not True or manifest['billing_changes'] is not False
            or manifest['max_attempts'] != (planned if followup or remaining else 18) or manifest['immediate_retries'] != 0
            or manifest['min_start_spacing_seconds'] != 30):
        raise ValueError('measurement budget drift')
    original = read(ORIGINAL_MANIFEST)['provider_body_sha256_by_qid']
    if packet['benchmark']['sha256'] != sha(BENCHMARK):
        raise ValueError('frozen benchmark drift')
    full = {c['qid']: c for c in read(PREFLIGHT)['cases']}
    if ((not followup and not remaining and planned != 18) or not 0 < planned <= 18
            or [c['qid'] for c in packet['cases']] != manifest['selection']['qids']):
        raise ValueError('workload population drift')
    if followup:
        if manifest.get('parent_output') != OUTPUT.relative_to(ROOT).as_posix():
            raise ValueError('followup parent drift')
        parent_packet, parent_state = read(OUTPUT / 'preflight.json'), read(OUTPUT / 'execution.json')
        if packet['cases'] != unattempted_cases(parent_packet, parent_state):
            raise ValueError('followup contains attempted or reordered cases')
        if manifest['source_identity']['runtime_sha256'] != read(OUTPUT / 'manifest.json')['source_identity']['runtime_sha256']:
            raise ValueError('followup product runtime drift')
        from scripts.operations.with_gemini_key import read_key
        credential = read_key(ROOT / 'configs/key.yaml', manifest['credential_name'])
        if hashlib.sha256(credential.encode()).hexdigest() != parent_state['credential_fingerprint']:
            raise ValueError('followup credential changed')
        if (manifest['max_prompt_characters'] != sum(len(c['prompt']) for c in packet['cases'])
                or manifest['max_output_tokens_total'] != planned * 1024
                or manifest['max_output_tokens_per_attempt'] != 1024
                or manifest['timeout_seconds'] != 15 or manifest['key_rotation'] is not False
                or manifest['credential_name'] != 'key_2'):
            raise ValueError('followup budget/credential drift')
    if remaining:
        _parent, expected, events, state = remaining_inputs()
        verify_current_regression()
        from scripts.operations.with_gemini_key import read_key
        credential = read_key(ROOT / 'configs/key.yaml', manifest['credential_name'])
        if (packet['cases'] != expected or manifest['credential_name'] != 'key_2'
                or hashlib.sha256(credential.encode()).hexdigest() != state['credential_fingerprint']
                or manifest['daily_attempt_cap'] != 18 or manifest['paid_fallback'] is not False
                or manifest['max_prompt_characters'] != sum(len(c['prompt']) for c in expected)
                or manifest['max_output_tokens_total'] != planned * 1024
                or manifest['max_output_tokens_per_attempt'] != 1024
                or manifest['timeout_seconds'] != 15 or manifest['key_rotation'] is not False):
            raise ValueError('remaining cohort payload, credential or budget drift')
        check_shared_allowance(events, planned, collector.pacific_day())
    for case in packet['cases']:
        body = collector.body_hash(collector.serialized_body(case, config))
        if (case != full[case['qid']] or body != original[case['qid']]
                or body != manifest['provider_body_sha256_by_qid'][case['qid']]):
            raise ValueError('measurement payload drift')
    history = read(HISTORY)['attempts']
    if followup:
        history += read(OUTPUT / 'execution.json')['attempts']
    check_shared_allowance(history, planned, collector.pacific_day())


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
        'planned_requests': manifest.get('planned_calls', 18), 'http_status_counts': dict(Counter(str(e.get('http_status')) for e in state['attempts'])),
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
    parser.add_argument('action', choices=['prepare', 'run', 'summary', 'prepare-followup', 'run-followup', 'summary-followup',
                                         'prepare-remaining', 'run-remaining', 'summary-remaining'])
    args = parser.parse_args()
    if args.action.endswith('-remaining'):
        result = prepare_remaining() if args.action == 'prepare-remaining' else run(REMAINING) if args.action == 'run-remaining' else summarize(REMAINING)
    elif args.action.endswith('-followup'):
        result = prepare_followup() if args.action == 'prepare-followup' else run(FOLLOWUP) if args.action == 'run-followup' else summarize(FOLLOWUP)
    else:
        result = prepare() if args.action == 'prepare' else run() if args.action == 'run' else summarize()
    print(json.dumps({k: result[k] for k in ('status', 'planned_calls', 'max_prompt_characters',
        'provider_attempts', 'successful_product_requests', 'raw_format', 'warm_latency') if k in result}, indent=2))
