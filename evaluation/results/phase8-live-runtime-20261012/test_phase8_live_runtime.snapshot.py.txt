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
