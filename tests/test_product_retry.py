"""Retry503 recovery, costs and observation boundaries without network I/O."""
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from campusai.llm.client import GeminiClient, LLMError
from campusai.llm.factory import create_llm
from campusai.llm.retry import retry503
from evaluation.common.release_artifacts import sha256, write_json
from scripts.benchmarks import product_retry as policy


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr('time.time', lambda: now[0])
    monkeypatch.setattr('time.perf_counter', lambda: now[0])
    monkeypatch.setattr('time.monotonic', lambda: now[0])
    monkeypatch.setattr('time.sleep', lambda delay: now.__setitem__(0, now[0] + delay))
    return now


@pytest.mark.parametrize('first', [400, 401, 403, 408, 429, 500, 502, 504, 'timeout', 'network'])
def test_narrow_client_does_not_retry_other_failures(first, monkeypatch, clock):
    sent = []
    def transport(request, **kwargs):
        sent.append(request.data)
        if first == 'timeout':
            raise TimeoutError('synthetic')
        if first == 'network':
            raise URLError('synthetic')
        raise HTTPError(request.full_url, first, 'synthetic', {}, io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen', transport)
    with pytest.raises(LLMError):
        GeminiClient('synthetic', max_retries=1, retry_only_503=True).complete('q')
    assert len(sent) == 1 and clock[0] == 1000


@pytest.mark.parametrize('hint,delay', [('7', 30), ('NaN', None), ('bad', None)])
def test_client_503_recovers_same_payload_and_counts_wait_in_latency(tmp_path, monkeypatch, clock, hint, delay):
    config = tmp_path / 'client.json'
    write_json(config, {'llm': {'provider': 'gemini', 'model': 'gemini-3.8-flash',
        'cache_path': ':memory:', 'requests_per_minute': 0,
        'max_retries': 1, 'retry_only_503': True}})
    client = create_llm(config, {'GEMINI_API_KEY': 'synthetic'})
    sent = []
    def transport(request, **kwargs):
        sent.append(request.data)
        if len(sent) == 1:
            raise HTTPError(request.full_url, 503, 'synthetic', {'Retry-After': hint}, io.BytesIO())
        return io.BytesIO(b'{"candidates":[{"content":{"parts":[{"text":"OK"}]}}]}')
    monkeypatch.setattr('urllib.request.urlopen', transport)
    try:
        first = client.complete('q')
        second = client.complete('q')
        assert sent[0] == sent[1] and len(sent) == 2
        assert first.text == 'OK' and second.cached
        assert 30000 <= first.latency_ms <= 60000
        if delay is not None:
            assert first.latency_ms == delay * 1000
    finally:
        client.close()


def test_product_profile_stops_503_then_recovers_after_cooldown(monkeypatch, tmp_path, clock):
    from campusai.llm.factory import _read_config

    config = _read_config(Path('configs/product_llm.yaml'))['llm']
    assert config['timeout_seconds'] == 15
    assert config['max_retries'] == 0 and config['retry_only_503'] is True
    assert config['overload_circuit_path']
    assert config['retry_min_wait_seconds'] == 1 and config['retry_max_wait_seconds'] == 3
    assert config['generation_config']['maxOutputTokens'] == 1024

    config['overload_circuit_path'] = str(tmp_path / 'health.sqlite3')
    config_path = tmp_path / 'product.json'
    write_json(config_path, {'llm': config})
    client = create_llm(config_path, {'GEMINI_API_KEY': 'synthetic'})
    calls, waits, timeouts = [], [], []
    payload = {'candidates': [{'content': {'parts': [{'text': '{"answer":"ok"}'}]}}]}

    def transport(request, timeout):
        calls.append(json.loads(request.data))
        timeouts.append(timeout)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 503, 'busy', {}, io.BytesIO())
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr('urllib.request.urlopen', transport)
    monkeypatch.setattr('campusai.llm.retry.time.sleep', waits.append)
    try:
        with pytest.raises(LLMError):
            client.generate_json('short prompt')
        with pytest.raises(LLMError, match='cooling down'):
            client.generate_json('another prompt')
        assert len(calls) == 1 and waits == []
        clock[0] += 61
        assert client.generate_json('short prompt', schema={'type': 'object', 'properties': {
            'answer': {'type': 'string'}}}) == {'answer': 'ok'}
        assert len(calls) == 2 and timeouts == [15, 15]
        assert waits == []
        assert all(body['generationConfig']['maxOutputTokens'] == 1024 for body in calls)
    finally:
        client.close()


