"""Exercise overload recovery using a fake clock/transport and real SQLite."""
import io
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError

import pytest

from campusai.llm.client import GeminiClient, LLMError
from campusai.llm.overload import OverloadCircuit, ProviderCoolingDown
from campusai.llm.cache import SQLiteLLMCache


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr('campusai.llm.overload.time.time', lambda: now[0])
    return now


def test_persistent_cooldown_shared_by_keys_then_one_real_recovery(tmp_path, monkeypatch, clock):
    path = tmp_path / 'health.sqlite3'
    sent = []
    def transport(request, **_):
        sent.append(request.data)
        if len(sent) == 1:
            raise HTTPError(request.full_url, 503, 'busy', {'Retry-After': '120'}, io.BytesIO())
        return io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('key-two', max_retries=0, overload_circuit_path=path)
    with pytest.raises(LLMError):
        client.complete('q')
    # New client + different credential + different prompt cannot bypass 503.
    other = GeminiClient('key-three', max_retries=0, overload_circuit_path=path)
    for _ in range(20):
        with pytest.raises(LLMError, match='cooling down') as error:
            other.complete('different question')
        assert error.value.retry_after_seconds == 120
    assert len(sent) == 1
    clock[0] += 119
    with pytest.raises(LLMError, match='cooling down'):
        other.complete('q')
    clock[0] += 1
    assert other.complete('q').text == 'ok'
    assert len(sent) == 2 and sent[0] == sent[1]
    assert client.complete('another').text == 'ok'
    assert len(sent) == 3


def test_concurrent_recovery_admits_one_and_crashed_lease_expires(tmp_path, clock):
    circuit = OverloadCircuit(tmp_path / 'health.db', 'model')
    circuit.failed(0, overloaded=True)
    clock[0] += 60
    def acquire(_):
        try:
            return circuit.acquire(15)
        except ProviderCoolingDown:
            return None
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(acquire, range(8)))
    assert sum(value is not None for value in results) == 1
    old = next(value for value in results if value is not None)
    clock[0] += 21
    new = circuit.acquire(15)
    circuit.succeeded(old)
    with pytest.raises(ProviderCoolingDown):
        circuit.acquire(15)
    circuit.succeeded(new)
    circuit.acquire(15)


def test_repeated_outages_backoff_and_stale_success_cannot_clear_them(tmp_path, clock):
    circuit = OverloadCircuit(tmp_path / 'health.db', 'model')
    generation = circuit.acquire(15)
    for delay in (60, 120, 240, 300, 300):
        circuit.failed(generation, overloaded=True)
        circuit.succeeded(generation)
        with pytest.raises(ProviderCoolingDown) as error:
            circuit.acquire(15)
        assert error.value.retry_after_seconds == delay
        clock[0] += delay
        generation = circuit.acquire(15)
    circuit.succeeded(generation)
    assert circuit.acquire(15) is not None


def test_success_cache_remains_available_during_cooldown(tmp_path, monkeypatch, clock):
    def transport(request, **_):
        prompt = json.loads(request.data)['contents'][0]['parts'][0]['text']
        if prompt == 'fail':
            raise HTTPError(request.full_url, 503, 'busy', {}, io.BytesIO())
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('fake', max_retries=0, overload_circuit_path=tmp_path / 'health.db',
                          cache=SQLiteLLMCache(':memory:'))
    try:
        assert client.complete('good').text == 'ok'
        with pytest.raises(LLMError):
            client.complete('fail')
        assert client.complete('good').cached
        with pytest.raises(LLMError, match='cooling down'):
            client.complete('uncached')
    finally:
        client.close()


def test_overload_cancels_requests_already_waiting_in_rate_limiter(tmp_path, monkeypatch, clock):
    from types import SimpleNamespace
    path = tmp_path / 'health.db'
    client = GeminiClient('fake', max_retries=0, overload_circuit_path=path)
    client.limiter = SimpleNamespace(wait=lambda: client.overload_circuit.failed(0, overloaded=True))
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_k: pytest.fail('queued work sent during outage'))
    with pytest.raises(LLMError, match='cooling down'):
        client.complete('q')


@pytest.mark.parametrize('status', [400, 401, 403])
def test_other_statuses_are_not_misclassified_as_overload(tmp_path, monkeypatch, clock, status):
    sent = []
    def transport(request, **_):
        sent.append(1)
        raise HTTPError(request.full_url, status, 'error', {}, io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('fake', max_retries=0, overload_circuit_path=tmp_path / 'health.db')
    for _ in range(2):
        with pytest.raises(LLMError):
            client.complete('q')
    assert len(sent) == 2


def test_429_cooldown_survives_restart_key_change_and_recovers_once(tmp_path, monkeypatch, clock):
    from campusai.llm.client import LLMRateLimitError
    from campusai.llm.failures import public_provider_failure
    path = tmp_path/'health.db'
    sent = []
    def transport(request, **_):
        sent.append(1)
        if len(sent) == 1:
            raise HTTPError(request.full_url,429,'private',{'Retry-After':'120'},io.BytesIO())
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    first = GeminiClient('first', max_retries=0, overload_circuit_path=path)
    with pytest.raises(LLMRateLimitError) as failure:
        first.complete('q')
    assert public_provider_failure(failure.value) == {'error_code':'provider_rate_limited','retry_after_seconds':120}
    other = GeminiClient('second', max_retries=0, overload_circuit_path=path)
    for _ in range(20):
        with pytest.raises(LLMRateLimitError) as failure:
            other.complete('new')
        assert public_provider_failure(failure.value)['error_code'] == 'provider_rate_limited'
    assert len(sent) == 1
    clock[0] += 120
    assert other.complete('q').text == 'ok' and len(sent) == 2


def test_schema_migration_keeps_old_cooldown_and_late_signal_cannot_shorten_it(tmp_path, clock):
    import sqlite3
    path = tmp_path/'old.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE overload (endpoint TEXT PRIMARY KEY, failures INTEGER, until REAL, '
                   'probe_until REAL, generation INTEGER)')
        db.execute('INSERT INTO overload VALUES (?, 1, ?, 0, 3)', ('model', clock[0]+120))
    circuit = OverloadCircuit(path,'model')
    with sqlite3.connect(path) as db:
        # Rollback/older releases can still use the original INSERT shape.
        db.execute('INSERT INTO overload VALUES (?, 0, 0, 0, 0)', ('older-release',))
    with pytest.raises(ProviderCoolingDown) as failure:
        circuit.acquire(15)
    assert failure.value.retry_after_seconds == 120
    circuit.failed(2, overloaded=False, rate_limited=True, retry_after=600)
    circuit.failed(1, overloaded=True, retry_after=1)
    circuit.succeeded(1)
    assert circuit.remaining_seconds() == 600


@pytest.mark.parametrize('hint', ['NaN', 'Infinity', '-Infinity'])
def test_nonfinite_retry_after_does_not_break_cooldown(tmp_path, monkeypatch, clock, hint):
    from campusai.llm.client import _retry_after_seconds
    assert _retry_after_seconds(hint) is None
    def transport(request, **_):
        raise HTTPError(request.full_url,429,'busy',{'Retry-After':hint},io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen',transport)
    client = GeminiClient('fake',max_retries=0,overload_circuit_path=tmp_path/'health.db')
    with pytest.raises(LLMError) as failure:
        client.complete('q')
    assert failure.value.retry_after_seconds == 60
