"""Independent-project admission: real SQLite, deterministic HTTP and no retries."""
import io
import json
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.client import GeminiClient, LLMError, LLMRateLimitError
from campusai.llm.factory import create_llm
from campusai.llm.project_router import GeminiProjectRouter
from campusai.llm.quota import QuotaGovernor, QuotaPolicy


MODEL = 'gemini-3.5-flash-lite'
ENDPOINT = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
CREDENTIALS = [('GEMINI_API_KEY', 'fake-first-secret'),
               ('GEMINI_API_KEY_2', 'fake-second-secret'),
               ('GEMINI_API_KEY_3', 'fake-third-secret')]
RESPONSE = b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}'


def build(tmp_path, **kwargs):
    health = tmp_path / 'health.db'
    router = GeminiProjectRouter(CREDENTIALS, health_path=health, model=MODEL)
    governor = QuotaGovernor(tmp_path / 'quota.db', 'existing-owner-budget',
        QuotaPolicy(0, requests_per_day=kwargs.pop('daily', 20)), max_wait_seconds=0)
    return GeminiClient(CREDENTIALS[0][1], model=MODEL, max_retries=0,
        generation_config={'maxOutputTokens': 32}, quota_governor=governor,
        overload_circuit_path=health, project_router=router, **kwargs)


def transport(monkeypatch, errors=()):
    calls = []
    def send(request, **_):
        calls.append(request)
        if len(calls) <= len(errors) and errors[len(calls)-1]:
            raise HTTPError(request.full_url, errors[len(calls)-1], 'unavailable',
                            {'Retry-After': '120'}, io.BytesIO(b'{}'))
        return io.BytesIO(RESPONSE)
    monkeypatch.setattr('urllib.request.urlopen', send)
    return calls


def key(request):
    return dict((k.lower(), v) for k, v in request.header_items())['x-goog-api-key']


def test_three_projects_change_only_credential_and_preserve_shared_daily_budget(tmp_path, monkeypatch):
    calls = transport(monkeypatch)
    client = build(tmp_path, daily=3)
    for _ in range(3):
        assert client.complete('same benign question').text == 'ok'
    with pytest.raises(LLMRateLimitError, match='budget exhausted'):
        client.complete('fourth')
    assert [key(r) for r in calls] == [value for _, value in CREDENTIALS]
    assert len({r.data for r in calls}) == len({r.full_url for r in calls}) == 1
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 3
    state = (tmp_path/'health.db').read_bytes() + (tmp_path/'quota.db').read_bytes()
    assert all(value.encode() not in state for _, value in CREDENTIALS)


def test_cache_hit_does_not_select_another_key_or_spend_quota(tmp_path, monkeypatch):
    calls = transport(monkeypatch)
    client = build(tmp_path, cache=SQLiteLLMCache(':memory:'))
    try:
        client.complete('one')
        assert client.complete('one').cached
        client.complete('two')
        assert [key(r) for r in calls] == [value for _, value in CREDENTIALS[:2]]
        assert client.quota_governor.snapshot()['reserved_attempts_today'] == 2
    finally:
        client.close()


def test_streaming_uses_one_project_per_call_and_preserves_genuine_token_capture(tmp_path, monkeypatch):
    from campusai.llm.streaming import capture_stream
    calls = []
    event = {'candidates': [{'index': 0, 'content': {'parts': [{'text': 'ok'}]}, 'finishReason': 'STOP'}]}
    def send(request, **_):
        calls.append(request)
        return io.BytesIO(b'data: ' + json.dumps(event).encode() + b'\n\n')
    monkeypatch.setattr('urllib.request.urlopen', send)
    client = build(tmp_path)
    for _ in range(3):
        with capture_stream() as stream:
            assert client.complete('benign streaming question').text == 'ok'
        row = stream.summary()['calls'][0]
        assert row['status'] == 'complete' and row['first_text_delta_ms'] is not None
    assert [key(r) for r in calls] == [value for _, value in CREDENTIALS]
    assert all(r.full_url == ENDPOINT.replace(':generateContent', ':streamGenerateContent?alt=sse') for r in calls)


