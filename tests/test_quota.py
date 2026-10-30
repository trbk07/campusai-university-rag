"""Durable quota contracts; fake clock/provider, real SQLite and subprocesses."""
from datetime import datetime
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

import pytest

from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.client import GeminiClient, LLMError, LLMProviderError, LLMRateLimitError
from campusai.llm.factory import create_llm
from campusai.llm.quota import (QuotaExceeded, QuotaGovernor, QuotaPolicy,
                               QuotaStateError, estimate_gemini_tokens)


@pytest.fixture
def clock(monkeypatch):
    now = [datetime(2026, 10, 15, 12, tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()]
    monkeypatch.setattr(time, 'time', lambda: now[0])
    monkeypatch.setattr(time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(time, 'sleep', lambda delay: now.__setitem__(0, now[0] + delay))
    return now


def governor(tmp_path, **kwargs):
    wait = kwargs.pop('max_wait_seconds', 0)
    return QuotaGovernor(tmp_path/'quota.db', 'owner-project/model',
                         QuotaPolicy(kwargs.pop('requests_per_minute', 0), **kwargs), max_wait_seconds=wait)


def reserve(g, input_tokens=10, output_tokens=10, finish=True):
    key = g.reserve(input_tokens, output_tokens, lease_seconds=20)
    if finish:
        g.finish(key)
    return key


def test_rpm_spacing_wait_is_bounded_and_persistent(tmp_path, clock):
    g = governor(tmp_path, requests_per_minute=60, max_wait_seconds=2)
    reserve(g)
    initial = clock[0]
    restarted = governor(tmp_path, requests_per_minute=60, max_wait_seconds=2)
    reserve(restarted)
    assert clock[0] == initial + 1
    assert restarted.snapshot()['reserved_attempts_today'] == 2
    slower = governor(tmp_path, requests_per_minute=5, max_wait_seconds=2)
    # Policy changes preserve spent attempts; stale workers cannot send.
    with pytest.raises(QuotaStateError):
        reserve(g)
    reserve(slower)
    before = clock[0]
    with pytest.raises(QuotaExceeded) as error:
        reserve(slower)
    assert error.value.retry_after_seconds == 12 and clock[0] == before


def test_input_tpm_is_rolling_not_a_fixed_minute_bucket(tmp_path, clock):
    g = governor(tmp_path, input_tokens_per_minute=100)
    reserve(g, 60, 1000)
    with pytest.raises(QuotaExceeded) as error:
        reserve(g, 50, 0)
    assert error.value.reason == 'input_tpm' and error.value.retry_after_seconds == 60
    clock[0] += 59
    with pytest.raises(QuotaExceeded) as error:
        reserve(g, 50, 0)
    assert error.value.retry_after_seconds == 1
    clock[0] += 1
    reserve(g, 50, 0)
    assert g.snapshot()['accounted_input_tokens_last_minute'] == 50


def test_rpd_and_output_reservations_survive_restart_and_do_not_refund(tmp_path, clock):
    g = governor(tmp_path, requests_per_day=5, total_tokens_per_day=100)
    key = reserve(g, 40, 60, finish=False)
    g.finish(key, {'promptTokenCount':10, 'totalTokenCount':20})
    other = governor(tmp_path, requests_per_day=5, total_tokens_per_day=100)
    assert other.snapshot()['accounted_tokens_today'] == 100
    with pytest.raises(QuotaExceeded) as error:
        reserve(other, 1, 1)
    assert error.value.reason == 'total_tpd'
    assert other.snapshot()['reserved_attempts_today'] == 1


def test_usage_over_estimate_increases_both_counters(tmp_path, clock):
    g = governor(tmp_path, input_tokens_per_minute=100, total_tokens_per_day=150)
    key = reserve(g, 10, 10, finish=False)
    g.finish(key, {'promptTokenCount':120, 'totalTokenCount':200})
    assert g.snapshot()['accounted_input_tokens_last_minute'] == 120
    assert g.snapshot()['accounted_tokens_today'] == 200
    with pytest.raises(QuotaExceeded):
        reserve(g)


@pytest.mark.parametrize('date,hours', [(datetime(2026,3,8),23), (datetime(2026,11,1),25)])
def test_pacific_day_reset_handles_dst(tmp_path, clock, date, hours):
    clock[0] = date.replace(tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()
    g = governor(tmp_path, requests_per_day=1)
    reserve(g)
    with pytest.raises(QuotaExceeded) as error:
        reserve(g)
    assert error.value.retry_after_seconds == hours * 3600
    clock[0] += hours * 3600
    reserve(g)
    assert g.snapshot()['reserved_attempts_today'] == 1


def test_new_day_does_not_reset_rolling_minute_or_live_lease(tmp_path, clock):
    clock[0] = datetime(2026,10,15,23,59,50,tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()
    g = governor(tmp_path, requests_per_day=1, input_tokens_per_minute=15)
    reserve(g, 10, 0)
    clock[0] += 10
    with pytest.raises(QuotaExceeded) as error:
        reserve(g, 10, 0)
    assert error.value.reason == 'input_tpm' and error.value.retry_after_seconds == 50
    clock[0] += 50
    reserve(g, 10, 0)
    with sqlite3.connect(g.path) as db:
        assert db.execute('SELECT COUNT(*) FROM quota_attempts').fetchone()[0] == 1


def test_crashed_lease_expires_but_attempt_remains_charged(tmp_path, clock):
    g = governor(tmp_path, requests_per_day=2)
    reserve(g, finish=False)
    restarted = governor(tmp_path, requests_per_day=2)
    with pytest.raises(QuotaExceeded) as error:
        reserve(restarted)
    assert error.value.reason == 'in_flight' and error.value.retry_after_seconds == 20
    clock[0] += 20
    reserve(restarted)
    with pytest.raises(QuotaExceeded) as error:
        reserve(restarted)
    assert error.value.reason == 'rpd'
    clock[0] -= 24 * 3600
    with pytest.raises(QuotaExceeded):
        reserve(restarted)
    assert restarted.snapshot()['reserved_attempts_today'] == 2


def test_processes_share_atomic_daily_budget(tmp_path):
    path = tmp_path/'quota.db'
    workers = [subprocess.Popen([sys.executable, '-m', 'tests.deployment.quota_host', str(path)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(6)]
    results = []
    try:
        for worker in workers:
            output, error = worker.communicate(timeout=15)
            assert worker.returncode == 0, error
            results.append(json.loads(output))
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.communicate()
    assert sum(row['admitted'] for row in results) == 3
    g = QuotaGovernor(path, 'subprocess-test', QuotaPolicy(0, requests_per_day=3, max_in_flight=6))
    assert g.snapshot()['reserved_attempts_today'] == 3 and g.snapshot()['in_flight'] == 0


def test_in_flight_waits_for_completion_not_crash_lease(tmp_path, monkeypatch, clock):
    g = governor(tmp_path, max_wait_seconds=6)
    first = g.reserve(10, 10, lease_seconds=65)
    started = clock[0]
    def sleep(delay):
        clock[0] += delay
        if clock[0] - started >= 0.5:
            # Separate worker/connection: polling must not hold a SQLite lock.
            governor(tmp_path, max_wait_seconds=6).finish(first)
    monkeypatch.setattr(time, 'sleep', sleep)
    reserve(g)
    assert clock[0] - started == 0.5
    assert g.snapshot()['reserved_attempts_today'] == 2
    assert g.snapshot()['in_flight'] == 0


def test_busy_wait_is_bounded_and_not_reported_as_exhausted_quota(tmp_path, monkeypatch, clock):
    from campusai.llm.failures import public_provider_failure
    g = governor(tmp_path, max_wait_seconds=6)
    g.reserve(10, 10, lease_seconds=65)
    started = clock[0]
    client = GeminiClient('fake', generation_config={'maxOutputTokens':100},
                          max_retries=0, quota_governor=g)
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: pytest.fail('busy worker must not send'))
    with pytest.raises(LLMRateLimitError) as error:
        client.complete('next question')
    assert clock[0] - started == 6
    assert public_provider_failure(error.value)['error_code'] == 'provider_busy'
    assert g.snapshot()['reserved_attempts_today'] == 1


def test_hundred_distinct_questions_release_leases_and_keep_daily_accounting(tmp_path, monkeypatch, clock):
    g = governor(tmp_path, requests_per_minute=15, requests_per_day=100, max_wait_seconds=6)
    calls = []
    def transport(request, **kwargs):
        calls.append(request.data)
        clock[0] += 2
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('fake', generation_config={'maxOutputTokens':100},
                          max_retries=0, quota_governor=g)
    for number in range(100):
        assert client.complete(f'question {number}').text == 'ok'
    assert len(set(calls)) == 100
    assert g.snapshot()['reserved_attempts_today'] == 100
    assert g.snapshot()['in_flight'] == 0
    with pytest.raises(LLMRateLimitError):
        client.complete('over daily budget')
    assert len(calls) == 100


@pytest.mark.parametrize('status', [429, 503, 401, 'timeout'])
def test_failed_transports_keep_budget_and_release_lease(tmp_path, monkeypatch, clock, status):
    g = governor(tmp_path, requests_per_day=1)
    calls = []
    def transport(request, **kwargs):
        calls.append(request.data)
        if status == 'timeout':
            raise TimeoutError('private')
        raise HTTPError(request.full_url, status, 'private', {}, io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('private-key', generation_config={'maxOutputTokens':100}, max_retries=0, quota_governor=g)
    with pytest.raises(LLMError):
        client.complete('private-prompt')
    assert g.snapshot()['in_flight'] == 0
    with pytest.raises(LLMRateLimitError):
        client.complete('another')
    assert len(calls) == 1 and g.snapshot()['reserved_attempts_today'] == 1
    persisted = g.path.read_bytes()
    assert b'private-key' not in persisted and b'private-prompt' not in persisted


def test_cache_hits_need_no_reservation_and_429_is_not_cached(tmp_path, monkeypatch, clock):
    g = governor(tmp_path, requests_per_day=2)
    calls = []
    def transport(request, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise HTTPError(request.full_url,429,'private',{'Retry-After':'120'},io.BytesIO())
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('fake', generation_config={'maxOutputTokens':100}, max_retries=0,
        quota_governor=g, overload_circuit_path=tmp_path/'health.db', cache=SQLiteLLMCache(':memory:'))
    try:
        assert client.complete('good').text == 'ok'
        with pytest.raises(LLMRateLimitError):
            client.complete('bad')
        assert client.complete('good').cached
        for _ in range(20):
            with pytest.raises(LLMRateLimitError) as error:
                client.complete('bad')
            assert error.value.retry_after_seconds == 120
        assert len(calls) == 2 and g.snapshot()['reserved_attempts_today'] == 2
    finally:
        client.close()


def test_quota_rejection_does_not_occupy_recovery_probe(tmp_path, monkeypatch, clock):
    g = governor(tmp_path, requests_per_day=1)
    reserve(g)
    client = GeminiClient('fake', generation_config={'maxOutputTokens':100}, max_retries=0,
        quota_governor=g, overload_circuit_path=tmp_path/'health.db')
    client.overload_circuit.failed(0, overloaded=True)
    clock[0] += 60
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: pytest.fail('no budget'))
    with pytest.raises(LLMRateLimitError):
        client.complete('q')
    assert client.overload_circuit.remaining_seconds() == 0


def test_outage_cancels_quota_wait_without_transport(tmp_path, monkeypatch, clock):
    g = governor(tmp_path, requests_per_minute=60, max_wait_seconds=2)
    reserve(g)
    client = GeminiClient('fake', generation_config={'maxOutputTokens':100}, max_retries=0,
        quota_governor=g, overload_circuit_path=tmp_path/'health.db')
    def sleep(delay):
        clock[0] += delay
        client.overload_circuit.failed(0, overloaded=True)
    monkeypatch.setattr(time, 'sleep', sleep)
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: pytest.fail('outage'))
    with pytest.raises(LLMProviderError, match='cooling down'):
        client.complete('q')
    assert g.snapshot()['reserved_attempts_today'] == 1


def test_corrupt_state_fails_closed(tmp_path, monkeypatch, clock):
    g = governor(tmp_path)
    g.path.write_bytes(b'not sqlite')
    client = GeminiClient('fake', generation_config={'maxOutputTokens':100}, max_retries=0, quota_governor=g)
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: pytest.fail('corrupt state'))
    with pytest.raises(LLMProviderError, match='state unavailable'):
        client.complete('q')


def test_utf8_estimate_includes_schema_system_and_output_ceiling():
    body = {'contents':[{'parts':[{'text':'Tiếng Việt'}]}], 'systemInstruction':{'parts':[{'text':'system'}]},
            'generationConfig':{'maxOutputTokens':100,'candidateCount':2,'responseSchema':{'type':'OBJECT'}}}
    estimated, output = estimate_gemini_tokens(body)
    assert estimated == len(json.dumps(body,ensure_ascii=False).encode('utf-8')) + 1024
    assert output == 200


@pytest.mark.parametrize('body', [
    {}, {'generationConfig':{'maxOutputTokens':True}},
    {'generationConfig':{'maxOutputTokens':100},'cachedContent':'cached/token'},
    {'generationConfig':{'maxOutputTokens':100},'contents':[{'parts':[{'inlineData':{}}]}]},
])
def test_unknown_token_inputs_fail_closed(body):
    with pytest.raises(ValueError):
        estimate_gemini_tokens(body)


@pytest.mark.parametrize('change', [
    {'max_retries':1}, {'provider':'groq'}, {'requests_per_minute':1.5},
    {'quota':{'scope':'project/model'}},
    {'quota':{'scope':'project/model','state_path':':memory:'}},
    {'quota':{'scope':'project/model','state_path':'unused','requests_per_day':True}},
    {'quota':{'scope':'project/model','state_path':'unused','unknown_limit':1}},
    {'generation_config':{'maxOutputTokens':0}},
])
def test_invalid_factory_quota_does_not_open_cache_or_send(tmp_path, monkeypatch, change):
    body = {'provider':'gemini','model':'m','max_retries':0,'requests_per_minute':5,
            'generation_config':{'maxOutputTokens':100},'quota':{'scope':'project/model','state_path':str(tmp_path/'q.db')}}
    body.update(change)
    path = tmp_path/'config.json'
    path.write_text(json.dumps({'llm':body}),encoding='utf-8')
    monkeypatch.setattr('campusai.llm.factory.SQLiteLLMCache', lambda *_a: pytest.fail('invalid quota opened cache'))
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: pytest.fail('invalid config sent'))
    with pytest.raises(ValueError):
        create_llm(path, {'GEMINI_API_KEY':'fake','GROQ_API_KEY':'fake'})


def test_factory_constructs_governor_and_reconciles_usage(tmp_path, monkeypatch, clock):
    config = {'llm':{'provider':'gemini','model':'m','max_retries':0,'requests_per_minute':5,
        'cache_path':':memory:','generation_config':{'maxOutputTokens':100},
        'quota':{'scope':'owner/m','state_path':str(tmp_path/'q.db'),'requests_per_day':1}}}
    path = tmp_path/'config.json'
    path.write_text(json.dumps(config),encoding='utf-8')
    monkeypatch.setattr('urllib.request.urlopen',lambda *_a, **_kw: io.BytesIO(json.dumps({
        'candidates':[{'content':{'parts':[{'text':'ok'}]}}],
        'usageMetadata':{'promptTokenCount':2000,'totalTokenCount':2100}}).encode()))
    client = create_llm(path, {'GEMINI_API_KEY':'fake'})
    try:
        assert client.complete('hello').text == 'ok'
        assert client.quota_governor.snapshot()['accounted_tokens_today'] == 2100
        with pytest.raises(LLMRateLimitError):
            client.complete('new')
        assert client.complete('hello').cached
    finally:
        client.close()


def test_continuity_profile_preserves_frozen_generation_settings(tmp_path):
    from campusai.llm.factory import _read_config
    original = _read_config('configs/product_llm.yaml')['llm']
    current = _read_config('configs/continuity_llm.yaml')['llm']
    quota = current.pop('quota')
    assert current == original
    assert quota == {'state_path':'data/operations/gemini-quota.sqlite3',
        'scope':'gemini:owner:gemini-3.8-flash','max_in_flight':1,'max_wait_seconds':2}
    current['quota'] = {**quota,'state_path':str(tmp_path/'q.db')}
    current['overload_circuit_path'] = str(tmp_path/'health.db')
    path = tmp_path/'config.json'
    path.write_text(json.dumps({'llm':current}),encoding='utf-8')
    client = create_llm(path, {'GEMINI_API_KEY':'fake'})
    try:
        assert client.quota_governor.policy.requests_per_minute == 10
        assert client.quota_governor.policy.requests_per_day is None
    finally:
        client.close()


def test_explicit_twenty_second_wait_is_bounded_and_releases_sqlite_lock(tmp_path,clock,monkeypatch):
    g=governor(tmp_path,requests_per_minute=3,max_wait_seconds=20)
    reserve(g)
    started=clock[0]
    def sleep(delay):
        # Another connection remains usable during pacing.
        with sqlite3.connect(g.path,timeout=0.1) as db:
            db.execute('BEGIN IMMEDIATE')
            db.rollback()
        clock[0]+=delay
    monkeypatch.setattr(time,'sleep',sleep)
    reserve(g)
    assert clock[0]-started==20
    with pytest.raises(ValueError,match='between 0 and 20'):
        governor(tmp_path,requests_per_minute=3,max_wait_seconds=21)
