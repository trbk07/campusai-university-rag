"""Source access survives provider outage without publishing an AI answer."""
import io
import json
import threading
from dataclasses import replace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from campusai.api import CampusAIApplication
from campusai.deployment.local_server import make_local_server
from campusai.llm.client import GeminiClient, LLMProviderError, LLMRateLimitError
from campusai.rag.excerpts import source_excerpts
from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation
from campusai.rag.service import CampusAIQueryService
from campusai.web import make_wsgi_app
from tests.test_basic_rag import FakeRetriever, evidence, valid_payload
from tests.test_web import call


def test_twenty_http_queries_during_outage_then_real_recovery(tmp_path, monkeypatch):
    now, attempts = [1000.0], []
    monkeypatch.setattr('campusai.llm.overload.time.time', lambda: now[0])
    original = urlopen

    def transport(request, **kwargs):
        if not request.full_url.startswith('https://generativelanguage.googleapis.com/'):
            return original(request, **kwargs)
        attempts.append(request.data)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, 503, 'private', {}, io.BytesIO())
        payload = valid_payload()
        payload['citations'] = [{'chunk_id':'c1','page':3,'quote':'MATH101 is required.'}]
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[
            {'text':json.dumps(payload)}]}}]}).encode())

    monkeypatch.setattr('urllib.request.urlopen', transport)
    client = GeminiClient('synthetic-secret', max_retries=0,
                          overload_circuit_path=tmp_path/'health.db')
    retriever = FakeRetriever([evidence()])
    retriever.index_root = tmp_path
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(client))
    app = CampusAIApplication(service, provider_failure_excerpts=True)
    try:
        with make_local_server('127.0.0.1', 0, make_wsgi_app(app, max_concurrent_queries=1)) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
            def query(question):
                request = Request(base+'/api/query', data=json.dumps(
                    {'question':question,'language':'en'}).encode(),
                    headers={'Content-Type':'application/json'})
                with original(request, timeout=2) as response:
                    assert response.code == 200
                    return json.load(response)
            try:
                for index in range(20):
                    value = query(f'Which course is required, request {index}?')
                    assert value['ok'] and value['answer']['abstained']
                    assert not value['cache_hit']
                    assert value['answer']['claims'] == value['answer']['citations'] == []
                    assert value['fallback']['kind'] == 'source_excerpts'
                    assert value['fallback']['citations'][0]['quote'] == 'MATH101 is required.'
                    assert value['provider_status']['error_code'] == 'provider_overloaded'
                    assert 'synthetic-secret' not in json.dumps(value)
                assert len(attempts) == 1  # Nineteen local lookups, zero retries.
                now[0] += 60
                recovered = query('Which course is required?')
                assert not recovered['answer']['abstained'] and 'fallback' not in recovered
                assert query('Which course is required?')['cache_hit']
                assert len(attempts) == 2
            finally:
                server.shutdown()
                worker.join()
    finally:
        app.close()


@pytest.mark.parametrize('error', [LLMProviderError('private'), LLMRateLimitError('private')])
def test_fallback_never_caches_provider_fault_or_excerpt(tmp_path, error):
    class Provider:
        calls = 0
        def generate_json(self, *_args, **_kwargs):
            self.calls += 1
            raise error
    provider = Provider()
    retriever = FakeRetriever([evidence()])
    retriever.index_root = tmp_path
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(provider))
    app = make_wsgi_app(CampusAIApplication(service, provider_failure_excerpts=True))
    try:
        for _ in range(2):
            value = json.loads(call(app, '/api/query', 'POST', {'question':'Which course?'})['body'])
            assert value['fallback']['citations'] and not value['cache_hit']
        assert provider.calls == 2
    finally:
        service.close()


def test_excerpt_is_bounded_original_text_and_deduplicated():
    content = ('Unrelated introduction.\n'*70 +
               'Stack push inserts at the first node.\nStack pop removes the first node.\n' +
               'Unrelated appendix.\n'*100)
    items = [evidence(f'c{i}', content=content) for i in range(6)]
    excerpts = source_excerpts('Where do stack push and pop operate?', items)
    assert len(excerpts) == 1
    quote = excerpts[0]['quote']
    assert 'Stack push inserts' in quote and len(quote) <= 900 and quote in content
    assert validate_citation(excerpts[0], items[0], require_quote=True).valid


def test_table_excerpt_preserves_one_complete_original_row():
    item = evidence(content='{"headers":["Course","Credits"],"rows":[["A001","2"],["B002","4"]]}',
                    metadata={'table_id':'t1'})
    item = replace(item, content_type='table')
    excerpts = source_excerpts('B002 credits?', [item])
    assert len(excerpts) == 1
    assert json.loads(excerpts[0]['quote']) == ['B002','4']
    assert validate_citation(excerpts[0], item, require_quote=True).valid


def test_no_source_means_no_excerpt():
    assert source_excerpts('Anything?', []) == []
    assert source_excerpts('Anything?', [evidence(content='')]) == []


def test_at_most_three_original_request_scoped_sources():
    items = [evidence(f'c{i}', content=f'Original source {i}.') for i in range(10)]
    excerpts = source_excerpts('Original source?', items)
    assert len(excerpts) == 3
    assert {row['chunk_id'] for row in excerpts} <= {r.chunk_id for r in items}
    assert all(row['doc_id'] == 'doc-1' and row['page'] == 3 for row in excerpts)
