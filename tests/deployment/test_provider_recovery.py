"""Real HTTP/SQLite contracts with deterministic provider faults, no live calls."""
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from campusai.api import CampusAIApplication
from campusai.deployment.local_server import make_local_server
from campusai.llm.client import (GeminiClient, LLMAuthenticationError, LLMProviderError,
                                LLMRateLimitError, LLMResponseError)
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.web import make_wsgi_app
from tests.test_basic_rag import FakeRetriever, evidence, valid_payload
from tests.test_web import call, Service


def service_for(llm, root):
    retriever = FakeRetriever([evidence()])
    retriever.index_root = root
    return CampusAIQueryService(retriever, GroundedAnswerGenerator(llm))


def test_same_question_recovers_over_wsgi_after_durable_cooldown(tmp_path, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr('campusai.llm.overload.time.time', lambda: now[0])
    sent = []

    def transport(request, **kwargs):
        sent.append(request.data)
        if len(sent) == 1:
            raise HTTPError(request.full_url, 503, 'private-provider-detail', {}, io.BytesIO())
        payload = valid_payload()
        payload['citations'] = [{'chunk_id': 'c1', 'page': 3, 'quote': 'MATH101 is required.'}]
        return io.BytesIO(json.dumps({'candidates': [{'content': {'parts': [
            {'text': json.dumps(payload)}]}}]}).encode())

    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('fake-secret', max_retries=0, overload_circuit_path=tmp_path/'health.db')
    service = service_for(client, tmp_path)
    app = make_wsgi_app(CampusAIApplication(service))
    query = {'question': 'Which course?', 'language': 'en'}
    try:
        for _ in range(2):
            response = call(app, '/api/query', 'POST', query)
            assert response['status'].startswith('503')
            assert dict(response['headers'])['Retry-After'] == '60'
            body = json.loads(response['body'])
            assert body == {'ok': False, 'error_code': 'provider_overloaded', 'retry_after_seconds': 60}
            assert b'private-provider-detail' not in response['body']
            assert b'fake-secret' not in response['body']
        assert len(sent) == 1
        now[0] += 60
        recovered = json.loads(call(app, '/api/query', 'POST', query)['body'])
        assert recovered['ok'] and not recovered['answer']['abstained'] and not recovered['cache_hit']
        cached = json.loads(call(app, '/api/query', 'POST', query)['body'])
        assert cached['cache_hit'] and len(sent) == 2
        assert 'provider_failure' not in recovered['answer']
    finally:
        service.close()


@pytest.mark.parametrize('error,cause,code,status', [
    (LLMRateLimitError('private'), HTTPError('https://provider.test',429,'quota',{'Retry-After':'20'},io.BytesIO()), 'provider_rate_limited',429),
    (LLMProviderError('private'), TimeoutError('private'), 'provider_timeout',504),
    (LLMProviderError('private'), URLError(TimeoutError('private')), 'provider_timeout',504),
    (LLMProviderError('private'), URLError('network'), 'provider_unavailable',503),
    (LLMAuthenticationError('private'), None, 'provider_authentication_failed',503),
    (LLMResponseError('private'), None, 'provider_invalid_response',502),
])
def test_operational_errors_are_not_grounding_answers(tmp_path, error, cause, code, status):
    class FailingLLM:
        def generate_json(self, *args, **kwargs):
            raise error from cause
    service = service_for(FailingLLM(), tmp_path)
    try:
        response = call(make_wsgi_app(CampusAIApplication(service)), '/api/query', 'POST', {'question':'Which course?'})
        body = json.loads(response['body'])
        assert response['status'].startswith(str(status))
        assert body['ok'] is False and body['error_code'] == code and 'answer' not in body
        assert b'private' not in response['body']
        if code == 'provider_rate_limited':
            assert body['retry_after_seconds'] == 20
    finally:
        service.close()


def test_local_http_health_and_second_query_do_not_wait_for_first(tmp_path):
    entered, release = threading.Event(), threading.Event()
    class SlowService(Service):
        def __init__(self):
            self.calls = 0
        def ask(self, *args, **kwargs):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return super().ask(*args, **kwargs)
    service = SlowService()
    service.retriever.index_root = tmp_path
    # Library reads must use this test's empty store, never the owner's actual
    # registry and PDF history. Keep the real concurrency deadline unchanged.
    app = make_wsgi_app(CampusAIApplication(service, ingestion_defaults={
        'store_dir': tmp_path/'store', 'index_dir': tmp_path/'index'}), max_concurrent_queries=1)
    with make_local_server('127.0.0.1', 0, app) as server, ThreadPoolExecutor(max_workers=1) as executor:
        worker = threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def query():
            req = Request(base+'/api/query',data=b'{"question":"hello"}',headers={'Content-Type':'application/json'})
            with urlopen(req,timeout=2) as response:
                return json.load(response)
        first = executor.submit(query)
        try:
            assert entered.wait(2)
            with urlopen(base+'/health',timeout=1) as response:
                assert json.load(response)['status'] == 'ok'
            with urlopen(base+'/',timeout=1) as response:
                assert response.status == 200
            with urlopen(base+'/api/documents',timeout=1) as response:
                library = json.load(response)
                assert library['ok'] and library['documents'] == [] and library['jobs'] == []
            # This fixture has no configured provider; readiness must still
            # respond immediately with its truthful not-ready status.
            with pytest.raises(HTTPError) as not_ready:
                urlopen(base+'/ready',timeout=1)
            assert not_ready.value.code == 503
            assert json.load(not_ready.value)['status'] == 'not_ready'
            with pytest.raises(HTTPError) as busy:
                query()
            assert busy.value.code == 429
            assert json.load(busy.value)['error_code'] == 'query_busy'
            assert service.calls == 1
        finally:
            release.set()
            server.shutdown()
            worker.join(2)
        assert first.result()['ok']
        # Failed/admitted requests release their query slot for subsequent work.
        assert call(app,'/api/query','POST',{'question':'hello'})['status'].startswith('200')


def test_local_transport_refuses_public_bind():
    with pytest.raises(ValueError, match='loopback'):
        make_local_server('0.0.0.0',0,lambda *_args: [])


def test_delete_intent_returns_while_cleanup_waits_for_query(tmp_path, monkeypatch):
    from campusai.web_documents import WebDocuments
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    mutation_arrived, deleted = threading.Event(), threading.Event()
    class SlowService(Service):
        def ask(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            finished.set()
            return super().ask(*args, **kwargs)
    service = SlowService()
    service.retriever.index_root = tmp_path
    application = CampusAIApplication(service, ingestion_defaults={'store_dir':tmp_path/'store','index_dir':tmp_path/'index'})
    from campusai.documents.registry import DocumentRegistry
    from campusai.schemas import Document
    DocumentRegistry(tmp_path/'store/registry.json').add(Document('a'*64,str(tmp_path/'source.pdf'),1))
    service_app = make_wsgi_app(application, max_concurrent_queries=1)
    def delete(_self, _doc_id):
        assert finished.is_set(), 'Deletion must wait until the active query releases its sources'
        deleted.set()
        return {'ok':True}
    monkeypatch.setattr(WebDocuments, '_delete_artifacts', delete)
    monkeypatch.setattr(WebDocuments, 'locate_quote', lambda *_args: {'ok':True,'page':1})
    def observed(environ, start_response):
        if environ['REQUEST_METHOD'] == 'DELETE':
            mutation_arrived.set()
        return service_app(environ, start_response)
    with make_local_server('127.0.0.1', 0, observed) as server, ThreadPoolExecutor(max_workers=2) as executor:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def request(path, method='GET', payload=None):
            data = None if payload is None else json.dumps(payload).encode()
            with urlopen(Request(base+path, method=method, data=data,
                    headers={'Content-Type':'application/json'}), timeout=2) as response:
                return json.load(response)
        query = executor.submit(request, '/api/query', 'POST', {'question':'hello'})
        try:
            assert entered.wait(2)
            deletion = executor.submit(request, '/api/documents/'+('a'*64), 'DELETE')
            assert mutation_arrived.wait(2)
            assert request('/health')['status'] == 'ok'
            assert request('/api/documents')['ok']
            assert request('/api/documents/'+('a'*64)+'/locate', 'POST', {'quote':'original'})['page'] == 1
            assert deletion.result(timeout=2)['deleting']
            assert not deleted.is_set()
            release.set()
            assert query.result(timeout=2)['ok']
            assert deleted.wait(2)
        finally:
            release.set()
            server.shutdown()
            worker.join(2)
