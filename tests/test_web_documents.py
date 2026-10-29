"""Real PDF/worker/index/HTTP lifecycle, with a local deterministic test LLM."""
import io
import json
import threading
import time
from pathlib import Path

import fitz
import pytest

from campusai.api import CampusAIApplication
from campusai.ingestion.jobs import IngestionJobManager
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app, ASSETS


def call(web, path, method='GET', payload=None, raw=None, scope=None, headers=None):
    data = raw if raw is not None else json.dumps(payload).encode() if payload is not None else b''
    environ = {'PATH_INFO':path, 'REQUEST_METHOD':method, 'CONTENT_LENGTH':str(len(data)), 'wsgi.input':io.BytesIO(data), **(headers or {})}
    if scope is not None:
        environ['campusai.authorized_doc_ids'] = scope
    result = {}
    def respond(status, response_headers):
        result.update(status=int(status.split()[0]), headers=dict(response_headers))
    result['raw'] = b''.join(web(environ, respond))
    if result['headers']['Content-Type'].startswith('application/json'):
        result['body'] = json.loads(result['raw'])
    return result


def pdf_bytes(text='Enrollment requires approval from the academic advisor. Students must complete all prerequisite courses before enrollment.'):
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72,72), text)
        return pdf.tobytes()


class LocalEvidenceLLM:
    """Test-only provider that quotes an actual retrieval chunk verbatim."""
    model = 'local-ui-test'
    def generate_json(self, prompt, **kwargs):
        # Grounding's context has stable SOURCE/CHUNK/PAGE headers. Tests use
        # captured actual retrieval below to create schema-valid source claims.
        result = self.evidence()
        quote = 'Enrollment requires approval from the academic advisor.'
        return {'answer':quote, 'confidence':'high', 'abstained':False,
            'claims':[{'claim_id':'c1','text':quote,'citation_ids':[result.chunk_id]}],
            'citations':[{'chunk_id':result.chunk_id,'page':result.page,'quote':quote}]}


@pytest.fixture
def runtime(tmp_path):
    retriever = HybridRetriever(tmp_path/'index')
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(None), default_mode='bm25')
    jobs = IngestionJobManager()
    application = CampusAIApplication(service, jobs=jobs, ingestion_defaults={'store_dir':tmp_path/'store', 'index_dir':tmp_path/'index', 'dense_model':'fallback-hash-256'})
    web = make_wsgi_app(application)
    yield web, application, tmp_path
    application.close()


def upload_ready(web, data=None):
    response = call(web, '/api/documents/upload', 'POST', raw=data or pdf_bytes(), headers={'CONTENT_TYPE':'application/pdf','HTTP_X_FILENAME':'Enrollment.pdf'})
    assert response['status'] == 202, response
    job_id = response['body']['job']['job_id']
    deadline = time.monotonic()+10
    while time.monotonic() < deadline:
        job = call(web, '/api/jobs/'+job_id)['body']['job']
        if job['state'] in {'succeeded','review_required','failed','cancelled'}:
            return job
        time.sleep(.02)
    pytest.fail('job did not terminate')


def test_real_upload_query_source_feedback_delete_and_reupload(runtime):
    web, application, root = runtime
    job = upload_ready(web)
    assert job['ready'] and job['index_status'] == 'ready'
    doc_id = job['document_id']
    listing = call(web,'/api/documents')['body']
    assert len(listing['documents']) == 1
    doc = listing['documents'][0]
    assert doc['ready'] and doc['name'] == 'Enrollment.pdf' and doc['page_count'] == 1
    assert 'source_path' not in json.dumps(listing)
    service = application.query_service
    evidence = service.retriever.search('Enrollment approval academic advisor', doc_ids=[doc_id], mode='bm25')
    assert evidence
    llm = LocalEvidenceLLM()
    llm.evidence = lambda: evidence[0]
    service.answer_generator.llm = llm
    answer = call(web,'/api/query','POST', {'question':'What approval is required for enrollment?', 'doc_ids':[doc_id]})
    assert answer['status'] == 200, answer
    public = answer['body']['answer']
    assert not public['abstained'], public
    assert public['citations'][0]['doc_id'] == doc_id
    assert public['citations'][0]['page'] == 1
    source = call(web,f'/api/documents/{doc_id}/file')
    assert source['raw'].startswith(b'%PDF-')
    with fitz.open(stream=source['raw'], filetype='pdf') as pdf:
        assert public['citations'][0]['quote'] in pdf[0].get_text()
    response_id = answer['headers']['X-Request-ID']
    assert call(web,'/api/feedback','POST', {'response_id':response_id,'kind':'helpful'})['status'] == 200
    feedback = json.loads((root/'store/feedback.jsonl').read_text().strip())
    assert feedback['response_id'] == response_id and 'question' not in feedback
    assert call(web,f'/api/documents/{doc_id}','DELETE')['status'] == 200
    assert call(web,f'/api/documents/{doc_id}/file')['status'] == 404
    assert call(web,'/api/documents')['body']['documents'] == []
    assert doc_id not in service.retriever._indexes
    assert not (root/'store'/doc_id).exists() and not (root/'index'/doc_id).exists()
    assert not (root/'store/uploads'/doc_id).exists()
    assert json.loads((root/'index/manifest.json').read_text())['documents'] == []
    assert call(web,'/api/feedback','POST', {'response_id':response_id,'kind':'incorrect'})['status'] == 400
    assert upload_ready(web)['ready']


