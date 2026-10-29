"""OpenAI-compatible SSE for local inference, using bounded real wire frames."""
import io
import json
import urllib.error

import pytest

from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.client import OpenAICompatibleClient, LLMError, LLMResponseError
from campusai.llm.streaming import capture_stream, StreamCancelled


def event(text=None, *, finish=None, **extra):
    delta = {} if text is None else {'content': text}
    return {'id': 'request-1', 'model': 'local-model', 'choices': [
        {'index': 0, 'delta': delta, 'finish_reason': finish}], **extra}


def wire(*events, done=True):
    result = b''.join(b'data: '+json.dumps(v).encode()+b'\n\n' for v in events)
    return result + (b'data: [DONE]\n\n' if done else b'')


class Fragmented(io.BytesIO):
    def read1(self, size=-1): return self.read(min(size, 3))


def client(**kwargs):
    return OpenAICompatibleClient('http://127.0.0.1:11437/v1/chat/completions',
        'local-placeholder', 'local-model', max_retries=0, **kwargs)


def test_stream_preserves_prompt_schema_and_measures_final_text_not_reasoning(monkeypatch):
    sent = []
    hidden = event()
    hidden['choices'][0]['delta'] = {'role': 'assistant', 'reasoning_content': 'private reasoning'}
    output = wire(hidden, event('{"answer":'), event('"ok"}', finish='stop'),
        {'id':'request-1','model':'local-model','choices':[], 'usage':{'total_tokens':20}})
    def send(request, **_):
        sent.append(request)
        return Fragmented(output)
    monkeypatch.setattr('urllib.request.urlopen', send)
    notifications = []
    with capture_stream(notifications.append) as capture:
        result = client().generate_json('source-only question', schema={'type':'object','required':['answer']})
    assert result == {'answer':'ok'}
    body = json.loads(sent[0].data)
    assert body == {'model':'local-model','messages':[{'role':'user','content':'source-only question'}],
                    'response_format':{'type':'json_object'},'stream':True,'stream_options':{'include_usage':True}}
    summary = capture.summary()
    assert summary['protocol'] == 'openai-sse'
    assert summary['calls'][0]['first_text_delta_ms'] is not None
    assert summary['calls'][0]['status'] == 'complete'
    assert summary['calls'][0]['text_characters'] == len('{"answer":"ok"}')
    assert notifications == [{'type':'progress','phase':'generating'}, {'type':'progress','phase':'verifying'}]
    assert 'private reasoning' not in json.dumps(summary)


@pytest.mark.parametrize('body', [
    wire(event('partial'),done=False), wire(event('partial')),
    wire(event('complete',finish='stop'),done=False),
    wire(event('complete',finish='length')),
    wire(event('complete',finish='content_filter')),
    wire(event('complete',finish='stop'),event('extra')),
    wire(event('complete',finish='stop'),event(finish='stop')),
    wire(event('a'),event('b', id='other-request',finish='stop')),
    wire(event('a'),event('b', model='other-model',finish='stop')),
    wire({'choices':None}), wire({'choices':[None]}),
    wire({'choices':[{'index':True,'delta':{}}]}),
    wire({'choices':[{'index':0,'delta':None}]}),
    wire({'choices':[{'index':0,'delta':{'content':[]}}]}),
    wire({'choices':[{'index':0,'delta':{'refusal':'no'}}]}),
    wire({'choices':[{'index':0,'delta':{'tool_calls':[{'name':'untrusted'}]}}]}),
    wire({'error':{'message':'private provider detail'}}),
    wire(event('complete',finish='stop')) + wire(event('extra')),
    b'data: {"_stream_done":true}\n\n', b'data: {bad-json}\n\n',
])
def test_incomplete_or_invalid_stream_is_not_returned_or_cached(monkeypatch, body):
    cache = SQLiteLLMCache(':memory:')
    model = client(cache=cache)
    sent = []
    def send(*_, **__):
        sent.append(1)
        return Fragmented(body)
    monkeypatch.setattr('urllib.request.urlopen', send)
    try:
        for _ in range(2):
            with pytest.raises(LLMError), capture_stream():
                model.complete('same question')
        assert len(sent) == 2
    finally:
        model.close()


