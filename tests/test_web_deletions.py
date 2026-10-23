"""Deletion covers uploads that have not reached the document registry yet."""
import time
import threading

import pytest

from tests.test_web_documents import call, pdf_bytes, runtime, upload_ready


def wait_for(predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        assert time.monotonic() < deadline, 'deletion did not complete'
        time.sleep(.02)


@pytest.mark.parametrize('error', [OSError('failed'), RuntimeError('job_cancelled')])
def test_delete_unregistered_failed_or_cancelled_upload(runtime, monkeypatch, error):
    from campusai.ingestion import jobs
    web, application, root = runtime

    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(jobs, 'ingest_document', fail)
    job = upload_ready(web)
    assert job['state'] in {'failed', 'cancelled'}
    assert call(web, '/api/documents')['body']['documents'] == []
    doc_id = job['document_id']
    assert call(web, f'/api/documents/{doc_id}', 'DELETE', scope=[])['status'] == 404
    assert (root/'store/uploads'/doc_id).exists()
    assert call(web, f'/api/documents/{doc_id}', 'DELETE')['status'] == 200
    assert not (root/'store/uploads'/doc_id).exists()
    assert application.jobs.list() == []


@pytest.mark.parametrize('stage', ['parsing', 'indexing'])
def test_running_delete_returns_before_worker_stops_and_prevents_republication(runtime, monkeypatch, stage):
    from campusai.ingestion import jobs
    from campusai.retrieval import index_builder
    web, application, root = runtime
    entered, release = threading.Event(), threading.Event()
    original = jobs.ingest_document if stage == 'parsing' else index_builder.build_document_indexes

    def pause(*args, **kwargs):
        result = original(*args, **kwargs) if stage == 'indexing' else None
        entered.set()
        assert release.wait(5)
        if stage == 'parsing':
            kwargs['progress']('parsing', .5)
            return original(*args, **kwargs)
        return result

    monkeypatch.setattr(jobs if stage == 'parsing' else index_builder,
                        'ingest_document' if stage == 'parsing' else 'build_document_indexes', pause)
    data = pdf_bytes()
    response = call(web, '/api/documents/upload', 'POST', raw=data,
                    headers={'CONTENT_TYPE':'application/pdf'})
    doc_id = response['body']['job']['document_id']
    assert entered.wait(3)
    try:
        deletion = call(web, f'/api/documents/{doc_id}', 'DELETE')
        assert deletion['status'] == 202 and deletion['body']['deleting']
        assert not release.is_set()
        assert (root/'store/.deletions'/doc_id).is_file()
        listing = call(web, '/api/documents')['body']
        assert all(job['deleting'] for job in listing['jobs'])
        assert all(not doc['ready'] for doc in listing['documents'])
        assert call(web, f'/api/documents/{doc_id}/file')['status'] == 409
        assert call(web, '/api/query', 'POST', {'question':'Enrollment?', 'doc_ids':[doc_id]})['status'] in {404,409}
        assert call(web, '/api/documents/upload', 'POST', raw=data,
                    headers={'CONTENT_TYPE':'application/pdf'})['status'] == 409
    finally:
        release.set()
    wait_for(lambda: not application.jobs.list())
    wait_for(lambda: not (root/'store/.deletions'/doc_id).exists())
    assert not (root/'store/uploads'/doc_id).exists()
    assert not (root/'store'/doc_id).exists()
    assert not (root/'index'/doc_id).exists()
    assert call(web, '/api/documents')['body']['documents'] == []
    monkeypatch.setattr(jobs if stage == 'parsing' else index_builder,
                        'ingest_document' if stage == 'parsing' else 'build_document_indexes', original)
    assert upload_ready(web)['ready']


def test_delete_queued_upload_does_not_wait_for_another_pdf(runtime, monkeypatch):
    from campusai.ingestion import jobs
    web, application, root = runtime
    entered, release = threading.Event(), threading.Event()
    original = jobs.ingest_document

    def pause(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(jobs, 'ingest_document', pause)
    headers = {'CONTENT_TYPE':'application/pdf'}
    first = call(web, '/api/documents/upload', 'POST', raw=pdf_bytes('First source.'), headers=headers)
    assert entered.wait(2)
    second = call(web, '/api/documents/upload', 'POST', raw=pdf_bytes('Second source.'), headers=headers)
    doc_id = second['body']['job']['document_id']
    try:
        assert second['body']['job']['state'] == 'queued'
        assert call(web, f'/api/documents/{doc_id}', 'DELETE')['status'] == 202
        wait_for(lambda: not (root/'store/.deletions'/doc_id).exists())
        assert not (root/'store/uploads'/doc_id).exists()
        assert len(application.jobs.list()) == 1
        assert application.jobs.list()[0]['job_id'] == first['body']['job']['job_id']
    finally:
        release.set()


def test_durable_delete_intent_is_recovered_when_web_app_reopens(runtime):
    from campusai.web import make_wsgi_app
    web, application, root = runtime
    job = upload_ready(web)
    doc_id = job['document_id']
    intents = root/'store/.deletions'
    intents.mkdir()
    (intents/doc_id).write_text('')
    reopened = make_wsgi_app(application)
    wait_for(lambda: not (intents/doc_id).exists())
    assert call(reopened, '/api/documents')['body']['documents'] == []
    assert application.jobs.list() == []


def test_delete_during_answer_returns_immediately_and_keeps_source_until_answer_finishes(runtime):
    web, application, root = runtime
    doc_id = upload_ready(web)['document_id']
    entered, release = threading.Event(), threading.Event()
    result = {}

    def answer(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        assert (root/'store/uploads'/doc_id).is_dir()
        return {'ok':True, 'answer':{'citations':[]}}
    application.query = answer
    thread = threading.Thread(target=lambda: result.update(call(web, '/api/query', 'POST',
        {'question':'What approval is required?', 'doc_ids':[doc_id]})))
    thread.start()
    assert entered.wait(2)
    try:
        assert call(web, f'/api/documents/{doc_id}', 'DELETE')['status'] == 202
        assert call(web, '/api/documents')['status'] == 200
        assert (root/'store/uploads'/doc_id).is_dir()
    finally:
        release.set()
        thread.join(3)
    assert result['status'] == 200
    wait_for(lambda: not (root/'store/.deletions'/doc_id).exists())
    assert not (root/'store/uploads'/doc_id).exists()


def test_delete_failure_is_visible_and_can_be_retried(runtime, monkeypatch):
    from campusai.web_documents import WebDocuments
    web, _, root = runtime
    doc_id = upload_ready(web)['document_id']
    original = WebDocuments._delete_artifacts

    def fail(*args):
        raise OSError('private filesystem error')
    monkeypatch.setattr(WebDocuments, '_delete_artifacts', fail)
    response = call(web, f'/api/documents/{doc_id}', 'DELETE')
    assert response['status'] == 503
    assert 'private' not in response['raw'].decode()
    doc = call(web, '/api/documents')['body']['documents'][0]
    assert doc['deleting'] and doc['delete_failed'] and not doc['ready']
    monkeypatch.setattr(WebDocuments, '_delete_artifacts', original)
    assert call(web, f'/api/documents/{doc_id}', 'DELETE')['status'] == 200
    assert not (root/'store/.deletions'/doc_id).exists()
