"""Real wire framing and admission contracts; no external model calls."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
import sqlite3
import threading
import urllib.error

import pytest

from campusai.llm.client import GeminiClient, LLMProviderError, LLMResponseError, LLMRateLimitError
from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.quota import QuotaGovernor, QuotaPolicy
from campusai.llm.streaming import capture_stream, StreamCancelled, current_stream, stream_endpoint


def event(text=None, *, finish=None, **extra):
    c = {'index': 0}
    if text is not None: c['content'] = {'parts': [{'text': text}]}
    if finish: c['finishReason'] = finish
    return {'candidates': [c], **extra}


def frames(*values):
    return b''.join(b'data: ' + json.dumps(v, ensure_ascii=False).encode('utf8') + b'\n\n' for v in values)


class Fragmented(io.BytesIO):
    def read1(self, size=-1): return self.read(min(3, size))


def test_stream_preserves_json_request_and_assembles_fragmented_final_text(monkeypatch, tmp_path):
    calls = []
    wire = (b'\xef\xbb\xbf: keepalive\r\n\r\n' + frames(
        {'candidates': [{'content': {'parts': [{'text': 'private thought', 'thought': True}]}}]},
        event('{"answer":"Tiếng Việt'), event(' tự nhiên"}', finish='STOP',
            usageMetadata={'totalTokenCount': 18}, modelVersion='exact-model')))
    def transport(request, timeout):
        calls.append(request)
        assert timeout == 60
        return Fragmented(wire)
    monkeypatch.setattr('urllib.request.urlopen', transport)
    cache = SQLiteLLMCache(str(tmp_path/'cache.sqlite'))
    client = GeminiClient('fixture-key', model='fixture-model', cache=cache, max_retries=0)
    notifications = []
    with capture_stream(notifications.append) as capture:
        result = client.generate_json('fixture prompt', schema={'type':'object','required':['answer']})
    assert result == {'answer': 'Tiếng Việt tự nhiên'}
    assert calls[0].full_url.endswith(':streamGenerateContent?alt=sse')
    assert calls[0].get_header('X-goog-api-key') == 'fixture-key'
    assert json.loads(calls[0].data) == client.prepare_json_request('fixture prompt', schema={'type':'object','required':['answer']})
    assert notifications == [{'type':'progress','phase':'generating'}, {'type':'progress','phase':'verifying'}]
    record = capture.summary()['calls'][0]
    assert record['first_text_delta_ms'] >= 0 and record['request_to_first_text_ms'] >= record['first_text_delta_ms']
    assert 0 <= record['http_headers_ms'] <= record['first_text_delta_ms']
    assert record['status'] == 'complete' and record['text_characters'] == len('{"answer":"Tiếng Việt tự nhiên"}')
    assert 'private thought' not in json.dumps(capture.summary())
    assert current_stream() is None
    cache.close()


@pytest.mark.parametrize('wire', [
    frames(event('partial')),  # no terminal marker
    frames(event('partial', finish='MAX_TOKENS')),
    frames(event('partial', finish='SAFETY')),
    frames(event('complete', finish='STOP'),event('extra')),
    frames(event('complete', finish='STOP'),event('',finish='STOP')),
    b'data: {not-json}\n\n', b'data: []\n\n', b'data: {"a":1}',
    frames({'promptFeedback': {'blockReason':'SAFETY'}}),
    frames({'promptFeedback': None}), frames({'candidates': None}),
    frames({'candidates': [{'content': None}]}),
    frames({'candidates': [{'content': {'parts': 9}}]}),
    frames({'candidates': [{'index': True}]}),
    frames({'candidates': [{'content': {'parts': [{'text':'hidden','thought':1}]}}]}),
    frames(event('a',modelVersion='one'),event('b',modelVersion=None),event('c',finish='STOP',modelVersion='two')),
    frames(event('a', modelVersion='one'), event('b',finish='STOP',modelVersion='two')),
])
def test_incomplete_or_malformed_stream_is_not_published_or_cached(wire, monkeypatch, tmp_path):
    monkeypatch.setattr('urllib.request.urlopen',lambda *_a, **_kw: Fragmented(wire))
    client = GeminiClient('fixture-key', cache=SQLiteLLMCache(str(tmp_path/'cache.sqlite')), max_retries=0)
    with capture_stream(), pytest.raises(LLMResponseError): client.complete('private fixture')
    # Failed/quarantined output must never become a provider-cache success.
    with sqlite3.connect(client.cache.path) as db:
        assert db.execute('SELECT COUNT(*) FROM responses').fetchone()[0] == 0
    client.close()


def test_stream_limits_and_multiline_sse(monkeypatch):
    from campusai.llm import streaming
    wire = b'data: {"candidates":\ndata: [{"content":{"parts":[{"text":"ok"}]},"finishReason":"STOP"}]}\n\n'
    monkeypatch.setattr('urllib.request.urlopen', lambda *_a, **_kw: Fragmented(wire))
    client = GeminiClient('fixture-key', max_retries=0)
    with capture_stream(): assert client.complete('q').text == 'ok'
    monkeypatch.setattr(streaming,'MAX_STREAM_BYTES',16)
    with capture_stream(), pytest.raises(LLMResponseError,match='size limit'): client.complete('q')


def test_stream_http_failure_keeps_quota_and_cooldown_without_retry(tmp_path, monkeypatch):
    posts = []
    def transport(request, **_kwargs):
        posts.append(request)
        raise urllib.error.HTTPError(request.full_url,503,'busy',{'Retry-After':'60'},io.BytesIO(b'{}'))
    monkeypatch.setattr('urllib.request.urlopen',transport)
    governor = QuotaGovernor(tmp_path/'quota.sqlite','fixture-project',QuotaPolicy(100,requests_per_day=50),max_wait_seconds=0)
    client = GeminiClient('fixture-key', max_retries=0, quota_governor=governor,
        generation_config={'maxOutputTokens':100},overload_circuit_path=str(tmp_path/'health.sqlite'))
    with capture_stream(), pytest.raises(LLMProviderError): client.complete('q')
    with capture_stream(), pytest.raises(LLMProviderError): client.complete('q')
    assert len(posts) == 1 and client.overload_circuit.remaining_seconds() > 0
    assert governor.snapshot()['reserved_attempts_today'] == 1


def test_consumer_cancellation_closes_wire_and_does_not_cache_or_retry(monkeypatch, tmp_path):
    response = Fragmented(frames(event('part'),event('rest',finish='STOP')))
    calls=[];stopped=threading.Event()
    def transport(*_a, **_kw): calls.append(True);return response
    monkeypatch.setattr('urllib.request.urlopen',transport)
    client=GeminiClient('fixture-key',max_retries=3,cache=SQLiteLLMCache(str(tmp_path/'cache.sqlite')))
    with capture_stream(lambda _e:stopped.set(),stopped.is_set), pytest.raises(StreamCancelled): client.complete('q')
    assert response.closed and len(calls)==1
    client.close()


def test_stream_context_is_thread_local_and_endpoint_never_contains_credentials():
    assert stream_endpoint('https://example.test/model:generateContent?key=hidden&alt=json&region=x') == 'https://example.test/model:streamGenerateContent?region=x&alt=sse'
    assert stream_endpoint('https://example.test/chat/completions') is None
    with capture_stream() as capture:
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(current_stream).result() is None
        assert current_stream() is capture


def test_cached_response_is_not_falsely_counted_as_a_stream_delta(tmp_path,monkeypatch):
    posts=[]
    def transport(*_a, **_kw):
        posts.append(True)
        return io.BytesIO(json.dumps(event('cached value',finish='STOP')).encode())
    monkeypatch.setattr('urllib.request.urlopen',transport)
    client=GeminiClient('fixture-key',max_retries=0,cache=SQLiteLLMCache(str(tmp_path/'cache.sqlite')))
    assert client.complete('q').text=='cached value'
    seen=[]
    with capture_stream(seen.append) as capture: result=client.complete('q')
    assert result.cached and len(posts)==1 and seen==[] and capture.summary()['calls']==[]
    client.close()


def test_cancelled_stream_keeps_attempt_charged_but_releases_inflight_lease(tmp_path,monkeypatch):
    governor=QuotaGovernor(tmp_path/'quota.sqlite','fixture-project',QuotaPolicy(100,requests_per_day=50),max_wait_seconds=0)
    reserve=governor.reserve;leases=[];cancelled=threading.Event()
    def reserved(*args,**kw):leases.append(kw['lease_seconds']);return reserve(*args,**kw)
    monkeypatch.setattr(governor,'reserve',reserved)
    response=Fragmented(frames(event('partial'),event('rest',finish='STOP')))
    monkeypatch.setattr('urllib.request.urlopen',lambda *_a,**_kw:response)
    client=GeminiClient('fixture-key',max_retries=0,timeout=2,quota_governor=governor,
        generation_config={'maxOutputTokens':100})
    with capture_stream(lambda _e:cancelled.set(),cancelled.is_set),pytest.raises(StreamCancelled):client.complete('q')
    snapshot=governor.snapshot()
    assert leases==[9] and snapshot['reserved_attempts_today']==1 and snapshot['in_flight']==0
    assert response.closed
