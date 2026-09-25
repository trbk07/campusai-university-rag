import time

import fitz

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


def test_warmup_skips_deterministic_fallback_model():
    assert warm_retrieval_models(dense_model="fallback-hash-256") == []