def test_product_retry_does_not_violate_long_provider_retry_after(monkeypatch, tmp_path):
    from campusai.llm.factory import _read_config
    config = _read_config('configs/product_llm.yaml')
    config['llm']['overload_circuit_path'] = str(tmp_path / 'health.sqlite3')
    path = tmp_path / 'product.json'
    write_json(path, config)
    client = create_llm(path, {'GEMINI_API_KEY': 'synthetic'})
    calls, waits = [], []

    def transport(request, timeout):
        calls.append(timeout)
        raise HTTPError(request.full_url, 503, 'busy', {'Retry-After': '30'}, io.BytesIO())

    monkeypatch.setattr('urllib.request.urlopen', transport)
    monkeypatch.setattr('campusai.llm.retry.time.sleep', waits.append)
    try:
        with pytest.raises(LLMError):
            client.complete('short prompt')
        assert calls == [15] and waits == []
    finally:
        client.close()


def test_second_503_stops_and_retains_both_attempts(clock):
    events, reservations = [], []
    def unavailable(request, **kwargs):
        raise HTTPError(request.full_url, 503, 'synthetic', {}, io.BytesIO())
    with pytest.raises(HTTPError):
        retry503(Request('https://offline.invalid', data=b'{}'), unavailable,
                 timeout=60, attempts=events, before_retry=lambda: reservations.append(1))
    assert len(events) == 2 and len(reservations) == 1
    assert all(e['http_status'] == 503 and e['status'] == 'failed' for e in events)
    assert events[0]['retry_wait_ms'] >= 30000
    assert events[1]['provider_start'] - events[0]['provider_start'] >= 30


def test_closed_http_error_body_cannot_become_invalid_input(monkeypatch, clock):
    error = HTTPError('https://offline.invalid', 503, 'synthetic', {}, io.BytesIO())
    def transport(*args, **kwargs):
        raise error
    monkeypatch.setattr('urllib.request.urlopen', transport)
    from campusai.llm.client import LLMProviderError
    with pytest.raises(LLMProviderError, match='HTTP 503'):
        GeminiClient('synthetic', max_retries=1, retry_only_503=True).complete('q')


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(policy, 'ROOT', tmp_path)
    identity = {'source_sha256': 'test'}
    monkeypatch.setattr('evaluation.common.release_artifacts.source_identity', lambda _: identity)
    budget = {'path': str(tmp_path / 'budget.json'), 'bundle_id': 'test', 'max_extra_attempts': 3}
    bindings = []
    for index, count in enumerate((68, 54, 2)):
        body = {'contents': [{'parts': [{'text': 'q'}]}]}
        p = tmp_path / f'packet-{index}.json'
        write_json(p, {'max_provider_calls': count, 'prompt_chars': count, 'provider_bodies': [body] * count,
            'max_retries': 1,
            'retry_only_http_status': 503, 'llm_config': {'max_retries': 1, 'retry_only_503': True,
                'generation_config': {'maxOutputTokens': 4096}},
            'retry_budget': budget})
        bindings.append({'path': str(p), 'sha256': sha256(p)})
    manifest = tmp_path / 'manifest.json'
    # 124 planned prompts plus three retries of a one-character prompt.
    write_json(manifest, {'source_identity': identity, 'retry_budget': budget, 'packets': bindings,
        'maximum_external_post_requests': 127, 'maximum_new_prompt_characters': 127,
        'maximum_total_output_tokens': 127 * 4096, 'max_retries': 1})
    policy.initialize(manifest, sha256(manifest))
    return manifest, bindings


def test_shared_budget_spans_packets_and_new_worker_instances(bundle, clock):
    manifest, packets = bundle
    body = {'contents': [{'parts': [{'text': 'q'}]}]}
    for packet in packets:
        first = policy.Budget(packet['path'], packet['sha256'])
        first.before_attempt('one', body, False)
        first.reserve_retry('one')
        # Recreate the object as a fresh worker would; memory is not the budget.
        policy.Budget(packet['path'], packet['sha256']).before_attempt('one', body, True)
    last = policy.Budget(packets[-1]['path'], packets[-1]['sha256'])
    last.before_attempt('two', body, False)
    with pytest.raises(RuntimeError, match='exhausted'):
        last.reserve_retry('two')
    state = policy.read(last.path)
    assert len(state['attempts']) == 7 and len(state['retry_reservations']) == 3
    starts = [r['provider_start'] for r in state['attempts']]
    assert all(b - a >= 30 for a, b in zip(starts, starts[1:]))
    last.stop('provider503')
    with pytest.raises(ValueError, match='stopped'):
        policy.Budget(packets[0]['path'], packets[0]['sha256'])
    with pytest.raises(ValueError, match='already consumed'):
        policy.initialize(manifest, sha256(manifest))


