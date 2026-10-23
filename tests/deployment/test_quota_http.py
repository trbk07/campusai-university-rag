"""Actual loopback HTTP, durable quota and grounded answers; no live provider."""
import io
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from campusai.api import CampusAIApplication
from campusai.deployment.local_server import make_local_server
from campusai.llm.cache import SQLiteLLMCache
from campusai.llm.client import GeminiClient
from campusai.llm.quota import QuotaGovernor, QuotaPolicy
from campusai.web import make_wsgi_app
from tests.deployment.test_provider_recovery import service_for
from tests.test_basic_rag import valid_payload


@pytest.mark.parametrize('fault', [False, True])
def test_http_budget_cache_and_durable_429_recovery(tmp_path, monkeypatch, fault):
    now = [1000.0]
    monkeypatch.setattr('time.time', lambda: now[0])
    original_urlopen = urlopen
    calls = []
    def transport(request, **kwargs):
        if request.full_url.startswith('http://127.0.0.1:'):
            return original_urlopen(request, **kwargs)
        calls.append(request.data)
        if fault and len(calls) == 1:
            raise HTTPError(request.full_url,429,'private-provider-detail',{'Retry-After':'120'},io.BytesIO())
        payload = valid_payload()
        payload['citations'] = [{'chunk_id':'c1','page':3,'quote':'MATH101 is required.'}]
        return io.BytesIO(json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(payload)}]}}]}).encode())
    monkeypatch.setattr('urllib.request.urlopen', transport)
    policy = QuotaPolicy(0, requests_per_day=2 if fault else 1)
    def client():
        return GeminiClient('private-key', generation_config={'maxOutputTokens':1024},max_retries=0,
            overload_circuit_path=tmp_path/'health.db', cache=SQLiteLLMCache(tmp_path/'cache.db'),
            quota_governor=QuotaGovernor(tmp_path/'quota.db','owner/model',policy,max_wait_seconds=0))
    llm = client()
    service = service_for(llm,tmp_path)
    app = make_wsgi_app(CampusAIApplication(service),max_concurrent_queries=1)
    with make_local_server('127.0.0.1',0,app) as server:
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def query(question='Which course?'):
            request = Request(base+'/api/query',data=json.dumps({'question':question,'language':'en'}).encode(),
                              headers={'Content-Type':'application/json'})
            with original_urlopen(request,timeout=2) as response:
                return json.load(response)
        try:
            if fault:
                for _ in range(20):
                    with pytest.raises(HTTPError) as response:
                        query()
                    assert response.value.code == 429 and response.value.headers['Retry-After'] == '120'
                    body = json.load(response.value)
                    assert body == {'ok':False,'error_code':'provider_rate_limited','retry_after_seconds':120}
                    assert 'private' not in json.dumps(body)
                assert len(calls) == 1
                now[0] += 120
            answer = query()
            assert answer['ok'] and not answer['answer']['abstained'] and not answer['cache_hit']
            for _ in range(10):
                assert query()['cache_hit']
            assert len(calls) == (2 if fault else 1)
            with pytest.raises(HTTPError) as response:
                query('Which course is required?')
            assert response.value.code == 429
            assert json.load(response.value)['error_code'] == 'provider_rate_limited'
            with original_urlopen(base+'/health',timeout=1) as response:
                assert json.load(response)['status'] == 'ok'
            assert llm.quota_governor.snapshot()['in_flight'] == 0
        finally:
            server.shutdown()
            thread.join(2)
            service.close()
    # Reconstruct application/client with the same durable files. Neither a
    # new credential nor a new service cache can reset the daily allowance.
    restarted = client()
    restarted_service = service_for(restarted,tmp_path)
    from tests.test_web import call
    try:
        body = call(make_wsgi_app(CampusAIApplication(restarted_service)), '/api/query','POST',
                    {'question':'Which course is required?','language':'en'})
        assert body['status'].startswith('429')
        assert restarted.quota_governor.snapshot()['reserved_attempts_today'] == (2 if fault else 1)
        assert len(calls) == (2 if fault else 1)
    finally:
        restarted_service.close()
