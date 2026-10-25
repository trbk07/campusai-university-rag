"""OCR backend selection must preserve native pages, cache identity and old journals."""
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from campusai.ingestion.background.state import job_identity, legacy_job_identity
from campusai.ingestion.jobs import IngestionJobManager, JobStoreUnavailable
from campusai.ingestion.ocr import OCRDocument
from campusai.ingestion.ocr_assets import validate_tesseract_assets
from campusai.ingestion.pipeline import ingest_document
from tests.test_mixed_pdf import mixed_pdf


def test_backend_upgrade_reprocesses_cached_ocr_instead_of_returning_old_text(mixed_pdf,tmp_path,monkeypatch):
    calls=[]
    def recognize(*args,**kwargs):
        backend=kwargs['backend'];calls.append(backend)
        return OCRDocument([{'page':2,'text':backend+' enrollment requires advisor approval.'}],
                           'test-'+backend,.99,.01)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf',recognize)
    first=ingest_document(mixed_pdf,store_dir=tmp_path/'store',enable_ocr=True)
    second=ingest_document(mixed_pdf,store_dir=tmp_path/'store',enable_ocr=True,ocr_backend='tesseract')
    assert calls==['rapidocr','tesseract'] and not second.cached
    assert second.metadata['parser_version']=='tesseract-vie-eng-v1'
    text=(tmp_path/'store'/second.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert 'Native prerequisite' in text and 'tesseract enrollment' in text
    assert 'rapidocr enrollment' not in text
    assert second.doc_id==first.doc_id and second.page_count==3


@pytest.mark.parametrize('legacy_function',[job_identity,legacy_job_identity])
def test_pre_backend_journal_survives_upgrade_retry_and_second_restart(tmp_path,mixed_pdf,legacy_function):
    ledger=tmp_path/'jobs.sqlite3'
    manager=IngestionJobManager(journal_path=ledger)
    identifier=manager.submit(mixed_pdf,store_dir=tmp_path/'store')
    manager._futures[identifier].result(timeout=5);manager.shutdown()
    with sqlite3.connect(ledger) as db:
        payload,options=db.execute('select payload,options from jobs').fetchone()
        job,old=json.loads(payload),json.loads(options)
        old.pop('ocr_backend');old.pop('ocr_data_dir')
        old_identity=legacy_function(job['source_sha256'],old)
        job.update(identity=old_identity,state='failed',retryable=True)
        db.execute('update jobs set payload=?,options=?',(json.dumps(job),json.dumps(old)))
    manager=IngestionJobManager(journal_path=ledger)
    try:
        assert manager.get(identifier)['identity']==old_identity
        retry=manager.retry(identifier)
        manager._futures[retry].result(timeout=5)
        assert retry!=identifier and manager._options[retry]['ocr_backend']=='rapidocr'
    finally:manager.shutdown()
    manager=IngestionJobManager(journal_path=ledger)
    try:assert len(manager.list())==2 and manager.get(identifier)['identity']==old_identity
    finally:manager.shutdown()


def test_tampered_language_asset_fails_before_launching_ocr(tmp_path):
    (tmp_path/'vie.traineddata').write_bytes(b'wrong model')
    with pytest.raises(ValueError):validate_tesseract_assets(tmp_path)


def test_real_tesseract_preserves_mixed_pages_and_records_pinned_models(mixed_pdf,tmp_path):
    data=Path('.cache/ocr/tessdata_fast')
    try:identity=validate_tesseract_assets(data)
    except ValueError:pytest.skip('optional local tesserocr and pinned language models not installed')
    original=hashlib.sha256(mixed_pdf.read_bytes()).hexdigest()
    document=ingest_document(mixed_pdf,store_dir=tmp_path/'store',enable_ocr=True,
        ocr_backend='tesseract',ocr_data_dir=data)
    assert document.status=='succeeded' and document.metadata['ocr']['page_numbers']==[2]
    assert document.metadata['ocr']['model_identity']['model_sha256']==identity['model_sha256']
    text=(tmp_path/'store'/document.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert 'Native prerequisite' in text and 'advisor approval' in text
    assert document.page_count==3 and hashlib.sha256(mixed_pdf.read_bytes()).hexdigest()==original
