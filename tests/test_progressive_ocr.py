"""Automatic OCR exposes only proved pages and resumes completed batches."""
import hashlib
import json
import threading
import time

import fitz
import pytest

from campusai.api import CampusAIApplication
from campusai.ingestion.jobs import IngestionJobManager
from campusai.ingestion.ocr import OCRDocument, OCRUnavailable, OCRLimitExceeded
from campusai.ingestion.pipeline import ingest_document
from campusai.rag.document_scope import RegisteredDocumentScopeReader, DocumentScopeUnavailable
from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app
from tests.test_mixed_pdf import mixed_pdf
from tests.test_web_documents import call
from tests.test_web_ocr import wait_job


def application(root, **overrides):
    service = CampusAIQueryService(HybridRetriever(root/'index'),
        GroundedAnswerGenerator(None), default_mode='bm25',
        document_scope_reader=RegisteredDocumentScopeReader(root/'store'))
    app = CampusAIApplication(service, jobs=IngestionJobManager(max_workers=2, journal_path=root/'jobs.sqlite3'),
        ingestion_defaults={'store_dir':root/'store','index_dir':root/'index',
            'dense_model':'fallback-hash-256','ocr_max_pages':2, **overrides})
    return app, make_wsgi_app(app)


def upload(web, data):
    response = call(web, '/api/documents/upload', 'POST', raw=data,
        headers={'CONTENT_TYPE':'application/pdf','HTTP_X_FILENAME':'Mixed.pdf'})
    assert response['status'] == 202, response
    return response['body']['job']['job_id']


