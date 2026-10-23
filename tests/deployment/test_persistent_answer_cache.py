"""Restart reuse reduces actual model invocations without crossing source scope."""
import json
from scripts.operations import serve
from campusai.web import make_wsgi_app
from tests.test_web import call
from tests.test_basic_rag import FakeLLM, FakeRetriever, evidence, valid_payload


def test_runtime_cache_survives_rebuild_and_invalidates_on_provider_and_corpus_change(tmp_path, monkeypatch):
    index = tmp_path / 'index'
    index.mkdir()
    monkeypatch.setenv('CAMPUSAI_INDEX_DIR', str(index))
    monkeypatch.setenv('CAMPUSAI_STORE_DIR', str(tmp_path / 'store'))
    profile = tmp_path / 'profile.json'
    profile.write_text('{"llm":{}}', encoding='utf-8')
    monkeypatch.setenv('CAMPUSAI_LLM_CONFIG', str(profile))
    monkeypatch.setenv('CAMPUSAI_RAG_CACHE_PATH', str(tmp_path / 'answers.db'))
    monkeypatch.setenv('CAMPUSAI_JOB_DB', str(tmp_path / 'jobs.db'))
    monkeypatch.setenv('CAMPUSAI_RETRIEVAL_CALIBRATION', str(tmp_path / 'absent'))
    clients = []
    endpoint = ['https://one.test/generate?key=private-secret']
    def llm(_path):
        client = FakeLLM(valid_payload())
        client.endpoint = endpoint[0]
        clients.append(client)
        return client
    def retriever(*_args, **_kwargs):
        value = FakeRetriever([evidence()])
        value.index_root = index
        return value
    monkeypatch.setattr(serve, 'create_llm', llm)
    monkeypatch.setattr(serve, 'HybridRetriever', retriever)
    def query():
        application = serve.build_application()
        try:
            assert 'private-secret' not in application.query_service.cache_namespace
            return json.loads(call(make_wsgi_app(application), '/api/query', 'POST',
                {'question': 'Which course?', 'language': 'en'})['body'])
        finally:
            application.close()
    assert not query()['cache_hit']
    assert query()['cache_hit']
    assert [client.calls for client in clients] == [1, 0]
    endpoint[0] = 'https://two.test/generate'
    assert not query()['cache_hit']
    assert clients[-1].calls == 1
    # Same model/endpoint, but a new corpus generation must not reuse an answer.
    document = index / 'doc-1'
    document.mkdir()
    (document / 'bm25.json').write_text(json.dumps({'items': []}), encoding='utf-8')
    assert not query()['cache_hit']
    assert clients[-1].calls == 1


def test_clearing_stored_answers_prevents_restart_reuse(tmp_path):
    from campusai.rag.cache import RAGAnswerCache
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    path = str(tmp_path / 'answers.db')
    def service():
        return CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(FakeLLM(valid_payload())),
                                    cache=RAGAnswerCache(path), cache_namespace='fixture')
    first = service()
    try:
        assert not first.ask('Which course?', language='en').abstained
        first.cache.clear()
    finally:
        first.close()
    second = service()
    try:
        assert not second.ask('Which course?', language='en').cache_hit
        assert second.answer_generator.llm.calls == 1
    finally:
        second.close()
