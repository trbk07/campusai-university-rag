from pathlib import Path

import fitz

from campusai.ingestion.ocr import ocr_pdf
from campusai.ingestion.pipeline import delete_document, ingest_document


def test_rapidocr_scanned_page_is_indexable_with_explicit_opt_in(tmp_path):
    source = Path("data/corpus/university/uet_admission_2025.pdf")
    if not source.exists():
        return
    with fitz.open(source) as original:
        scan = fitz.open()
        scan.insert_pdf(original, from_page=0, to_page=0)
        one_page = tmp_path / "scan.pdf"
        scan.save(one_page)
        scan.close()

    ocr_result = ocr_pdf(one_page, max_pages=1, timeout_seconds=60)
    assert ocr_result.engine == "rapidocr-onnxruntime"
    assert ocr_result.pages[0]["text"]
    assert ocr_result.average_confidence > 0.5

    store = tmp_path / "store"
    review = ingest_document(one_page, store_dir=store, enable_ocr=False)
    assert review.status == "review_required"
    document = ingest_document(
        one_page,
        store_dir=store,
        enable_ocr=True,
        ocr_max_pages=1,
        ocr_timeout_seconds=60,
    )
    try:
        assert document.status == "succeeded"
        assert document.metadata["ocr"]["engine"] == "rapidocr-onnxruntime"
        assert document.chunks
    finally:
        assert delete_document(document.doc_id, store_dir=store)