def test_429_is_project_local_persistent_and_never_retries_failed_call(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [429])
    client = build(tmp_path)
    with pytest.raises(LLMRateLimitError):
        client.complete('first')
    assert len(calls) == 1
    # Restart has a fresh cursor, but the exhausted project's cooldown survives.
    restarted = build(tmp_path)
    assert restarted.complete('second').text == 'ok'
    assert [key(r) for r in calls] == [value for _, value in CREDENTIALS[:2]]
    assert restarted.quota_governor.snapshot()['reserved_attempts_today'] == 2


def test_project_daily_hint_does_not_erase_or_replace_existing_shared_accounting(tmp_path, monkeypatch):
    calls = []
    detail = {'error': {'details': [{
        '@type': 'type.googleapis.com/google.rpc.QuotaFailure',
        'violations': [{
            'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier',
            'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests',
            'quotaDimensions': {'model': MODEL, 'location': 'global'}, 'quotaValue': '1'}]}]}}
    def send(request, **_):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 429, 'quota', {},
                            io.BytesIO(json.dumps(detail).encode()))
        return io.BytesIO(RESPONSE)
    monkeypatch.setattr('urllib.request.urlopen', send)
    client = build(tmp_path)
    # Preserve historical provider observations, even though they are now a
    # conservative aggregate bound. One project's new limit is not global.
    client.quota_governor.observe([{'kind': 'requests_per_day', 'value': 10}])
    before = client.quota_governor.snapshot()
    with pytest.raises(LLMRateLimitError):
        client.complete('exhausted project')
    assert client.complete('independent project').text == 'ok'
    after = client.quota_governor.snapshot()
    assert after['observed_provider_limits'] == before['observed_provider_limits']
    assert after['reserved_attempts_today'] == 2
    assert len(calls) == 2


def test_all_projects_exhausted_fail_before_transport_and_still_charge_failures(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [429, 429, 429])
    client = build(tmp_path)
    for number in range(3):
        with pytest.raises(LLMRateLimitError):
            client.complete(str(number))
    with pytest.raises(LLMRateLimitError, match='cooling down'):
        client.complete('all exhausted')
    assert len(calls) == 3
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 3


def test_503_still_blocks_all_keys_and_single_key_clients(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [503])
    client = build(tmp_path)
    with pytest.raises(LLMError):
        client.complete('first')
    with pytest.raises(LLMError, match='cooling down'):
        client.complete('second')
    single = GeminiClient('different-key', model=MODEL, max_retries=0,
                          overload_circuit_path=tmp_path / 'health.db')
    with pytest.raises(LLMError, match='cooling down'):
        single.complete('third')
    assert len(calls) == 1


def test_count_tokens_project_cooldown_does_not_poison_inference(tmp_path, monkeypatch):
    now = [2_000_000_000.0]
    monkeypatch.setattr('time.time', lambda: now[0])
    calls = transport(monkeypatch, [429, 429, 429])
    client = build(tmp_path, allow_pdf_scope=True)
    for _ in range(3):
        request = Request(ENDPOINT.replace(':generateContent', ':countTokens'),
                          data=b'{"contents":[{"parts":[{"text":"hello"}]}]}', method='POST')
        with pytest.raises(LLMRateLimitError):
            client._send(request, token_budget=(10, 0))
        now[0] += 1  # Respect countTokens' existing 3,000 RPM admission.
    assert client.complete('normal question').text == 'ok'
    assert len(calls) == 4
    assert client.count_tokens_quota_governor.snapshot()['reserved_attempts_today'] == 3
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 1


@pytest.mark.parametrize('url', [
    'https://proxy.invalid/v1beta/models/gemini-3.5-flash-lite:generateContent',
    ENDPOINT.replace('https:', 'http:'), ENDPOINT + '?key=',
    ENDPOINT + '?alt=sse&key=bad', ENDPOINT + '#secret',
    ENDPOINT.replace(MODEL, 'gemini-other'),
    ENDPOINT.replace('https://', 'https://user:pass@'),
    ENDPOINT.replace('.com/', '.com:444/'),
])
def test_credentials_never_routed_to_unapproved_origin_or_query(tmp_path, url):
    router = GeminiProjectRouter(CREDENTIALS, health_path=tmp_path/'health.db', model=MODEL)
    with pytest.raises(ValueError):
        router.route(Request(url, data=b'{}'), 10)


