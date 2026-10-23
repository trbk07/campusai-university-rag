import hashlib
import json
from pathlib import Path
import sqlite3
from threading import Event
from concurrent.futures import ThreadPoolExecutor

import pytest

from campusai.api import CampusAIApplication
from campusai.ingestion import jobs as module
from campusai.ingestion.jobs import IngestionJobManager, JobQueueFull, JobStoreUnavailable
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app
from tests.test_web_documents import call, pdf_bytes, LocalEvidenceLLM


def runtime(root,*,defaults=None):
    provider = LocalEvidenceLLM()
    service = CampusAIQueryService(HybridRetriever(root/'index'),GroundedAnswerGenerator(provider),default_mode='bm25')
    provider.evidence = lambda:service.last_retrieval[0]
    manager = IngestionJobManager(journal_path=root/'operations/jobs.sqlite3')
    app = CampusAIApplication(service,jobs=manager,ingestion_defaults={
        'store_dir':root/'store','index_dir':root/'index','dense_model':'fallback-hash-256',**(defaults or {})})
    return make_wsgi_app(app),app


def upload(web,data,name='Enrollment.pdf'):
    return call(web,'/api/documents/upload','POST',raw=data,
                headers={'CONTENT_TYPE':'application/pdf','HTTP_X_FILENAME':name})


def finish(app,job_id):
    future = app.jobs._futures.get(job_id)
    if future: future.result(timeout=10)
    return app.jobs.get(job_id)


def test_queue_full_creates_neither_upload_file_nor_job_and_duplicate_still_works(tmp_path,monkeypatch):
    entered,release = Event(),Event()
    original = module.ingest_document
    def pause(*args,**kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'ingest_document',pause)
    web,app = runtime(tmp_path)
    data = [pdf_bytes('Enrollment '+str(i)+' requires approval.') for i in range(4)]
    try:
        first = upload(web,data[0])['body']['job']['job_id']
        assert entered.wait(2)
        second = upload(web,data[1])['body']['job']['job_id']
        third = upload(web,data[2])['body']['job']['job_id']
        before = {p.relative_to(tmp_path) for p in (tmp_path/'store/uploads').rglob('*')}
        rejected = upload(web,data[3])
        assert rejected['status']==429 and rejected['body']['error_code']=='ingestion_busy'
        assert rejected['headers']['Retry-After']=='2'
        assert len(app.jobs.list())==3
        assert before=={p.relative_to(tmp_path) for p in (tmp_path/'store/uploads').rglob('*')}
        duplicate = upload(web,data[0])
        assert duplicate['status']==200 and duplicate['body']['duplicate']
        assert duplicate['body']['job']['job_id']==first
        assert app.jobs.stats()['active_workers']==1 and app.jobs.stats()['pending_work_items']==2
        assert app.jobs.cancel(second)
        fourth = upload(web,data[3])['body']['job']['job_id']
        assert app.jobs.stats()['pending_work_items']==2
        release.set()
        assert all(finish(app,j)['ready'] for j in (first,third,fourth))
    finally:
        release.set()
        app.close()


def test_cancel_spam_cannot_accumulate_unbounded_executor_work(tmp_path,monkeypatch):
    entered,release = Event(),Event()
    original = module.ingest_document
    def pause(*args,**kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'ingest_document',pause)
    manager = IngestionJobManager()
    first_source = tmp_path/'first.pdf';first_source.write_bytes(pdf_bytes())
    try:
        manager.submit(first_source,store_dir=tmp_path/'store')
        assert entered.wait(2)
        for index in range(40):
            source=tmp_path/f'{index}.pdf';source.write_bytes(pdf_bytes(f'Original content {index}.'))
            job_id=manager.submit(source,store_dir=tmp_path/'store')
            assert manager._executor.pending_count==1
            assert manager.cancel(job_id)
            assert manager._executor.pending_count==0
        assert manager.stats()['active_workers']==1 and manager.stats()['cancelled']==40
    finally:
        release.set();manager.shutdown()


def test_duplicate_concurrent_http_uploads_share_one_job_and_source(tmp_path,monkeypatch):
    entered,release=Event(),Event()
    original=module.ingest_document
    def pause(*args,**kwargs):
        entered.set();assert release.wait(5)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'ingest_document',pause)
    web,app=runtime(tmp_path)
    data=pdf_bytes()
    try:
        with ThreadPoolExecutor(max_workers=8) as workers:
            responses=list(workers.map(lambda _:upload(web,data),range(12)))
        ids={r['body']['job']['job_id'] for r in responses}
        assert len(ids)==1 and len(app.jobs.list())==1
        assert len(list((tmp_path/'store/uploads').rglob('*.pdf')))==1
        release.set();assert finish(app,next(iter(ids)))['ready']
    finally:
        release.set();app.close()


