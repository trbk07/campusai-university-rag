"""Measurement controls and raw-format denominators, never real network."""
import json
from pathlib import Path

import pytest

from evaluation.phase8 import measure_live_runtime as live


def test_workload_is_deterministic_unique_and_previously_approved():
    rows = live.read_rows(live.BENCHMARK)
    packet, approved = live.read(live.PREFLIGHT), live.read(live.ORIGINAL_MANIFEST)
    selected = live.select_cases(rows, packet, approved)
    assert selected == live.select_cases(rows, packet, approved)
    assert len(selected) == len({r['qid'] for r in selected}) == 18
    groups = live.connected_groups(rows)
    assert len({groups[r['qid']] for r in selected}) == 18
    assert selected[0]['qid'] == 'human-p7r18-curriculum-001-credits-1'
    assert all(r['planned_provider_call'] and r['qid'] in approved['provider_body_sha256_by_qid'] for r in selected)


@pytest.fixture
def measured(tmp_path, monkeypatch):
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    benchmark = tmp_path / 'benchmark.jsonl'
    benchmark.write_text('{"qid":"q","question":"question","source_group":"g"}\n', encoding='utf-8')
    monkeypatch.setattr(live, 'BENCHMARK', benchmark)
    live.write_json(tmp_path / 'manifest.json', {'scope': 'test workload'})
    live.write_json(tmp_path / 'preflight.json', {'cases': [{'qid': 'q', 'schema': {
        'type': 'object', 'required': ['answer'], 'properties': {'answer': {'type': 'string'}},
        'additionalProperties': False}}]})
    monkeypatch.setattr(live, 'validate_response', lambda *_a, **_kw: (True, []))
    monkeypatch.setattr(live, 'validate_release_response', lambda *_a, **_kw: (True, []))
    # Bind the actual module source as a fixture-local copy; no external writes.
    source = tmp_path / 'measure_live_runtime.py'
    source.write_bytes(Path(live.__file__).read_bytes())
    monkeypatch.setattr(live, '__file__', str(source))
    return tmp_path


@pytest.mark.parametrize('text, json_ok, schema_ok', [
    ('{"answer":"real"}', True, True), ('{"answer":42}', True, False),
    ('{"answer":"cut', False, False),
])
def test_raw_format_measurement_never_repairs_output(measured, text, json_ok, schema_ok):
    provider = {'final_text': text, 'finish_reason': 'STOP', 'model_version': 'actual-model',
                'usage': {}, 'latency_ms': 25}
    live.write_json(measured / 'execution.json', {'status': 'completed', 'predictions': [{
        'qid': 'q', 'provider_output': provider, 'internal_response': {}, 'public_response': {},
        'cold_start': True, 'latency_ms': 125, 'request_latency_ms': 30}],
        'attempts': [{'http_status': 200}], 'peak_working_set_bytes': 100})
    report = live.summarize(measured)
    assert report['raw_format']['denominator'] == 1
    assert report['raw_format']['json_valid'] == int(json_ok)
    assert report['raw_format']['schema_valid'] == int(schema_ok)
    assert report['raw_format']['normalization_or_repair'] is False
    assert live.read(measured / 'execution.json')['predictions'][0]['provider_output']['final_text'] == text


def test_503_fallback_schema_is_not_counted_as_gemini_format(measured):
    live.write_json(measured / 'execution.json', {'status': 'waiting_next_pacific_day', 'predictions': [],
        'attempts': [{'http_status': 503}], 'peak_working_set_bytes': 100,
        'failed_product_response': {'qid': 'q', 'internal': {}, 'public': {}, 'provider_output': None,
            'cold_start': True, 'request_latency_ms': 40, 'latency_ms': 140}})
    report = live.summarize(measured)
    assert report['provider_attempts'] == 1 and report['successful_product_requests'] == 0
    assert report['raw_format']['status'] == 'not_measured_no_provider_final_text'
    assert report['raw_format']['denominator'] == 0
    assert report['application_schema'] == {'valid': 1, 'denominator': 1,
        'policy': 'Includes error fallback; valid fallback is not successful Gemini format.'}
    assert report['request_latency_values_ms'] == [40]
    assert report['phase8_pass'] is False


def test_started_measurement_cannot_resume_or_resend(measured):
    live.write_json(measured / 'execution.json', {'attempts': [{'qid': 'q'}], 'shards': []})
    with pytest.raises(ValueError, match='no resume'):
        live.run(measured)


def test_followup_excludes_successful_and_failed_attempts():
    packet = {'cases': [{'qid': q} for q in ['success', 'failed', 'unattempted']]}
    state = {'status': 'waiting_next_pacific_day',
             'attempts': [{'qid': 'success'}, {'qid': 'failed', 'http_status': 503}],
             'predictions': [{'qid': 'success'}]}
    assert live.unattempted_cases(packet, state) == [{'qid': 'unattempted'}]


@pytest.mark.parametrize('attempts,completed,status', [
    (['a', 'a'], ['a'], 'waiting_next_pacific_day'),
    (['b'], ['b'], 'waiting_next_pacific_day'),
    (['a'], ['b'], 'waiting_next_pacific_day'),
    (['a'], ['a', 'a'], 'waiting_next_pacific_day'),
    (['a'], ['a'], 'running'),
    ([], [], 'waiting_next_pacific_day'),
])
def test_followup_rejects_ambiguous_or_active_parent(attempts, completed, status):
    with pytest.raises(ValueError):
        live.unattempted_cases({'cases': [{'qid': 'a'}, {'qid': 'b'}]}, {
            'status': status, 'attempts': [{'qid': q} for q in attempts],
            'predictions': [{'qid': q} for q in completed]})