def config(tmp_path):
    return {'llm': {'provider': 'gemini', 'model': MODEL, 'api_key_env': 'GEMINI_API_KEY',
        'api_key_envs': [name for name, _ in CREDENTIALS], 'independent_projects': True,
        'max_retries': 0, 'requests_per_minute': 0, 'cache_path': ':memory:',
        'overload_circuit_path': str(tmp_path/'health.db'),
        'generation_config': {'maxOutputTokens': 32},
        'quota': {'state_path': str(tmp_path/'quota.db'), 'scope': 'existing-owner-budget'}}}


def test_factory_opt_in_and_default_single_key_unchanged(tmp_path, monkeypatch):
    calls = transport(monkeypatch)
    document = config(tmp_path)
    path = tmp_path/'config.json'
    path.write_text(json.dumps(document))
    env = dict(CREDENTIALS)
    client = create_llm(path, environ=env)
    assert 'secret' not in repr(client.project_router)
    assert client.complete('first').text == 'ok'
    assert client.complete('second').text == 'ok'
    client.close()
    del document['llm']['api_key_envs'], document['llm']['independent_projects']
    path.write_text(json.dumps(document))
    client = create_llm(path, environ=env)
    assert client.project_router is None
    assert client.complete('third').text == 'ok'
    client.close()
    assert [key(r) for r in calls] == [CREDENTIALS[0][1], CREDENTIALS[1][1], CREDENTIALS[0][1]]


@pytest.mark.parametrize('change', [
    {'independent_projects': False}, {'independent_projects': 'true'},
    {'api_key_envs': None},
    {'api_key_envs': ['GEMINI_API_KEY', 'GEMINI_API_KEY']},
    {'api_key_envs': ['GEMINI_API_KEY_2', 'GEMINI_API_KEY']},
    {'api_key_envs': ['GEMINI_API_KEY', 'MISSING_KEY']},
    {'max_retries': 1}, {'quota': None}, {'overload_circuit_path': None},
    {'endpoint': 'https://proxy.invalid'}, {'provider': 'openai'},
])
def test_invalid_pool_fails_before_creating_budget_or_cache(tmp_path, change):
    document = config(tmp_path)
    document['llm'].update(change)
    path = tmp_path/'config.json'
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        create_llm(path, environ=dict(CREDENTIALS))
    assert not (tmp_path/'health.db').exists()
    assert not (tmp_path/'quota.db').exists()


def test_duplicate_secrets_and_partial_bad_pool_never_create_health_state(tmp_path):
    path = tmp_path/'health.db'
    for entries in ([CREDENTIALS[0], ('OTHER_ENV', CREDENTIALS[0][1])],
                    [CREDENTIALS[0], ('bad-env', 'other-secret')],
                    [CREDENTIALS[0], 'invalid-pair']):
        with pytest.raises(ValueError):
            GeminiProjectRouter(entries, health_path=path, model=MODEL)
        assert not path.exists()


def test_null_pool_without_consent_is_rejected_instead_of_silently_single_key(tmp_path):
    document = config(tmp_path)
    document['llm']['api_key_envs'] = None
    del document['llm']['independent_projects']
    path = tmp_path/'config.json'
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        create_llm(path, environ=dict(CREDENTIALS))
    assert not (tmp_path/'quota.db').exists()


def test_quota_failover_answers_same_question_and_charges_each_attempt(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [429, 429])
    client = build(tmp_path, project_quota_failover=True)
    assert client.complete('same question').text == 'ok'
    assert [key(r) for r in calls] == [v for _, v in CREDENTIALS]
    assert len({r.data for r in calls}) == 1
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 3
    # Two exhausted projects remain unavailable to subsequent questions.
    assert client.complete('next question').text == 'ok'
    assert key(calls[-1]) == CREDENTIALS[2][1]