def test_retry_restores_original_options_and_delete_is_durable(tmp_path,monkeypatch):
    original=module.ingest_document
    def fail(*_args,**_kwargs):raise OSError('private-path/credential-detail')
    monkeypatch.setattr(module,'ingest_document',fail)
    web,app=runtime(tmp_path,defaults={'max_mb':3,'max_pages':2,'batch_size':2})
    first=upload(web,pdf_bytes())['body']['job']['job_id']
    assert finish(app,first)['retryable']
    original_options=app.jobs._options[first]
    app.close()
    monkeypatch.setattr(module,'ingest_document',original)
    web,app=runtime(tmp_path,defaults={'dense_model':'must-not-be-used-for-retry','max_pages':1})
    try:
        listing=call(web,'/api/documents')['body']
        assert listing['jobs'][0]['job_id']==first and 'private-path' not in json.dumps(listing)
        response=call(web,f'/api/jobs/{first}/retry','POST',{})
        assert response['status']==200
        retry_id=response['body']['job']['job_id']
        assert app.jobs._options[retry_id]==original_options
        job=finish(app,retry_id)
        assert job['ready'] and job['retry_count']==1
        doc_id=job['document_id']
        assert call(web,f'/api/documents/{doc_id}','DELETE')['status']==200
    finally:app.close()
    web,app=runtime(tmp_path)
    try:
        assert call(web,'/api/documents')['body']['documents']==[]
        assert app.jobs.list()==[]
        assert not (tmp_path/'store/uploads'/doc_id).exists()
        assert finish(app,upload(web,pdf_bytes())['body']['job']['job_id'])['ready']
    finally:app.close()


def test_lifetime_owner_lock_does_not_recover_a_still_running_owner(tmp_path,monkeypatch):
    entered,release=Event(),Event();original=module.ingest_document
    def pause(*args,**kwargs):
        entered.set();assert release.wait(5)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'ingest_document',pause)
    path=tmp_path/'jobs.sqlite3';source=tmp_path/'source.pdf';source.write_bytes(pdf_bytes())
    manager=IngestionJobManager(journal_path=path)
    try:
        job_id=manager.submit(source,store_dir=tmp_path/'store')
        assert entered.wait(2)
        with pytest.raises(JobStoreUnavailable):IngestionJobManager(journal_path=path)
        assert manager.get(job_id)['state']=='running'
    finally:release.set();manager.shutdown()
    reopened=IngestionJobManager(journal_path=path)
    try:assert reopened.get(job_id)['state']=='succeeded'
    finally:reopened.shutdown()


def test_journal_failure_blocks_admission_and_readiness_without_creating_upload(tmp_path,monkeypatch):
    web,app=runtime(tmp_path)
    def fail(*_args):raise JobStoreUnavailable('private-storage-detail')
    monkeypatch.setattr(app.jobs._journal,'save',fail)
    try:
        response=upload(web,pdf_bytes())
        assert response['status']==503 and response['body']['error_code']=='job_store_unavailable'
        assert app.jobs.list()==[] and not list((tmp_path/'store').rglob('*.pdf'))
        ready=call(web,'/ready')
        assert ready['status']==503 and not ready['body']['ingestion_available']
        assert b'private-storage-detail' not in response['raw']
    finally:app.close()


def test_changed_source_cannot_be_retried_as_the_original_document(tmp_path,monkeypatch):
    original=module.ingest_document
    monkeypatch.setattr(module,'ingest_document',lambda *_a,**_k:(_ for _ in ()).throw(OSError('failure')))
    web,app=runtime(tmp_path)
    try:
        job_id=upload(web,pdf_bytes())['body']['job']['job_id'];finish(app,job_id)
        Path(app.jobs.get(job_id)['source_path']).write_bytes(pdf_bytes('Changed source.'))
        monkeypatch.setattr(module,'ingest_document',original)
        response=call(web,f'/api/jobs/{job_id}/retry','POST',{})
        assert response['status']==409 and response['body']['error_code']=='job_source_changed'
        assert len(app.jobs.list())==1
    finally:app.close()


@pytest.mark.parametrize('mode',['corrupt','future_schema','bad_payload'])
def test_corrupt_or_unsupported_journal_fails_closed(tmp_path,mode):
    path=tmp_path/'jobs.sqlite3'
    if mode=='corrupt':path.write_bytes(b'not a database')
    else:
        manager=IngestionJobManager(journal_path=path);manager.shutdown()
        with sqlite3.connect(path) as db:
            if mode=='future_schema':db.execute('PRAGMA user_version=99')
            else:db.execute('INSERT INTO jobs VALUES (?,?,?)',('bad','{}','{}'))
    with pytest.raises(JobStoreUnavailable):IngestionJobManager(journal_path=path)


def test_long_upload_filename_keeps_pdf_extension(tmp_path):
    web,app=runtime(tmp_path)
    try:
        response=upload(web,pdf_bytes(),'x'*300+'.pdf')
        job=finish(app,response['body']['job']['job_id'])
        assert job['ready'] and Path(job['source_path']).suffix=='.pdf'
        assert len(Path(job['source_path']).name)<=160
    finally:app.close()


def test_same_pdf_in_different_corpora_has_distinct_job_identity(tmp_path):
    source=tmp_path/'source.pdf';source.write_bytes(pdf_bytes())
    manager=IngestionJobManager(journal_path=tmp_path/'jobs.sqlite3')
    try:
        first=manager.submit(source,store_dir=tmp_path/'store-a',index_dir=tmp_path/'index-a')
        second=manager.submit(source,store_dir=tmp_path/'store-b',index_dir=tmp_path/'index-b')
        assert first!=second
        manager._futures[first].result(timeout=5);manager._futures[second].result(timeout=5)
        assert manager.get(first)['ready'] and manager.get(second)['ready']
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        assert all((tmp_path/name/digest/'dense.json').is_file() for name in ('index-a','index-b'))
    finally:manager.shutdown()