def test_document_listing_snapshots_job_history_once_for_multiple_pdfs(runtime, monkeypatch):
    web, application, _root = runtime
    first = upload_ready(web, pdf_bytes('First document contains an enrollment rule.'))
    second = upload_ready(web, pdf_bytes('Second document contains another enrollment rule.'))
    assert first['ready'] and second['ready']
    original = application.jobs_snapshot
    snapshots = []

    def counted_snapshot():
        snapshots.append(True)
        return original()

    monkeypatch.setattr(application, 'jobs_snapshot', counted_snapshot)
    response = call(web, '/api/documents')
    assert response['status'] == 200
    assert len(response['body']['documents']) == 2
    assert all(document['ready'] for document in response['body']['documents'])
    assert len(snapshots) == 1
    snapshots.clear()
    query = call(web, '/api/query', 'POST', {'question':'What is the enrollment rule?',
        'doc_ids':[first['document_id'], second['document_id']]})
    assert query['status'] == 200
    assert len(snapshots) == 1


def test_contained_normalizes_root_after_a_windows_directory_is_created(tmp_path):
    from campusai.web_documents import contained

    store = tmp_path / 'store'
    unresolved_store = store.resolve()
    store.mkdir()
    registry = store / 'registry.json'
    registry.write_text('{}', encoding='utf-8')
    assert contained(unresolved_store, registry) == registry.resolve()