def test_native_pages_can_be_asked_while_automatic_image_ocr_is_running(tmp_path, mixed_pdf, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def recognize(_path, **options):
        entered.set(); assert release.wait(5)
        assert options['page_numbers'] == [2]
        return OCRDocument([{'page':2,'text':'Advisor approval is necessary.'}], 'test', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    app, web = application(tmp_path)
    try:
        job = upload(web, mixed_pdf.read_bytes())
        assert entered.wait(5)
        doc = call(web,'/api/documents')['body']['documents'][0]
        assert doc['ready'] and doc['status'] == 'partial' and doc['unread_pages'] == [2]
        assert doc['readable_pages'] == [1,3] and doc['coverage_complete'] is False
        assert call(web,'/api/jobs/'+job)['body']['job']['state'] == 'running'
        class NativeAnswer:
            def generate_json(self, prompt, **kwargs):
                assert 'INCOMPLETE SOURCE' in prompt
                result = app.query_service.last_retrieval[0]
                quote = 'Native prerequisite courses must be completed before enrollment.'
                return {'answer':quote,'confidence':'high','abstained':False,
                    'claims':[{'claim_id':'c','text':quote,'citation_ids':[result.chunk_id]}],
                    'citations':[{'chunk_id':result.chunk_id,'page':result.page,'quote':quote}]}
        app.query_service.answer_generator.llm = NativeAnswer()
        result = call(web,'/api/query','POST',{'question':'What must be completed before enrollment?', 'doc_ids':[doc['doc_id']]})
        assert result['status'] == 200 and not result['body']['answer']['abstained']
        assert result['body']['source_coverage']['complete'] is False
        assert result['body']['answer']['citations'][0]['page'] == 1
        with pytest.raises(DocumentScopeUnavailable):
            app.query_service.document_scope_reader.read([doc['doc_id']])
        assert call(web,'/api/query','POST',{'question':'What is needed?', 'doc_ids':[doc['doc_id']]},scope=[])['status'] == 404
        release.set()
        assert wait_job(web,job)['ready']
        doc = call(web,'/api/documents')['body']['documents'][0]
        assert doc['coverage_complete'] and not doc['unread_pages']
    finally:
        release.set(); app.close()


def test_existing_review_upload_is_automatically_read_after_upgrade(tmp_path, mixed_pdf, monkeypatch):
    old, web = application(tmp_path, enable_ocr=False, progressive_ocr=False)
    try:
        legacy = wait_job(web, upload(web, mixed_pdf.read_bytes()))
        assert legacy['state'] == 'review_required' and not legacy['ready']
    finally:
        old.close()
    attempts = []
    def recognize(_path, **options):
        attempts.append(options['page_numbers'])
        return OCRDocument([{'page':2,'text':'Automatically recovered original scan.'}], 'test',.99,.1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    app, web = application(tmp_path)
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            docs = call(web, '/api/documents')['body']['documents']
            if docs and docs[0]['ready'] and docs[0]['coverage_complete']:
                break
            time.sleep(.01)
        assert docs[0]['ready'] and docs[0]['coverage_complete']
        assert attempts == [[2]]
        source = tmp_path/'store'/'uploads'/legacy['document_id']/'Mixed.pdf'
        assert source.read_bytes() == mixed_pdf.read_bytes()
        assert len(app.jobs.list()) == 2
    finally:
        app.close()


def test_automatic_upgrade_preserves_a_cancelled_job(tmp_path, mixed_pdf, monkeypatch):
    old, web = application(tmp_path, enable_ocr=False, progressive_ocr=False)
    try:
        legacy = wait_job(web, upload(web, mixed_pdf.read_bytes()))
        # A durable queued intent cancelled before scheduling must stay stopped.
        source = tmp_path/'store'/'uploads'/legacy['document_id']/'Mixed.pdf'
        job_id, created = old.jobs.prepare_upload(source, legacy['document_id'], **old.ingestion_defaults)
        # Same old options deduplicate, so create a distinct explicit intent.
        if not created:
            job_id, created = old.jobs.prepare_upload(source, legacy['document_id'],
                **{**old.ingestion_defaults, 'ocr_max_pages':1})
        assert created and old.jobs.cancel(job_id)
    finally:
        old.close()
    def forbidden(*args, **kwargs):
        pytest.fail('Cancelled upload must not restart OCR')
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', forbidden)
    app, web = application(tmp_path)
    try:
        # Join only the bounded startup scan, never the OCR worker itself.
        time.sleep(.1)
        assert len(app.jobs.list()) == 2
        assert app.jobs.get(job_id)['state'] == 'cancelled'
        assert not call(web, '/api/documents')['body']['documents'][0]['ready']
    finally:
        app.close()


def scanned_pages(path, count):
    with fitz.open() as original:
        original.new_page().insert_text((72,72),'A distinct scanned regulation line.',fontsize=18)
        image = original[0].get_pixmap().tobytes('png')
    with fitz.open() as pdf:
        for _ in range(count):
            page = pdf.new_page(); page.insert_image(page.rect,stream=image)
        pdf.save(path)


def test_automatic_batches_keep_original_page_numbers_and_never_repeat_finished_ocr(tmp_path,monkeypatch):
    source = tmp_path/'source.pdf'; scanned_pages(source,7)
    batches = []
    def recognize(_path, **options):
        batches.append(options['page_numbers'])
        return OCRDocument([{'page':n,'text':f'Recognized source page {n}.'} for n in options['page_numbers']], 'test', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    app, web = application(tmp_path)
    try:
        job = wait_job(web,upload(web,source.read_bytes()))
        assert job['ready'] and job['state'] == 'succeeded'
        assert batches == [[1,2],[3,4],[5,6],[7]]
        parsed = (tmp_path/'store'/job['document_id']/'parsed.md').read_text(encoding='utf-8')
        assert all(f'## Page {n}\nRecognized source page {n}.' in parsed for n in range(1,8))
        second = call(web,'/api/documents/upload','POST',raw=source.read_bytes(),headers={'CONTENT_TYPE':'application/pdf','HTTP_X_FILENAME':'Again.pdf'})
        assert second['body']['duplicate'] and len(batches) == 4
    finally: app.close()


def test_batch_checkpoint_survives_restart_and_rejects_changed_bytes(tmp_path,monkeypatch):
    source=tmp_path/'source.pdf'; scanned_pages(source,4)
    batches=[]
    def recognize(_path,**options):
        batches.append(options['page_numbers'])
        return OCRDocument([{'page':n,'text':f'Original page {n}.'} for n in options['page_numbers']], 'test', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf',recognize)
    kwargs=dict(store_dir=tmp_path/'store',allow_partial=True,enable_ocr=True,ocr_max_pages=2)
    first=ingest_document(source,**kwargs)
    assert first.status=='partial' and first.metadata['unread_pages']==[3,4]
    second=ingest_document(source,**kwargs)
    assert second.status=='succeeded' and batches==[[1,2],[3,4]]
    # Corruption is not used as an OCR observation on a later partial resume.
    source2=tmp_path/'other.pdf'; scanned_pages(source2,5)
    partial=ingest_document(source2,**kwargs)
    cache=tmp_path/'store'/partial.doc_id/'ocr-pages.json'
    raw=cache.read_text(encoding='utf-8').replace('Original page','Injected page')
    cache.write_text(raw,encoding='utf-8')
    repaired=ingest_document(source2,**kwargs)
    assert batches[-1]==[1,2]
    assert all('Injected' not in c.content for c in repaired.chunks)


def test_ocr_unavailable_keeps_readable_snapshot_and_stops_without_retry_loop(tmp_path,mixed_pdf,monkeypatch):
    attempts=[]
    def unavailable(*args,**kwargs):
        attempts.append(1); raise OCRUnavailable('offline engine unavailable')
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf',unavailable)
    app,web=application(tmp_path)
    try:
        job=wait_job(web,upload(web,mixed_pdf.read_bytes()))
        assert job['state']=='review_required' and job['ready'] and attempts==[1]
        doc=call(web,'/api/documents')['body']['documents'][0]
        assert doc['ready'] and doc['unread_pages']==[2]
        assert doc['coverage_complete'] is False
        assert job['retryable']
        monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', lambda *a,**kw:
            OCRDocument([{'page':2,'text':'Recovered scan text.'}], 'test',.99,.1))
        retried = call(web,'/api/jobs/'+job['job_id']+'/retry','POST',{})
        assert retried['status'] == 200
        assert wait_job(web,retried['body']['job']['job_id'])['ready']
        assert call(web,'/api/documents')['body']['documents'][0]['coverage_complete']
    finally:app.close()


def test_a_deadline_keeps_verified_completed_pages_for_the_next_pass(tmp_path,monkeypatch):
    source=tmp_path/'source.pdf'; scanned_pages(source,3)
    attempts=[]
    def recognize(_path,**options):
        attempts.append(options['page_numbers'])
        if len(attempts)==1:
            raise OCRLimitExceeded('OCR time limit exceeded',partial=OCRDocument(
                [{'page':1,'text':'Completed page before deadline.'}], 'test',.99,.1))
        return OCRDocument([{'page':n,'text':f'Remaining page {n}.'} for n in options['page_numbers']], 'test',.99,.1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf',recognize)
    app,web=application(tmp_path)
    try:
        job=wait_job(web,upload(web,source.read_bytes()))
        assert job['ready'] and attempts==[[1,2],[2,3]]
        parsed=(tmp_path/'store'/job['document_id']/'parsed.md').read_text(encoding='utf-8')
        assert 'Completed page before deadline.' in parsed
    finally:app.close()
