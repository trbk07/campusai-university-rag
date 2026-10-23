"""Manual bounded local OCR through the real PDF/job/index/HTTP lifecycle."""
import threading
import time
import fitz
import pytest

from campusai.api import CampusAIApplication
from campusai.ingestion.jobs import IngestionJobManager, JobQueueFull
from campusai.ingestion.ocr import OCRDocument, OCRUnavailable
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app
from tests.test_mixed_pdf import mixed_pdf
from tests.test_web_documents import call, upload_ready


def recognized(*args, **kwargs):
    assert kwargs['page_numbers'] == [2]
    return OCRDocument([{'page':2,'text':'Scanned enrollment requires advisor approval.'}], 'test-ocr', .99, .01)


def wait_job(web, job_id):
    deadline = time.monotonic()+10
    while time.monotonic()<deadline:
        job = call(web,'/api/jobs/'+job_id)['body']['job']
        if job['state'] not in {'staging','queued','running'}: return job
        time.sleep(.01)
    pytest.fail('OCR job did not finish')


@pytest.fixture
def ocr_app(tmp_path, mixed_pdf, monkeypatch):
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognized)
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(tmp_path/'index'),
        GroundedAnswerGenerator(None)), jobs=IngestionJobManager(max_workers=2),
        ingestion_defaults={'store_dir':tmp_path/'store','index_dir':tmp_path/'index',
                            'dense_model':'fallback-hash-256','ocr_max_pages':1})
    web = make_wsgi_app(app)
    job = upload_ready(web,mixed_pdf.read_bytes())
    assert job['state']=='review_required'
    try: yield web, app, job['document_id'], tmp_path
    finally: app.close()


def test_ocr_reprocesses_existing_pdf_without_reupload_and_preserves_scope(ocr_app):
    web, app, doc_id, root = ocr_app
    url = f'/api/documents/{doc_id}/ocr'
    before = call(web,f'/api/documents/{doc_id}/file')['raw']
    assert call(web,url,'POST',{},scope=[])['status']==404
    assert call(web,url,'POST',{},headers={'HTTP_SEC_FETCH_SITE':'cross-site'})['status']==403
    assert call(web,url,'POST',{'ocr_timeout_seconds':99999})['status']==400
    assert len(app.jobs.list())==1
    response = call(web,url,'POST',{})
    assert response['status']==202
    job = wait_job(web,response['body']['job']['job_id'])
    assert job['state']=='succeeded' and job['ready']
    assert len(app.jobs.list())==2
    assert call(web,f'/api/documents/{doc_id}/file')['raw']==before
    doc = call(web,f'/api/documents/{doc_id}')['body']['document']
    assert doc['ready'] and not doc['ocr_available']
    parsed = (root/'store'/doc_id/'parsed.md').read_text(encoding='utf-8')
    assert 'Native prerequisite' in parsed and 'Scanned enrollment' in parsed
    assert call(web,url,'POST',{})['status']==409


def test_failed_local_ocr_can_be_explicitly_reprocessed_without_erasing_history(ocr_app, monkeypatch):
    web, app, doc_id, _root = ocr_app
    def unavailable(*a, **kw): raise OCRUnavailable('test engine unavailable')
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', unavailable)
    url=f'/api/documents/{doc_id}/ocr'
    first=call(web,url,'POST',{})
    assert wait_job(web,first['body']['job']['job_id'])['state']=='review_required'
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognized)
    second=call(web,url,'POST',{})
    assert second['body']['job']['job_id']!=first['body']['job']['job_id']
    assert wait_job(web,second['body']['job']['job_id'])['ready']
    assert len(app.jobs.list())==3


def test_ocr_rejects_changed_source_before_admitting_work(ocr_app):
    web, app, doc_id, root=ocr_app
    source=root/'store'/'uploads'/doc_id/'Enrollment.pdf'
    source.write_bytes(source.read_bytes()+b'changed')
    result=call(web,f'/api/documents/{doc_id}/ocr','POST',{})
    assert result['status']==409 and result['body']['error_code']=='job_source_changed'
    assert len(app.jobs.list())==1


def test_ocr_page_budget_cannot_be_raised_by_client(ocr_app, mixed_pdf):
    web, app, _doc_id, root=ocr_app
    with fitz.open(mixed_pdf) as original, fitz.open() as pdf:
        pdf.insert_pdf(original)
        pdf.insert_pdf(original,from_page=1,to_page=1)
        new_job=upload_ready(web,pdf.tobytes())
    result=call(web,f"/api/documents/{new_job['document_id']}/ocr",'POST',{})
    assert result['status']==413 and result['body']['error_code']=='ocr_page_limit'


def test_duplicate_ocr_is_blocked_but_active_pdf_can_be_deleted(ocr_app, monkeypatch):
    web, app, doc_id, root=ocr_app
    entered, release=threading.Event(), threading.Event()
    def blocking(*a, **kw):
        entered.set(); assert release.wait(5); return recognized(*a, **kw)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', blocking)
    url=f'/api/documents/{doc_id}/ocr'
    try:
        response=call(web,url,'POST',{})
        assert entered.wait(5)
        assert call(web,url,'POST',{})['status']==409
        assert call(web,f'/api/documents/{doc_id}','DELETE')['status']==202
        assert call(web,'/api/query','POST',{'question':'What needs approval?','doc_ids':[doc_id]})['status']==409
    finally: release.set()
    deadline=time.monotonic()+5
    while app.jobs.list() or (root/'store/.deletions'/doc_id).exists():
        assert time.monotonic()<deadline
        time.sleep(.02)
    assert not (root/'store/uploads'/doc_id).exists()
    assert call(web,'/api/documents')['body']['documents']==[]


def test_ocr_queue_full_is_reported_without_extra_work(ocr_app, monkeypatch):
    web, app, doc_id, _root=ocr_app
    def full(*a, **kw): raise JobQueueFull('full')
    monkeypatch.setattr(app.jobs,'submit',full)
    result=call(web,f'/api/documents/{doc_id}/ocr','POST',{})
    assert result['status']==429 and result['headers']['Retry-After']=='2'
    assert len(app.jobs.list())==1
