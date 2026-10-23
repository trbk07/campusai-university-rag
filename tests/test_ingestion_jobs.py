import hashlib
import threading
import time

import fitz
import pytest

from campusai.ingestion.jobs import IngestionJobManager
from campusai.retrieval.model_runtime import warm_retrieval_models


def test_ingestion_job_is_background_deduplicated_and_observable(tmp_path):
    source = tmp_path / "report.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Revenue 2024\nDoanh thu 2024")
    document.save(source)
    document.close()

    manager = IngestionJobManager(max_workers=1)
    try:
        first = manager.submit(source, store_dir=tmp_path / "store")
        second = manager.submit(source, store_dir=tmp_path / "store")
        assert first == second
        deadline = time.time() + 3
        status = manager.get(first)
        while status and status["state"] not in {"succeeded", "failed"} and time.time() < deadline:
            time.sleep(0.01)
            status = manager.get(first)
        assert status is not None
        assert status["state"] == "succeeded"
        assert status["progress"] == 1.0
        assert status["document_id"]
    finally:
        manager.shutdown()


def test_failed_ingestion_can_be_retried(tmp_path):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a pdf")

    manager = IngestionJobManager(max_workers=1)
    try:
        first = manager.submit(source, store_dir=tmp_path / "store")
        deadline = time.time() + 3
        status = manager.get(first)
        while status and status["state"] not in {"succeeded", "failed"} and time.time() < deadline:
            time.sleep(0.01)
            status = manager.get(first)
        assert status is not None and status["state"] == "failed"

        second = manager.submit(source, store_dir=tmp_path / "store")
        assert second != first
    finally:
        manager.shutdown()


def test_upload_activation_returns_while_worker_verifies_source(tmp_path):
    source = tmp_path / 'uploads' / 'source.pdf'
    source.parent.mkdir()
    with fitz.open() as pdf:
        pdf.new_page().insert_text((72, 72), 'A source whose digest is verified by the worker.')
        pdf.save(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manager = IngestionJobManager(max_workers=1)
    worker_hash_started, release_worker_hash = threading.Event(), threading.Event()
    activation_returned = threading.Event()
    activation_errors = []
    original_hash = manager._sha256

    def slow_hash(path):
        worker_hash_started.set()
        assert release_worker_hash.wait(5)
        return original_hash(path)

    manager._sha256 = slow_hash
    try:
        job_id, created = manager.prepare_upload(source, digest, store_dir=tmp_path / 'store')
        assert created

        def activate():
            try:
                manager.activate(job_id)
            except BaseException as error:
                activation_errors.append(error)
            finally:
                activation_returned.set()

        thread = threading.Thread(target=activate)
        thread.start()
        assert worker_hash_started.wait(2), 'worker did not verify the staged upload'
        assert activation_returned.wait(2), 'upload activation performed the worker hash synchronously'
        assert not activation_errors
    finally:
        release_worker_hash.set()
        if 'thread' in locals():
            thread.join(5)
        manager.shutdown()
    assert not thread.is_alive()


def test_two_pdf_jobs_process_and_publish_indexes_concurrently(tmp_path, monkeypatch):
    from threading import Event, Lock
    import json
    import campusai.ingestion.jobs as compatibility
    from campusai.ingestion.pipeline import ingest_document as real_ingest

    sources = []
    for number in range(2):
        source = tmp_path / f'document-{number}.pdf'
        with fitz.open() as pdf:
            pdf.new_page().insert_text((72, 72), f'Independent source for document {number}.')
            pdf.save(source)
        sources.append(source)

    both_started, guard = Event(), Lock()
    started = []

    def concurrent_ingest(*args, **kwargs):
        with guard:
            started.append(args[0])
            if len(started) == 2:
                both_started.set()
        assert both_started.wait(5), 'the second PDF waited for the first ingestion worker'
        return real_ingest(*args, **kwargs)

    monkeypatch.setattr(compatibility, 'ingest_document', concurrent_ingest)
    store, index = tmp_path / 'store', tmp_path / 'index'
    manager = IngestionJobManager(max_workers=2, max_pending=2)
    try:
        job_ids = [manager.submit(source, store_dir=store, index_dir=index,
            dense_model='fallback-hash-256') for source in sources]
        deadline = time.monotonic() + 15
        states = [manager.get(job_id) for job_id in job_ids]
        while any(job['state'] not in {'succeeded', 'failed', 'cancelled'} for job in states):
            if time.monotonic() >= deadline:
                pytest.fail('parallel PDF jobs did not finish')
            time.sleep(.02)
            states = [manager.get(job_id) for job_id in job_ids]
        assert [job['state'] for job in states] == ['succeeded', 'succeeded']
        assert len(started) == 2
        assert all((index / job['document_id'] / 'dense.json').is_file() for job in states)
        manifest = json.loads((index / 'manifest.json').read_text(encoding='utf-8'))
        assert manifest['documents'] == sorted(job['document_id'] for job in states)
        assert len(manifest['document_manifests']) == 2
    finally:
        manager.shutdown()


def test_warmup_skips_deterministic_fallback_model():
    assert warm_retrieval_models(dense_model="fallback-hash-256") == []
