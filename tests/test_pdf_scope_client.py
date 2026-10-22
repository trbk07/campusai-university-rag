"""Real PDF bytes and durable accounting; all provider transports are local fakes."""
import base64
import hashlib
import json

import pytest

from campusai.llm.client import GeminiClient, LLMProviderError, LLMRateLimitError
from campusai.llm.pdf_scope import body_hash, pdf_parts
from campusai.llm.quota import QuotaGovernor, QuotaPolicy
from tests.test_document_scope import source


def documents(tmp_path, **options):
    _store,doc_id,path=source(tmp_path,('Readable source.',),**options)
    return [{'sha256':doc_id,'data':base64.b64encode(path.read_bytes()).decode()}]


def client(tmp_path, *, daily=10):
    governor=QuotaGovernor(tmp_path/'quota.sqlite','test-pdf',QuotaPolicy(0,
        input_tokens_per_minute=100_000,requests_per_day=daily),max_wait_seconds=0)
    return GeminiClient('fixture-key',model='gemini-test',max_retries=0,timeout=1,
        generation_config={'maxOutputTokens':32},quota_governor=governor,allow_pdf_scope=True)


def fake_transport(monkeypatch, count=100):
    calls=[]
    def transport(request,*args,**kwargs):
        body=json.loads(request.data);calls.append((request.full_url,body))
        assert 'fixture-key' not in json.dumps(body)
        if request.full_url.endswith(':countTokens'):return {'totalTokens':count}
        return {'candidates':[{'content':{'parts':[{'text':'{"ok": true}'}]},'finishReason':'STOP'}],
            'usageMetadata':{'promptTokenCount':80,'totalTokenCount':85},'modelVersion':'fixture-model'}
    monkeypatch.setattr('campusai.llm.client._request_json',transport)
    return calls


def test_pdf_request_is_measured_then_generated_with_two_durable_attempts(tmp_path,monkeypatch):
    llm=client(tmp_path);docs=documents(tmp_path);calls=fake_transport(monkeypatch)
    schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok']}
    expected=llm.prepare_json_request('Inspect the source.',schema,pdf_documents=docs)
    assert not calls
    response=llm.complete('Inspect the source.',pdf_documents=docs,
        generationConfig={'responseMimeType':'application/json','responseSchema':{'type':'OBJECT',
            'properties':{'ok':{'type':'BOOLEAN'}},'required':['ok']}})
    assert len(calls)==2 and calls[0][0].endswith(':countTokens')
    assert calls[1][1]==expected
    assert calls[0][1]=={'generateContentRequest':{'model':'models/gemini-test',**expected}}
    assert response.input_measurement['generation_body_sha256']==body_hash(expected)
    assert response.input_measurement['response']=={'totalTokens':100}
    assert llm.quota_governor.snapshot()['reserved_attempts_today']==2


@pytest.mark.parametrize('count',[None,True,-1,1.2,'100'])
def test_invalid_measurement_never_starts_generation(tmp_path,monkeypatch,count):
    llm=client(tmp_path);calls=fake_transport(monkeypatch,count)
    with pytest.raises(LLMProviderError,match='measurement'):
        llm.complete('Read.',pdf_documents=documents(tmp_path))
    assert len(calls)==1 and llm.quota_governor.snapshot()['reserved_attempts_today']==1


def test_measurement_does_not_bypass_daily_generation_admission(tmp_path,monkeypatch):
    llm=client(tmp_path,daily=1);calls=fake_transport(monkeypatch)
    with pytest.raises(LLMRateLimitError):llm.complete('Read.',pdf_documents=documents(tmp_path))
    assert len(calls)==1 and llm.quota_governor.snapshot()['reserved_attempts_today']==1


def test_default_client_and_unverified_parts_fail_before_transport(tmp_path,monkeypatch):
    calls=fake_transport(monkeypatch)
    docs=documents(tmp_path)
    llm=GeminiClient('fixture-key',generation_config={'maxOutputTokens':32})
    with pytest.raises(LLMProviderError):llm.complete('Read.',pdf_documents=docs)
    with pytest.raises(LLMProviderError):llm.complete('Read.',contents=[{'parts':[{'inlineData':{}}]}])
    enabled=client(tmp_path)
    for invalid in [[{'sha256':'0'*64,'data':docs[0]['data']}],
                 [{'sha256':'0'*64,'data':'not-base64'}],
                 docs*2]:
        with pytest.raises(LLMProviderError):enabled.complete('Read.',pdf_documents=invalid)
    assert not calls


def test_pdf_limits_are_based_on_actual_bytes_not_claimed_page_counts(tmp_path):
    docs=documents(tmp_path)
    assert pdf_parts(docs)[0]['inlineData']['mimeType']=='application/pdf'
    with pytest.raises(ValueError):pdf_parts([{**docs[0],'page_count':0}])
    with pytest.raises(ValueError):pdf_parts(docs*5)


def test_pdf_scope_cannot_disable_quota_or_enable_hidden_retries(tmp_path):
    with pytest.raises(ValueError):GeminiClient('fixture-key',allow_pdf_scope=True,max_retries=0)
    governor=QuotaGovernor(tmp_path/'quota.sqlite','scope',QuotaPolicy(0))
    with pytest.raises(ValueError):GeminiClient('fixture-key',allow_pdf_scope=True,
        max_retries=1,quota_governor=governor)