def test_stream_never_writes_unvalidated_json_into_nonstream_cache(monkeypatch):
    cache = SQLiteLLMCache(':memory:')
    model = client(cache=cache)
    calls = []
    def send(request, **_):
        calls.append(request)
        return Fragmented(wire(event('not JSON',finish='stop')))
    monkeypatch.setattr('urllib.request.urlopen', send)
    try:
        for _ in range(2):
            with pytest.raises(LLMResponseError), capture_stream():
                model.generate_json('source-only question',schema={'type':'object'})
        assert len(calls) == 2
    finally:
        model.close()


def test_cancelled_stream_or_retry_profile_never_opens_transport(monkeypatch):
    def forbidden(*_, **__): raise AssertionError('transport must not open')
    monkeypatch.setattr('urllib.request.urlopen', forbidden)
    with pytest.raises(StreamCancelled), capture_stream(cancelled=lambda:True):
        client().complete('question')
    model = OpenAICompatibleClient('http://127.0.0.1:11437/v1/chat/completions',
                                   'local-placeholder','local-model',max_retries=1)
    with pytest.raises(LLMError,match='max_retries=0'), capture_stream():
        model.complete('question')


def test_provider_error_does_not_retry_mid_stream(monkeypatch):
    sent = []
    def send(request, **_):
        sent.append(1)
        raise urllib.error.HTTPError(request.full_url,503,'busy',{},io.BytesIO(b'{}'))
    monkeypatch.setattr('urllib.request.urlopen',send)
    with pytest.raises(LLMError), capture_stream():
        client().complete('question')
    assert len(sent) == 1


def test_opt_in_native_schema_is_sent_and_post_validation_remains_enforced(monkeypatch):
    schema = {'type':'object','required':['claims'], 'properties':{
        'claims':{'type':'array','items':{'type':'object','required':['text']}}}}
    sent = []
    def send(request, **_):
        sent.append(json.loads(request.data))
        return Fragmented(wire(event('{"claims":["wrong item type"]}',finish='stop')))
    monkeypatch.setattr('urllib.request.urlopen',send)
    model = client(response_format_mode='json_schema')
    prepared = model.prepare_json_request('source-only question',schema=schema)
    assert prepared['response_format'] == {'type':'json_schema','json_schema':{
        'name':'campusai_response','schema':schema}}
    with pytest.raises(LLMResponseError), capture_stream():
        model.generate_json('source-only question',schema=schema)
    actual = sent[0];actual.pop('stream');actual.pop('stream_options')
    assert actual == prepared


def test_factory_schema_mode_is_explicit_and_gemini_profile_cannot_receive_it(tmp_path):
    from campusai.llm.factory import create_llm
    config = {'llm':{'provider':'openai-compatible','model':'local-model',
        'api_key_env':'LOCAL_TEST_KEY','cache_path':':memory:','max_retries':0,
        'endpoint':'http://127.0.0.1:11437/v1/chat/completions','response_format_mode':'json_schema'}}
    path=tmp_path/'config.json';path.write_text(json.dumps(config))
    model=create_llm(path,{'LOCAL_TEST_KEY':'local-placeholder'})
    assert model.response_format_mode=='json_schema'
    model.close()
    config['llm']['provider']='gemini';path.write_text(json.dumps(config))
    with pytest.raises(ValueError,match='response_format_mode'):
        create_llm(path,{'LOCAL_TEST_KEY':'local-placeholder'})


def test_optional_system_policy_is_in_exact_request_and_can_be_overridden():
    model=client(default_system_prompt='Use only source facts and preserve necessary qualifiers.')
    body=model.prepare_json_request('a question',schema={'type':'object'})
    assert body['messages'][0]=={'role':'system','content':model.default_system_prompt}
    assert body['messages'][1]=={'role':'user','content':'a question'}
    assert model.prepare_request('a question',system_prompt='different')['messages'][0]['content']=='different'


def test_decomposed_vietnamese_is_canonically_preserved_in_prepared_request():
    import unicodedata
    text = 'B\u1eadc 4 tr\u1edf l\u00ean; kh\u00f4ng b\u1ecf d\u1ea5u hay \u0111\u1ed5i s\u1ed1 2022.'
    model = client(default_system_prompt=unicodedata.normalize('NFD', text))
    body = model.prepare_request(unicodedata.normalize('NFD', text))
    assert [message['content'] for message in body['messages']] == [text, text]