def test_two_batches_of_five_pdfs_accumulate_and_can_be_queried_together(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from campusai.web_documents import WebDocuments

    index = tmp_path / 'index'
    manager = IngestionJobManager(max_workers=3, max_pending=8)
    failures = []
    original_update = manager._update

    def track_failure(job_id, **values):
        if values.get('state') == 'failed':
            import traceback
            failures.append(traceback.format_exc())
        return original_update(job_id, **values)
    monkeypatch.setattr(manager, '_update', track_failure)
    service = CampusAIQueryService(HybridRetriever(index), GroundedAnswerGenerator(None), default_mode='bm25')
    application = CampusAIApplication(service, jobs=manager,
        ingestion_defaults={'store_dir':tmp_path/'store','index_dir':index,'dense_model':'fallback-hash-256'})
    web = make_wsgi_app(application, max_concurrent_queries=4)
    simultaneous = Barrier(5)
    original_upload = WebDocuments.upload

    def synchronize_uploads(documents, data, name, environ):
        simultaneous.wait(timeout=3)
        return original_upload(documents, data, name, environ)

    monkeypatch.setattr(WebDocuments, 'upload', synchronize_uploads)
    def send(number):
        return call(web, '/api/documents/upload', 'POST', raw=pdf_bytes(f'Independent batch source {number}.'),
            headers={'CONTENT_TYPE':'application/pdf','HTTP_X_FILENAME':f'document-{number}.pdf'})

    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = list(pool.map(send, range(5)))
            responses += list(pool.map(send, range(5, 10)))
        assert all(response['status'] == 202 for response in responses), responses
        job_ids = [response['body']['job']['job_id'] for response in responses]
        deadline = time.monotonic() + 15
        jobs = [manager.get(job_id) for job_id in job_ids]
        while any(job['state'] not in {'succeeded','failed','cancelled','review_required'} for job in jobs):
            if time.monotonic() >= deadline:
                pytest.fail('five-file upload batch did not finish indexing')
            time.sleep(.02)
            jobs = [manager.get(job_id) for job_id in job_ids]
        assert all(job['state'] == 'succeeded' and job['ready'] for job in jobs), failures
        manifest = json.loads((index/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['documents'] == sorted(job['document_id'] for job in jobs)
        assert len(manifest['document_manifests']) == 10
        doc_ids = [job['document_id'] for job in jobs]
        assert len(call(web, '/api/documents')['body']['documents']) == 10
        answer = call(web, '/api/query', 'POST', {'question':'How many pages in all selected documents?',
            'language':'en', 'doc_ids':doc_ids,
            'history':[{'role':'user','content':'I have just added another batch of PDFs.'}]})
        assert answer['status'] == 200, answer
        assert sum(doc['page_count'] for doc in answer['body']['document_info']['documents']) == 10
        assert len(answer['body']['document_info']['documents']) == 10
        vietnamese = call(web, '/api/query', 'POST', {'question':'Tổng số trang của tất cả tài liệu đã chọn?',
            'doc_ids':doc_ids})
        assert vietnamese['status'] == 200, vietnamese
        assert len(vietnamese['body']['document_info']['documents']) == 10
        assert not vietnamese['body']['answer']['abstained']
    finally:
        application.close()


def test_query_is_not_blocked_while_pdf_upload_body_is_received(runtime):
    web, application, _ = runtime
    data = pdf_bytes()
    body_reading = threading.Event()
    release_body = threading.Event()
    query_finished = threading.Event()
    upload_result = {}
    query_result = {}

    class SlowUploadBody:
        def read(self, size=-1):
            body_reading.set()
            assert release_body.wait(5)
            return data[:size]

    def request(path, method, payload, result):
        try:
            result.update(call(web, path, method, payload=payload))
        except BaseException as error:  # Preserve background-thread failures for the assertion.
            result['error'] = error

    application.query = lambda *args, **kwargs: {'ok': True, 'answer': {'citations': []}}
    upload_environ = {
        'PATH_INFO': '/api/documents/upload', 'REQUEST_METHOD': 'POST',
        'CONTENT_LENGTH': str(len(data)), 'CONTENT_TYPE': 'application/pdf',
        'wsgi.input': SlowUploadBody(),
    }

    def upload():
        try:
            status = {}
            def respond(value, headers):
                status['code'] = int(value.split()[0])
            result = b''.join(web(upload_environ, respond))
            upload_result.update(status=status['code'], body=json.loads(result))
        except BaseException as error:
            upload_result['error'] = error

    upload_thread = threading.Thread(target=upload)
    upload_thread.start()
    try:
        assert body_reading.wait(2), 'upload never began reading its request body'
        query_thread = threading.Thread(target=lambda: (
            request('/api/query', 'POST', {'question': 'test query'}, query_result),
            query_finished.set(),
        ))
        query_thread.start()
        assert query_finished.wait(2), 'query waited for the PDF request body to finish'
        query_thread.join(2)
        assert 'error' not in query_result
        assert query_result['status'] == 200
    finally:
        release_body.set()
        upload_thread.join(5)
    assert not upload_thread.is_alive()
    assert 'error' not in upload_result
    assert upload_result['status'] == 202


def test_scope_is_enforced_for_listing_source_delete_jobs_query_and_feedback(runtime):
    web, _, _ = runtime
    job = upload_ready(web); doc_id = job['document_id']
    assert call(web,'/api/documents',scope=[])['body']['documents'] == []
    assert call(web,'/api/documents',scope=[])['body']['jobs'] == []
    for path, method, payload in [(f'/api/documents/{doc_id}','GET',None),(f'/api/documents/{doc_id}/file','GET',None),(f'/api/documents/{doc_id}','DELETE',None),(f'/api/jobs/{job["job_id"]}','GET',None),('/api/query','POST',{'question':'Enrollment?', 'doc_ids':[doc_id]})]:
        assert call(web,path,method,payload,scope=[])['status'] == 404
    answer = call(web,'/api/query','POST',{'question':'Enrollment?', 'doc_ids':[doc_id]})
    assert call(web,'/api/feedback','POST',{'response_id':answer['headers']['X-Request-ID'],'kind':'helpful'},scope=[])['status'] == 404
    assert call(web,'/api/documents/upload','POST',raw=pdf_bytes(),scope=[],headers={'CONTENT_TYPE':'application/pdf'})['status'] == 403
    assert call(web,'/api/query','POST',{'question':'Enrollment?', 'doc_ids':[]})['status'] == 400


@pytest.mark.parametrize('data',[b'not-pdf',b'%PDF-broken'])
def test_invalid_pdf_rejected_without_leaking_paths(runtime,data):
    web, _, root = runtime
    response = call(web,'/api/documents/upload','POST',raw=data,headers={'CONTENT_TYPE':'application/pdf'})
    assert response['status'] == 400
    assert str(root).encode() not in response['raw']
    assert not list((root/'store/uploads').rglob('*.pdf')) if (root/'store/uploads').exists() else True


def test_encrypted_oversized_duplicate_review_and_missing_source(runtime):
    web, application, root = runtime
    with fitz.open() as pdf:
        pdf.new_page()
        encrypted = pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='test', user_pw='test')
    assert call(web,'/api/documents/upload','POST',raw=encrypted,headers={'CONTENT_TYPE':'application/pdf'})['status'] == 400
    assert call(web,'/api/documents/upload','POST',raw=b'x',headers={'CONTENT_TYPE':'application/pdf','CONTENT_LENGTH':str(51*1048576)})['status'] == 413
    data = pdf_bytes()
    job = upload_ready(web,data)
    duplicate = call(web,'/api/documents/upload','POST',raw=data,headers={'CONTENT_TYPE':'application/pdf'})
    assert duplicate['body']['duplicate']
    Path(application.ingestion_defaults['store_dir'],'uploads',job['document_id'],'Enrollment.pdf').unlink()
    assert call(web,f'/api/documents/{job["document_id"]}/file')['status'] == 404
    review = upload_ready(web,pdf_bytes(''))
    assert review['state'] == 'review_required' and not review['ready']
    assert call(web,'/api/query','POST',{'question':'Anything?', 'doc_ids':[review['document_id']]})['status'] == 409


def test_asset_allowlist_cross_origin_and_feedback_validation(runtime):
    web, _, _ = runtime
    for asset in ASSETS:
        response = call(web,'/assets/'+asset)
        assert response['status'] == 200 and response['raw']
        assert response['headers']['X-Content-Type-Options'] == 'nosniff'
    for path in ['/assets/../web.py','/assets/pages/index.html','/api/documents/../../.env']:
        assert call(web,path)['status'] == 404
    assert call(web,'/api/feedback','POST',{'kind':'arbitrary','response_id':'unknown'})['status'] == 400
    assert call(web,'/api/documents/a','DELETE',headers={'HTTP_ORIGIN':'https://attacker.example','HTTP_HOST':'localhost:8000'})['status'] == 403


def test_modified_pdf_cannot_be_served_as_the_original_citation(runtime):
    web, _, root = runtime
    job = upload_ready(web)
    doc_id = job['document_id']
    (root/'store/uploads'/doc_id/'Enrollment.pdf').write_bytes(pdf_bytes('A different source document.'))
    assert call(web,f'/api/documents/{doc_id}/file')['status'] == 404


def test_runtime_capability_reports_configuration_without_disclosing_credentials(runtime):
    web, application, _ = runtime
    assert call(web,'/api/documents')['body']['runtime'] == {'ai_configured':False,'query_streaming':False,'query_timeout_ms':45000}
    application.query_service.answer_generator.llm = type('LLM',(),{'api_key':'private-credential-do-not-publish'})()
    response = call(web,'/api/documents')
    assert response['body']['runtime'] == {'ai_configured':True,'query_streaming':False,'query_timeout_ms':45000}
    assert b'private-credential' not in response['raw']


def test_source_preview_locates_quote_inside_multi_page_chunk_and_enforces_scope(runtime):
    web, _, _ = runtime
    with fitz.open() as pdf:
        pdf.new_page().insert_text((72,72),'Stacks and queues: an introduction.')
        pdf.new_page().insert_text((72,72),'A stack uses LIFO, last in first out.')
        data = pdf.tobytes()
    doc_id = upload_ready(web,data)['document_id']
    payload = {'quote':'A stack uses LIFO, last in first out.','page_range':[1,2]}
    result = call(web,f'/api/documents/{doc_id}/locate','POST',payload)
    assert result['status'] == 200 and result['body']['matched'] and result['body']['page'] == 2
    assert call(web,f'/api/documents/{doc_id}/locate','POST',payload,scope=[])['status'] == 404
    missing = call(web,f'/api/documents/{doc_id}/locate','POST',dict(payload,quote='Unsupported text'))
    assert not missing['body']['matched'] and missing['body']['page'] == 1
    assert call(web,f'/api/documents/{doc_id}/locate','POST',dict(payload,page_range=[0,999]))['status'] == 400


def test_failed_job_is_redacted_and_can_retry_through_the_existing_worker(runtime, monkeypatch):
    web, _, _ = runtime
    from campusai.ingestion import jobs
    original = jobs.ingest_document
    def fail(*args, **kwargs):
        raise OSError('private/path/API-key-placeholder')
    monkeypatch.setattr(jobs, 'ingest_document', fail)
    job = upload_ready(web)
    assert job['state'] == 'failed' and job['retryable']
    assert 'private/' not in json.dumps(job)
    monkeypatch.setattr(jobs, 'ingest_document', original)
    retry = call(web,f'/api/jobs/{job["job_id"]}/retry','POST',{})
    assert retry['status'] == 200
    job_id = retry['body']['job']['job_id']
    deadline = time.monotonic()+5
    while time.monotonic() < deadline:
        value = call(web,f'/api/jobs/{job_id}')['body']['job']
        if value['state'] not in {'queued','running'}:
            break
        time.sleep(.01)
    assert value['ready']
    assert call(web,f'/api/jobs/{job_id}/cancel','POST',{})['status'] == 409


def test_cooperative_job_cancel_is_scoped_and_reports_actual_terminal_state(runtime, monkeypatch):
    web, _, _ = runtime
    from threading import Event
    from campusai.ingestion import jobs
    entered, release = Event(), Event()
    def pause(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        kwargs['progress']('parsing',.5)
        raise AssertionError('cancellation should interrupt at the progress checkpoint')
    monkeypatch.setattr(jobs,'ingest_document',pause)
    response = call(web,'/api/documents/upload','POST',raw=pdf_bytes(),headers={'CONTENT_TYPE':'application/pdf'})
    job_id = response['body']['job']['job_id']
    assert entered.wait(2)
    try:
        assert call(web,f'/api/jobs/{job_id}/cancel','POST',{},scope=[])['status'] == 404
        assert call(web,f'/api/jobs/{job_id}/cancel','POST',{})['status'] == 200
    finally:
        release.set()
    deadline = time.monotonic()+5
    while time.monotonic()<deadline:
        job = call(web,f'/api/jobs/{job_id}')['body']['job']
        if job['state'] == 'cancelled':
            break
        time.sleep(.01)
    assert job['state'] == 'cancelled' and not job['ready']


def test_unmanaged_source_and_symlink_never_read_or_delete_outside_store(runtime):
    web, _, root = runtime
    from campusai.documents.registry import DocumentRegistry
    from campusai.schemas import Document
    outside = root/'private.pdf'; outside.write_bytes(pdf_bytes())
    registry = DocumentRegistry(root/'store/registry.json')
    doc_id = 'e'*64
    registry.add(Document(doc_id,str(outside),1))
    assert not call(web,'/api/documents')['body']['documents'][0]['file_available']
    assert call(web,f'/api/documents/{doc_id}/file')['status'] == 404
    assert call(web,f'/api/documents/{doc_id}','DELETE')['status'] == 200
    assert outside.exists()
    try:
        (root/'store'/doc_id).symlink_to(root, target_is_directory=True)
    except OSError:
        # Windows junctions do not require the symlink creation privilege.
        import os
        import subprocess
        if os.name != 'nt':
            raise
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(root/'store'/doc_id), str(root)], capture_output=True)
        assert result.returncode == 0, 'Cannot create symlink or junction fixture'
    registry.add(Document(doc_id,str(outside),1))
    assert call(web,f'/api/documents/{doc_id}','DELETE')['status'] == 404
    assert outside.exists()
    (root/'store'/doc_id).rmdir()
