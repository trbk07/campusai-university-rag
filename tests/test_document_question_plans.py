"""Actual uploaded PDFs: physical-page scope, multi-intent and missing pages."""
import re
import fitz
import pytest

from campusai.api import CampusAIApplication
from campusai.ingestion.jobs import IngestionJobManager
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app
from tests.test_web_documents import call, upload_ready


@pytest.fixture
def source_app(tmp_path):
    class RecordingModel:
        model = 'offline-scope-fixture'
        def __init__(self): self.prompts = []
        def generate_json(self, prompt, **kwargs):
            self.prompts.append(prompt)
            return {'answer':'The selected text is available for review.', 'abstained':True,
                'abstention_reason':'document_does_not_mention','confidence':'low','citations':[], 'claims':[]}
    provider = RecordingModel()
    service = CampusAIQueryService(HybridRetriever(tmp_path/'index'),
        GroundedAnswerGenerator(provider, source_citations=True), default_mode='bm25')
    app = CampusAIApplication(service, jobs=IngestionJobManager(journal_path=tmp_path/'jobs.sqlite3'),
        ingestion_defaults={'store_dir':tmp_path/'store','index_dir':tmp_path/'index','dense_model':'fallback-hash-256'})
    web = make_wsgi_app(app)
    with fitz.open() as pdf:
        for label in ('alpha', 'beta', 'gamma'):
            pdf.new_page().insert_text((72,72), f'The {label} subject is explained in this section. Each topic has original supporting source evidence.')
        job = upload_ready(web, pdf.tobytes())
    assert job['ready']
    try: yield web, app, provider, job['document_id']
    finally: app.close()


@pytest.mark.parametrize('question', ['Tóm tắt trang 2.', 'Explain the material on page 2.'])
def test_specific_page_uses_only_that_physical_page(source_app, question):
    web, app, provider, doc = source_app
    reply = call(web, '/api/query', 'POST', {'question':question, 'doc_ids':[doc]})
    assert reply['status'] == 200
    assert len(provider.prompts) == 1
    body = provider.prompts[0].split('EVIDENCE:\n',1)[1]
    assert 'beta subject' in body and 'alpha subject' not in body and 'gamma subject' not in body
    assert [r.page for r in app.query_service.last_retrieval] == [2]
    assert call(web, '/api/query', 'POST', {'question':question,'doc_ids':[doc]})['status'] == 200
    assert len(provider.prompts) == 1


@pytest.mark.parametrize('question', ['Tóm tắt trang 999.', 'Summarize pages 3-1.', 'Explain pages 1-999999999.'])
def test_invalid_or_nonexistent_page_is_explained_without_model(source_app, question):
    web, _app, provider, doc = source_app
    reply = call(web,'/api/query','POST',{'question':question,'doc_ids':[doc]})
    assert reply['status'] == 200 and not provider.prompts
    assert reply['body']['document_info']['kind'] == 'page_scope_unavailable'
    assert reply['body']['answer']['abstained']
    assert '3' in reply['body']['answer']['answer']


def test_page_range_includes_all_requested_pages_and_no_other_page(source_app):
    web, app, provider, doc = source_app
    reply = call(web,'/api/query','POST',{'question':'Summarize pages 1-2.','doc_ids':[doc],'language':'en'})
    assert reply['status'] == 200 and len(provider.prompts) == 1
    body = provider.prompts[0].split('EVIDENCE:\n',1)[1]
    assert 'alpha subject' in body and 'beta subject' in body and 'gamma subject' not in body
    assert {r.page for r in app.query_service.last_retrieval} == {1,2}


@pytest.mark.parametrize('question', [
    'Tài liệu có mấy trang? Tóm tắt phần beta.',
    'tài liệu có mấy trang và giải thích phần beta',
])
def test_count_plus_content_never_silently_drops_an_intent(source_app, question):
    web, _app, provider, doc = source_app
    reply = call(web,'/api/query','POST',{'question':question,'doc_ids':[doc]})
    assert reply['status'] == 200 and len(provider.prompts) == 1
    body = reply['body']
    assert body['answer']['schema_version'] == 'document-composite-v1'
    assert body['document_info']['documents'][0]['page_count'] == 3
    assert len(body['parts']) == 2 and body['parts'][1]['kind'] == 'grounded_answer'
    assert '3 trang' in body['answer']['answer']
    assert 'mấy trang' not in provider.prompts[0].split('QUESTION:\n',1)[1].split('EVIDENCE:',1)[0]