def test_single_packet_budget_caps_retries_to_one_global_503(tmp_path, monkeypatch, clock):
    monkeypatch.setattr(policy, 'ROOT', tmp_path)
    identity = {'source_sha256': 'single-packet-test'}
    monkeypatch.setattr('evaluation.common.release_artifacts.source_identity', lambda _: identity)
    budget = {'path': str(tmp_path / 'single-budget.json'), 'bundle_id': 'single', 'max_extra_attempts': 1}
    body = {'contents': [{'parts': [{'text': 'q'}]}]}
    packet = tmp_path / 'single-packet.json'
    write_json(packet, {'max_provider_calls': 2, 'prompt_chars': 2, 'provider_bodies': [body, body],
        'max_retries': 1, 'retry_only_http_status': 503,
        'llm_config': {'max_retries': 1, 'retry_only_503': True,
            'generation_config': {'maxOutputTokens': 1024}}, 'retry_budget': budget})
    manifest = tmp_path / 'single-manifest.json'
    write_json(manifest, {'source_identity': identity, 'retry_budget': budget,
        'packets': [{'path': str(packet), 'sha256': sha256(packet)}], 'max_retries': 1,
        'expected_packet_count': 1, 'maximum_external_post_requests': 3,
        'maximum_new_prompt_characters': 3, 'maximum_total_output_tokens': 3 * 1024})
    policy.initialize(manifest, sha256(manifest))
    assert policy.read(budget['path'])['max_total_output_tokens'] == 3072
    run = policy.Budget(packet, sha256(packet))
    run.before_attempt('first', body, False)
    run.reserve_retry('first')
    policy.Budget(packet, sha256(packet)).before_attempt('first', body, True)
    run.before_attempt('second', body, False)
    with pytest.raises(RuntimeError, match='exhausted'):
        run.reserve_retry('second')
    state = policy.read(budget['path'])
    assert len(state['retry_reservations']) == 1
    assert len(state['attempts']) == 3
    assert all(b['provider_start'] - a['provider_start'] >= 30
               for a, b in zip(state['attempts'], state['attempts'][1:]))
    Path(budget['path']).unlink()
    overbudget = policy.read(manifest)
    overbudget['maximum_total_output_tokens'] = 3 * 4096
    write_json(manifest, overbudget)
    with pytest.raises(ValueError, match='budget changed'):
        policy.initialize(manifest, sha256(manifest))


def test_manifest_must_budget_the_largest_retry_prompt(bundle):
    manifest, packets = bundle
    path = Path(policy.read(manifest)['retry_budget']['path'])
    path.unlink()
    payload = policy.read(manifest)
    payload['maximum_new_prompt_characters'] -= 1
    write_json(manifest, payload)
    with pytest.raises(ValueError, match='budget changed'):
        policy.initialize(manifest, sha256(manifest))


def test_free_tier_primary_bundle_claims_one_shard_per_pacific_day_and_pins_model(tmp_path, monkeypatch, clock):
    from datetime import datetime
    # Use the controlled clock for calendar reads as well as time.time(). The
    # real 23:30-00:00 Pacific guard must not make this offline test time-flaky.
    clock[0] = datetime(2026, 1, 15, 12, tzinfo=policy.PACIFIC).timestamp()
    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(clock[0], tz)
    monkeypatch.setattr(policy, 'datetime', ControlledDateTime)
    monkeypatch.setattr(policy, 'ROOT', tmp_path)
    identity = {'source_sha256': 'free-tier-shards'}
    monkeypatch.setattr('evaluation.common.release_artifacts.source_identity', lambda _: identity)
    budget = {'path': str(tmp_path / 'shards-budget.json'), 'bundle_id': 'shards', 'max_extra_attempts': 1}
    body = {'contents': [{'parts': [{'text': 'q'}]}]}
    packet_bindings = []
    for index, count in enumerate((14, 14, 14, 14, 12)):
        packet = tmp_path / f'shard-{index}.json'
        write_json(packet, {'source_identity': identity, 'max_provider_calls': count,
            'prompt_chars': count, 'provider_bodies': [body] * count, 'max_retries': 1,
            'retry_only_http_status': 503, 'llm_config': {'max_retries': 1, 'retry_only_503': True,
                'generation_config': {'maxOutputTokens': 1024}}, 'retry_budget': budget,
            'output_path': str(tmp_path / f'out-{index}.json')})
        packet_bindings.append({'path': str(packet), 'sha256': sha256(packet)})
    manifest = tmp_path / 'shards-manifest.json'
    write_json(manifest, {'source_identity': identity, 'retry_budget': budget,
        'packets': packet_bindings, 'max_retries': 1, 'expected_packet_count': 5,
        'maximum_external_post_requests': 69, 'maximum_new_prompt_characters': 69,
        'maximum_total_output_tokens': 69 * 1024,
        'quota_window_policy': {'provider': 'gemini_free_tier', 'reset_timezone': 'America/Los_Angeles',
            'max_shards_per_pacific_date': 1, 'max_planned_posts_per_shard': 14,
            'max_attempts_per_shard_per_day': 15, 'model_version_must_remain_constant': True}})
    policy.initialize(manifest, sha256(manifest))

    first = policy.Budget(packet_bindings[0]['path'], packet_bindings[0]['sha256'])
    first.claim_quota_window()
    first.before_attempt('qid', body, False)
    first.record_model_version('gemini-3.8-flash-001')
    same_day = policy.Budget(packet_bindings[1]['path'], packet_bindings[1]['sha256'])
    with pytest.raises(RuntimeError, match='daily request window already used'):
        same_day.claim_quota_window()

    next_day = policy.Budget(packet_bindings[1]['path'], packet_bindings[1]['sha256'])
    with pytest.raises(ValueError, match='model version changed'):
        next_day.record_model_version('gemini-3.8-flash-002')
    assert policy.read(budget['path'])['provider_model_version'] == 'gemini-3.8-flash-001'
    clock[0] += 24 * 60 * 60
    next_day.claim_quota_window()
    clock[0] = datetime(2026, 1, 16, 23, 45, tzinfo=policy.PACIFIC).timestamp()
    near_reset = policy.Budget(packet_bindings[2]['path'], packet_bindings[2]['sha256'])
    with pytest.raises(RuntimeError, match='next Pacific quota window'):
        near_reset.claim_quota_window()