def test_shared_allowance_counts_prior_failures_and_other_days():
    prior = [{'pacific_day': 'today', 'http_status': 503}] * 4
    live.check_shared_allowance(prior, 14, 'today')
    with pytest.raises(ValueError, match='shared'):
        live.check_shared_allowance(prior, 15, 'today')
    live.check_shared_allowance(prior, 18, 'tomorrow')
    with pytest.raises(ValueError, match='shared'):
        live.check_shared_allowance([{'pacific_day': 'old'}] * 158, 3, 'today')


def test_remaining_real_cohort_is_thirteen_unique_never_attempted_cases():
    _packet, cases, events, _state = live.remaining_inputs()
    assert len(cases) == len({c['qid'] for c in cases}) == 13
    attempted = {e['qid'] for directory in (live.OUTPUT, live.FOLLOWUP)
                 for e in live.read(directory / 'execution.json')['attempts']}
    assert not attempted.intersection(c['qid'] for c in cases)
    # Seven Phase 8 attempts plus two integration starts and a failed Phase 7 start.
    assert len(events) == 10


def test_historical_regression_rejects_an_unmeasured_runtime_without_network(monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: pytest.fail('network sent'))
    # Phase 9 changes the serving runtime. The old Phase 8 receipt must remain
    # historical and cannot authorize new live measurements. Test that guard
    # without assuming the checkout always equals the old replay's source tree.
    identity = dict(live.source_identity(live.ROOT), runtime_sha256='unmeasured-runtime')
    monkeypatch.setattr(live, 'source_identity', lambda _root: identity)
    with pytest.raises(ValueError, match='does not qualify'):
        live.verify_current_regression()


@pytest.fixture
def remaining_history(tmp_path, monkeypatch):
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    original, followup = tmp_path / 'original', tmp_path / 'followup'
    original.mkdir()
    followup.mkdir()
    monkeypatch.setattr(live, 'OUTPUT', original)
    monkeypatch.setattr(live, 'FOLLOWUP', followup)
    benchmark = tmp_path / 'benchmark.jsonl'
    benchmark.write_text('frozen', encoding='utf-8')
    monkeypatch.setattr(live, 'BENCHMARK', benchmark)
    history = tmp_path / 'history.json'
    live.write_json(history, {'attempts': []})
    monkeypatch.setattr(live, 'HISTORY', history)
    integration = tmp_path / 'integration.json'
    live.write_json(integration, {'offline': False, 'external_provider_calls': 2,
        'observations': [{'provider_start': 1791900000}, {'provider_start': 1791900030}]})
    monkeypatch.setattr(live, 'OTHER_LEDGER_PATHS', (integration,))
    for directory, qids, attempted in ((original, ['a', 'b', 'c'], ['a']), (followup, ['b', 'c'], ['b'])):
        live.write_json(directory / 'manifest.json', {'bindings': {}})
        live.write_json(directory / 'preflight.json', {'cases': [{'qid': q} for q in qids],
            'benchmark': {'sha256': live.sha(benchmark)}})
        live.write_json(directory / 'execution.json', {'status': 'waiting_next_pacific_day',
            'manifest_sha256': live.sha(directory / 'manifest.json'),
            'attempts': [{'qid': q, 'http_status': 503, 'pacific_day': '2026-10-13'} for q in attempted],
            'predictions': []})
    return original, followup, integration


def test_remaining_counts_failed_calls_and_integration_starts(remaining_history):
    _packet, cases, events, _state = live.remaining_inputs()
    assert cases == [{'qid': 'c'}]
    assert len(events) == 4 and all(e['pacific_day'] == '2026-10-13' for e in events)


@pytest.mark.parametrize('damage', ['overlap', 'manifest', 'missing_start'])
def test_remaining_rejects_corrupt_or_overlapping_history(remaining_history, damage):
    original, followup, integration = remaining_history
    if damage == 'overlap':
        path = followup / 'preflight.json'
        packet = live.read(path)
        packet['cases'] = [{'qid': 'a'}, {'qid': 'c'}]
        live.write_json(path, packet)
    elif damage == 'manifest':
        live.write_json(original / 'manifest.json', {'bindings': {}, 'tampered': True})
    else:
        ledger = live.read(integration)
        ledger['observations'].pop()
        live.write_json(integration, ledger)
    with pytest.raises(ValueError):
        live.remaining_inputs()


def test_remaining_prepare_checks_quota_before_creating_state(tmp_path, monkeypatch):
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    monkeypatch.setattr(live, 'remaining_inputs', lambda: ({}, [{'qid': 'pending'}],
        [{'pacific_day': 'today'}] * 18, {}))
    monkeypatch.setattr(live, 'verify_current_regression', lambda: None)
    monkeypatch.setattr(live.collector, 'pacific_day', lambda: 'today')
    output = tmp_path / 'new-cohort'
    with pytest.raises(ValueError, match='shared'):
        live.prepare_remaining(output)
    assert not output.exists()
