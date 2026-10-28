"""Streaming uses the existing scope/grounding path; progress contains no text."""
import io
import json
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from campusai.api import CampusAIApplication
from campusai.deployment.local_server import make_local_server
from campusai.llm.client import GeminiClient
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.web import make_wsgi_app
from tests.test_basic_rag import evidence, valid_payload
from tests.test_gemini_streaming import event, frames


def payload():
    value = valid_payload()
    value['claims'] = [{'claim_id':'a','text':value['answer'],'citation_ids':['c1']}]
    # The native JSON schema intentionally does not accept public-only fields.
    value['citations'] = [{'chunk_id':'c1','page':3,'quote':value['answer']}]
    return value


class GatedResponse:
    def __init__(self, value, release, *, failure=False):
        text = json.dumps(value)
        midpoint = max(1,len(text)//2)
        self.first = frames(event(text[:midpoint]))
        self.last = frames(event(text[midpoint:],finish='STOP',usageMetadata={'totalTokenCount':40}))
        self.release, self.failure = release, failure
        self.closed = threading.Event()
    def __enter__(self): return self
    def __exit__(self,*_args): self.closed.set()
    def read1(self, _size):
        if self.first:
            value,self.first=self.first,b''
            return value
        assert self.release.wait(5)
        if self.failure:
            raise HTTPError('https://fixture.invalid',503,'private error',{'Retry-After':'60'},io.BytesIO(b'{}'))
        value,self.last=self.last,b''
        return value
    read=read1


def runtime(tmp_path, monkeypatch, *, value=None, failure=False):
    release=threading.Event();wire=GatedResponse(value or payload(),release,failure=failure)
    posts=[]
    original=urlopen
    def transport(request, **kwargs):
        if request.full_url.startswith('https://generativelanguage.googleapis.com/'):
            posts.append(request)
            return wire
        return original(request,**kwargs)
    monkeypatch.setattr('urllib.request.urlopen',transport)
    service=CampusAIQueryService(SimpleNamespace(index_root=tmp_path,_indexes={},reranker=None,
        search=lambda *_a, **_kw:[evidence()]),GroundedAnswerGenerator(GeminiClient('fixture-key',max_retries=0)))
    application=CampusAIApplication(service)
    traces=[]
    return make_wsgi_app(application,telemetry_hook=traces.append,max_concurrent_queries=1,
        enable_query_streaming=True),application,wire,release,posts,traces


def call(web, *, scope=None, question='Which course is required?'):
    body=json.dumps({'question':question,'language':'en','doc_ids':['doc-1']}).encode()
    env={'PATH_INFO':'/api/query','REQUEST_METHOD':'POST','HTTP_ACCEPT':'application/x-ndjson',
        'CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)}
    if scope is not None:env['campusai.authorized_doc_ids']=scope
    head={}
    response=web(env,lambda status,headers:head.update(status=int(status.split()[0]),headers=dict(headers)))
    return head,response


def test_actual_http_first_model_progress_precedes_verified_answer(tmp_path,monkeypatch):
    web,app,wire,release,posts,traces=runtime(tmp_path,monkeypatch)
    with make_local_server('127.0.0.1',0,web) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        req=Request(f'http://127.0.0.1:{server.server_port}/api/query',
            data=b'{"question":"Which course is required?","language":"en","doc_ids":["doc-1"]}',
            headers={'Content-Type':'application/json','Accept':'application/x-ndjson'})
        try:
            with urlopen(req,timeout=5) as response:
                assert response.headers['Content-Type'].startswith('application/x-ndjson')
                first=response.readline()
                assert json.loads(first)=={'type':'progress','phase':'generating'}
                assert b'MATH101' not in first and traces==[] and not release.is_set()
                release.set()
                rest=[json.loads(line) for line in response if line.strip()]
                final=rest[-1]
                assert final['type']=='result' and final['status']==200
                assert final['value']['answer']['abstained'] is False
                assert final['value']['answer']['citations'][0]['quote']=='MATH101 is required.'
                assert len(traces)==1 and traces[0]['request_id']==response.headers['X-Request-ID']
                assert traces[0]['model_stream']['calls'][0]['first_text_delta_ms']>=0
                assert 'MATH101' not in json.dumps(traces[0]['model_stream'])
            assert len(posts)==1 and wire.closed.wait(1)
        finally:
            release.set();server.shutdown();thread.join(5);app.close()


@pytest.mark.parametrize('defect',['answer','citation','claim'])
def test_stream_does_not_publish_unsupported_model_fragments(tmp_path,monkeypatch,defect):
    value=payload()
    if defect=='answer':value['answer']='MATH999 fabricated.'
    if defect=='citation':value['citations'][0]['chunk_id']='fabricated'
    if defect=='claim':value['claims'][0]['text']='MATH999 fabricated.'
    web,app,wire,release,posts,traces=runtime(tmp_path,monkeypatch,value=value)
    try:
        head,response=call(web)
        assert next(response)==b'{"type": "progress", "phase": "generating"}\n'
        release.set();body=b''.join(response)
        assert b'MATH999' not in body and b'fabricated' not in body
        final=json.loads(body.splitlines()[-1])['value']['answer']
        assert final['abstained'] and final['citations']==[]
    finally:release.set();app.close()


def test_failure_after_first_delta_keeps_operational_error_without_partial_answer(tmp_path,monkeypatch):
    web,app,wire,release,posts,traces=runtime(tmp_path,monkeypatch,failure=True)
    try:
        head,response=call(web);assert next(response)
        release.set();lines=[json.loads(x) for x in response]
        assert lines[-1]['status']==503
        assert lines[-1]['value']['error_code']=='provider_overloaded'
        assert lines[-1]['value']['retry_after_seconds']==60
        assert 'answer' not in lines[-1]['value'] and len(posts)==1
    finally:release.set();app.close()


def test_closing_unstarted_stream_observes_cancellation_and_releases_query_lease(tmp_path,monkeypatch):
    web,app,wire,release,posts,traces=runtime(tmp_path,monkeypatch)
    try:
        head,response=call(web)
        response.close();release.set()
        assert wire.closed.wait(2)
        # The cancelled query cannot publish a cached success. A second normal
        # request must invoke its provider again rather than use partial output.
        second_posts=[]
        def recovered(*_a, **_kw):
            second_posts.append(True)
            return io.BytesIO(frames(event(json.dumps(payload()),finish='STOP')))
        monkeypatch.setattr('urllib.request.urlopen',recovered)
        deadline=time.monotonic()+2
        while True:
            next_head,next_response=call(web)
            body=b''.join(next_response)
            if next_head['status']!=429:break
            assert time.monotonic()<deadline
            time.sleep(.01)
        final=json.loads(body.splitlines()[-1])['value']
        assert next_head['status']==200 and not final['answer']['abstained']
        assert second_posts==[True] and traces[-1]['cache_hit'] is False
    finally:release.set();app.close()


def test_denied_scope_preserves_json_error_and_never_calls_model(tmp_path,monkeypatch):
    web,app,wire,release,posts,traces=runtime(tmp_path,monkeypatch)
    try:
        head,response=call(web,scope=['another-document'])
        assert head['status']==400 and head['headers']['Content-Type'].startswith('application/json')
        assert json.loads(b''.join(response))['ok'] is False
        assert posts==[] and len(traces)==1 and traces[0]['model_stream']['calls']==[]
    finally:release.set();app.close()


def test_failure_before_model_text_preserves_json_status_retry_and_request_id(tmp_path,monkeypatch):
    web,app,wire,release,posts,traces=runtime(tmp_path,monkeypatch)
    def failure(*_a, **_kw):
        raise HTTPError('https://fixture.invalid',503,'private message',{'Retry-After':'60'},io.BytesIO(b'{}'))
    monkeypatch.setattr('urllib.request.urlopen',failure)
    try:
        head,response=call(web);body=b''.join(response)
        assert head['status']==503 and head['headers']['Retry-After']=='60'
        assert head['headers']['Content-Type'].startswith('application/json')
        assert json.loads(body)['error_code']=='provider_overloaded' and b'private' not in body
        assert traces[0]['request_id']==head['headers']['X-Request-ID']
        assert traces[0]['model_stream']['calls'][0]['first_text_delta_ms'] is None
    finally:app.close()


def test_default_transport_stays_native_even_if_streaming_is_requested(tmp_path,monkeypatch):
    posts=[]
    def native(request,**_kw):
        posts.append(request.full_url)
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(payload())}]}}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen',native)
    service=CampusAIQueryService(SimpleNamespace(index_root=tmp_path,_indexes={},reranker=None,
        search=lambda *_a,**_kw:[evidence()]),GroundedAnswerGenerator(GeminiClient('fixture-key',max_retries=0)))
    app=CampusAIApplication(service);traces=[]
    web=make_wsgi_app(app,telemetry_hook=traces.append)
    try:
        head,response=call(web);value=json.loads(b''.join(response))
        assert head['headers']['Content-Type'].startswith('application/json')
        assert value['ok'] and not value['answer']['abstained']
        assert len(posts)==1 and posts[0].endswith(':generateContent')
        assert 'model_stream' not in traces[0]
    finally:app.close()