def test_quota_failover_stops_after_each_project_was_tried_once(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [429, 429, 429])
    client = build(tmp_path, project_quota_failover=True)
    with pytest.raises(LLMRateLimitError):
        client.complete('question')
    with pytest.raises(LLMRateLimitError):
        client.complete('later question')
    assert len(calls) == 3
    assert len({key(r) for r in calls}) == 3
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 3


@pytest.mark.parametrize('status', [401, 403, 503, 'timeout'])
def test_quota_failover_does_not_repeat_other_provider_errors(tmp_path, monkeypatch, status):
    calls = []
    def send(request, **_):
        calls.append(request)
        if status == 'timeout':
            raise TimeoutError()
        raise HTTPError(request.full_url, status, 'unavailable', {}, io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen', send)
    client = build(tmp_path, project_quota_failover=True)
    with pytest.raises(LLMError):
        client.complete('question')
    assert len(calls) == 1


def test_local_budget_rejection_never_triggers_project_failover(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [429])
    client = build(tmp_path, daily=1, project_quota_failover=True)
    with pytest.raises(LLMRateLimitError):
        client.complete('question')
    assert len(calls) == 1
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 1


def test_thousand_calls_have_no_hundred_question_ceiling(tmp_path, monkeypatch):
    from collections import Counter
    calls = transport(monkeypatch)
    client = build(tmp_path, daily=1000, project_quota_failover=True)
    for i in range(1000):
        assert client.complete(f'question {i}').text == 'ok'
    assert sorted(Counter(key(r) for r in calls).values()) == [333, 333, 334]
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 1000


def test_continue_until_all_independent_projects_are_exhausted(tmp_path, monkeypatch):
    from collections import Counter
    budgets = {secret: limit for (_,secret),limit in zip(CREDENTIALS,[2,3,4])}
    used, attempts = Counter(), Counter()
    def send(request, **_):
        secret = key(request)
        attempts[secret] += 1
        if used[secret] >= budgets[secret]:
            raise HTTPError(request.full_url,429,'quota',{'Retry-After':'120'},io.BytesIO())
        used[secret] += 1
        return io.BytesIO(RESPONSE)
    monkeypatch.setattr('urllib.request.urlopen',send)
    client = build(tmp_path, project_quota_failover=True)
    for i in range(sum(budgets.values())):
        assert client.complete(f'question {i}').text == 'ok'
    assert dict(used) == budgets
    with pytest.raises(LLMRateLimitError):
        client.complete('all projects exhausted')
    charged = sum(attempts.values())
    assert charged == 12  # Nine successes and one 429 from each project.
    with pytest.raises(LLMRateLimitError):
        client.complete('during cooldown')
    assert sum(attempts.values()) == charged
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == charged


def test_factory_requires_explicit_failover_opt_in(tmp_path):
    document = config(tmp_path)
    document['llm']['project_quota_failover'] = True
    path = tmp_path/'config.json'
    path.write_text(json.dumps(document))
    client = create_llm(path, environ=dict(CREDENTIALS))
    assert client.project_quota_failover is True
    client.close()


def test_streaming_quota_failover_preserves_failed_attempt_and_real_deltas(tmp_path, monkeypatch):
    from campusai.llm.streaming import capture_stream
    calls = []
    def send(request, **_):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(request.full_url,429,'quota',{'Retry-After':'120'},io.BytesIO())
        event = {'candidates':[{'index':0,'content':{'parts':[{'text':'ok'}]},'finishReason':'STOP'}]}
        return io.BytesIO(b'data: '+json.dumps(event).encode()+b'\n\n')
    monkeypatch.setattr('urllib.request.urlopen',send)
    client = build(tmp_path, project_quota_failover=True)
    with capture_stream() as stream:
        assert client.complete('question').text == 'ok'
    assert [key(r) for r in calls] == [v for _,v in CREDENTIALS[:2]]
    assert [r['status'] for r in stream.summary()['calls']] == ['incomplete','complete']
    assert stream.summary()['calls'][1]['first_text_delta_ms'] is not None
    assert client.quota_governor.snapshot()['reserved_attempts_today'] == 2
