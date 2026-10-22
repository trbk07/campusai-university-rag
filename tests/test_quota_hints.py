"""Typed free-quota exhaustion must stop transport until the correct window."""
import io
import json
from datetime import datetime
from urllib.error import HTTPError

import pytest
from campusai.llm.client import GeminiClient, LLMRateLimitError
from campusai.llm.quota import QuotaGovernor, QuotaPolicy
from campusai.llm.quota_hints import google_quota_hints, scoped_quota_hint

MODEL = 'gemini-3.5-flash-lite'


def quota_error(kind='Day', value='50', model=MODEL, delay='2.5s'):
    return {'error': {'message': 'private detail must stay private', 'details': [
        {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': delay},
        {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{
            'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests',
            'quotaId': f'GenerateRequestsPer{kind}PerProjectPerModel-FreeTier',
            'quotaDimensions': {'model': model, 'location': 'global', 'project': 'private-project'},
            'quotaValue': value, 'futureQuotaValue': '1000', 'subject': 'private-project'}]}]}}


@pytest.mark.parametrize('now,seconds', [('2026-03-08T08:00:00+00:00', 23*3600),
                                        ('2026-11-01T07:00:00+00:00', 25*3600)])
def test_daily_reset_handles_pacific_dst(now, seconds, monkeypatch):
    timestamp = datetime.fromisoformat(now).timestamp()
    monkeypatch.setattr('campusai.llm.quota_hints.time.time', lambda: timestamp)
    delay, violations = scoped_quota_hint(google_quota_hints(quota_error()), MODEL)
    assert delay == seconds and violations[0]['value'] == 50
    assert 'private' not in json.dumps(violations)


@pytest.mark.parametrize('payload', [None, [], {'error': []}, {'error': {'details': 2}},
    {'error': {'message': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit 50'}}])
def test_untyped_or_malformed_error_prose_is_not_a_quota_limit(payload):
    assert google_quota_hints(payload) == {'retry_delay_seconds': None, 'violations': []}


@pytest.mark.parametrize('duration', ['NaNs', 'Infinitys', '-1s', '1e6s', '86401s', {}, None])
def test_invalid_retry_duration_is_ignored(duration):
    assert google_quota_hints(quota_error(delay=duration))['retry_delay_seconds'] is None


def test_different_model_does_not_block_this_model_until_midnight():
    delay, violations = scoped_quota_hint(google_quota_hints(quota_error(model='gemini-other')), MODEL)
    assert delay == 2.5 and violations == []


def test_free_daily_exhaustion_survives_restart_without_more_posts(tmp_path, monkeypatch):
    now = [datetime.fromisoformat('2026-10-16T01:00:00+00:00').timestamp()]
    monkeypatch.setattr('campusai.llm.quota_hints.time.time', lambda: now[0])
    calls = []
    def transport(request, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 429, 'quota', {}, io.BytesIO(json.dumps(quota_error()).encode()))
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    def client():
        return GeminiClient('fake', model=MODEL, max_retries=0, generation_config={'maxOutputTokens': 100},
            overload_circuit_path=tmp_path/'circuit.db', quota_governor=QuotaGovernor(
                tmp_path/'quota.db', 'owner', QuotaPolicy(0), max_wait_seconds=0))
    first = client()
    with pytest.raises(LLMRateLimitError) as failure:
        first.complete('first')
    delay = failure.value.retry_after_seconds
    assert delay == 6*3600  # Next midnight Pacific, 07:00 UTC in October.
    first.close()
    restarted = client()
    try:
        now[0] += 301
        for i in range(20):
            with pytest.raises(LLMRateLimitError):
                restarted.complete(f'new {i}')
        assert len(calls) == 1
        snapshot = restarted.quota_governor.snapshot()
        assert snapshot['reserved_attempts_today'] == 1
        assert snapshot['observed_provider_limits']['requests_per_day']['value'] == 50
        assert 'private' not in json.dumps(snapshot)
        now[0] += delay - 301
        assert restarted.complete('recover').text == 'ok' and len(calls) == 2
    finally:
        restarted.close()


def test_minute_retry_info_respected_without_exponential_day_block(tmp_path, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr('campusai.llm.quota_hints.time.time', lambda: now[0])
    def transport(request, **kwargs):
        raise HTTPError(request.full_url, 429, 'quota', {}, io.BytesIO(json.dumps(
            quota_error(kind='Minute', delay='120s')).encode()))
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('fake', model=MODEL, max_retries=0, overload_circuit_path=tmp_path/'circuit.db')
    try:
        with pytest.raises(LLMRateLimitError) as failure:
            client.complete('first')
        assert failure.value.retry_after_seconds == 120
    finally:
        client.close()