def test_primary_schedule_counts_only_actual_provider_posts():
    body = {'contents': [{'parts': [{'text': 'one'}]}]}
    packet = {'schedule': [{'arm': 'baseline', 'qid': 'q'}, {'arm': 'current', 'qid': 'q'}],
        'cases': {'baseline': {'q': {'provider_body': None}},
                  'current': {'q': {'provider_body': body}}},
        'max_provider_calls': 1, 'prompt_chars': 3}
    assert policy.packet_usage(packet) == (1, 3, [3])


def test_denied_retry_budget_never_sends_second_attempt(clock):
    sent, events = [], []
    def unavailable(request, **kwargs):
        sent.append(1)
        raise HTTPError(request.full_url, 503, 'synthetic', {}, io.BytesIO())
    def deny():
        raise RuntimeError('budget exhausted')
    with pytest.raises(RuntimeError, match='budget exhausted'):
        retry503(Request('https://offline.invalid', data=b'{}'), unavailable,
                 timeout=60, attempts=events, before_retry=deny)
    assert len(sent) == len(events) == 1 and clock[0] == 1000


def test_budget_rejects_unreserved_replay_or_concurrent_writer(bundle, clock):
    _, packets = bundle
    packet = packets[0]
    budget = policy.Budget(packet['path'], packet['sha256'])
    body = {'contents': [{'parts': [{'text': 'q'}]}]}
    with pytest.raises(RuntimeError, match='unreserved'):
        budget.before_attempt('q', body, True)
    budget.before_attempt('q', body, False)
    with pytest.raises(RuntimeError, match='repeated'):
        budget.before_attempt('q', body, False)
    lock = budget.path.with_suffix('.json.lock')
    lock.touch()
    with pytest.raises(FileExistsError):
        budget.reserve_retry('q')
    assert lock.exists()  # Never remove another process's lock.


def test_archived_budget_cannot_reset_allowance(bundle, monkeypatch):
    manifest, packets = bundle
    path = Path(policy.read(manifest)['retry_budget']['path'])
    path.unlink()
    key = path.relative_to(policy.ROOT).as_posix()
    monkeypatch.setattr('evaluation.common.artifact_store.entries', lambda: {key: {}})
    with pytest.raises(ValueError, match='archived budget'):
        policy.initialize(manifest, sha256(manifest))


@pytest.mark.parametrize('value', [2, True, -1])
def test_invalid_narrow_retry_limits_fail_closed(value):
    with pytest.raises(ValueError):
        retry503(None, None, timeout=60, max_retries=value)


def test_invalid_factory_retry_policy_precedes_cache_creation(tmp_path):
    config = tmp_path / 'invalid.json'
    write_json(config, {'llm': {'provider': 'gemini', 'model': 'm',
                              'max_retries': 2, 'retry_only_503': True}})
    with pytest.raises(ValueError, match='at most one'):
        create_llm(config, {'GEMINI_API_KEY': 'synthetic'})
