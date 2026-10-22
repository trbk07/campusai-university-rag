"""Prompt JSON compatibility retains local schema validation and cache identity."""
import io
import json
import pytest
from campusai.llm.client import GeminiClient, LLMResponseError


def test_prompt_json_omits_unsupported_native_fields_and_keeps_schema_validation(monkeypatch):
    bodies=[]
    def transport(request,**kwargs):
        body=json.loads(request.data)
        bodies.append(body)
        text='{"answer":"ok"}' if len(bodies)==1 else '{"answer":42}'
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':text}]}}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen',transport)
    client=GeminiClient('fake',model='gemma-4-31b-it',json_mode='prompt',max_retries=0,
                        generation_config={'maxOutputTokens':100})
    schema={'type':'object','properties':{'answer':{'type':'string'}},'required':['answer']}
    assert client.generate_json('question',schema)=={'answer':'ok'}
    with pytest.raises(LLMResponseError,match='type mismatch'):
        client.generate_json('another',schema)
    for body in bodies:
        assert 'responseMimeType' not in body['generationConfig']
        assert 'responseSchema' not in body['generationConfig']
        assert 'OUTPUT_JSON_SCHEMA:' in body['contents'][0]['parts'][0]['text']


def test_json_mode_is_in_rag_cache_identity(tmp_path,monkeypatch):
    from tests.deployment.test_provider_recovery import service_for
    from tests.test_basic_rag import valid_payload
    from campusai.llm.cache import SQLiteLLMCache
    bodies=[]
    def transport(request,**kwargs):
        bodies.append(json.loads(request.data))
        payload=valid_payload()
        payload['citations']=[{'chunk_id':'c1','page':3,'quote':'MATH101 is required.'}]
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(payload)}]}}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen',transport)
    client=GeminiClient('fake',max_retries=0,cache=SQLiteLLMCache(':memory:'))
    service=service_for(client,tmp_path)
    try:
        assert not service.ask('Which course?',language='en').abstained
        assert not service.ask('Which course?',language='en').abstained and len(bodies)==1
        client.json_mode='prompt'
        assert not service.ask('Which course?',language='en').abstained and len(bodies)==2
    finally:
        service.close()