def test_stream_worker_capacity_survives_disconnect_and_worker_failure():
    from campusai.web_streaming import stream_response
    from campusai.web_documents import WebError
    from campusai.llm.streaming import current_stream
    slots=threading.BoundedSemaphore(1);release=threading.Event();entered=[]
    def run(_environ,_respond):
        entered.append(True)
        current_stream().notify({'type':'progress','phase':'generating','text':'must-not-leak'})
        assert release.wait(2)
        raise RuntimeError('private worker details')
    env={'CONTENT_LENGTH':'2'}
    output=stream_response(env,lambda *_a:None,run,b'{}',slots,[])
    try:
        assert json.loads(next(output))=={'type':'progress','phase':'generating'}
        with pytest.raises(WebError) as error:
            stream_response({},lambda *_a:None,run,b'{}',slots,[])
        assert error.value.code=='query_busy' and error.value.status==429
        assert entered==[True]
    finally:
        output.close();release.set()
    assert slots.acquire(timeout=2)
    slots.release()


@pytest.mark.parametrize('value',[None,1,'true'])
def test_streaming_enablement_requires_an_explicit_boolean(tmp_path,value):
    from tests.test_web import Service
    service=Service();service.retriever=SimpleNamespace(index_root=tmp_path,_indexes={})
    with pytest.raises(ValueError,match='boolean'):
        make_wsgi_app(CampusAIApplication(service),enable_query_streaming=value)
