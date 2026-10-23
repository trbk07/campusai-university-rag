"""Mixed native/scan PDFs must never silently omit unread pages."""
import fitz
import pytest

from campusai.ingestion.docling_parser import parse_pdf
from campusai.ingestion.pipeline import ingest_document
from campusai.ingestion.ocr import OCRDocument
from campusai.ingestion.ocr import ocr_pdf, OCRLimitExceeded


@pytest.fixture
def mixed_pdf(tmp_path):
    source = tmp_path / 'mixed.pdf'
    with fitz.open() as original:
        page = original.new_page()
        page.insert_text((72,72), 'Scanned enrollment requires advisor approval.', fontsize=18)
        image = page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')
    with fitz.open() as pdf:
        pdf.new_page().insert_text((72,72), 'Native prerequisite courses must be completed before enrollment.')
        page = pdf.new_page()
        page.insert_image(page.rect, stream=image)
        pdf.new_page()  # A genuinely blank page does not require OCR.
        pdf.save(source)
    return source


def test_mixed_scan_page_is_detected_but_blank_page_is_not(mixed_pdf):
    pages = parse_pdf(mixed_pdf)
    assert [page['page'] for page in pages if page.get('requires_ocr')] == [2]
    assert 'Native prerequisite' in pages[0]['text']


def test_mixed_scan_without_ocr_cannot_be_marked_complete(mixed_pdf, tmp_path):
    doc = ingest_document(mixed_pdf, store_dir=tmp_path/'store')
    assert doc.status == 'review_required'
    assert doc.review_reason == 'ocr_required'
    assert doc.metadata['unread_pages'] == [2]


def test_selective_ocr_preserves_native_page_and_physical_page_ids(mixed_pdf, tmp_path, monkeypatch):
    def recognize(path, **options):
        assert options['page_numbers'] == [2]
        return OCRDocument([{'page':2,'text':'Scanned enrollment requires advisor approval.'}],
                           'test-ocr', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    doc = ingest_document(mixed_pdf, store_dir=tmp_path/'store', enable_ocr=True)
    assert doc.status == 'succeeded'
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert 'Native prerequisite' in text and 'Scanned enrollment' in text
    assert '## Page 2\nScanned enrollment' in text
    assert doc.metadata['ocr']['page_numbers'] == [2]
    assert 'ocr_used' in doc.metadata['warnings']


def test_empty_ocr_result_cannot_hide_unread_page(mixed_pdf, tmp_path, monkeypatch):
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', lambda *a, **kw:
        OCRDocument([{'page':2,'text':''}], 'test-ocr', 0, .1))
    doc = ingest_document(mixed_pdf, store_dir=tmp_path/'store', enable_ocr=True)
    assert doc.status == 'review_required' and doc.metadata['unread_pages'] == [2]


def test_old_success_cache_cannot_hide_a_scan_page(mixed_pdf, tmp_path):
    import json
    store = tmp_path/'store'
    doc = ingest_document(mixed_pdf, store_dir=store)
    meta = store/doc.doc_id/'meta.json'
    old = json.loads(meta.read_text(encoding='utf-8'))
    old['status'] = 'succeeded'
    old['metadata'].pop('text_coverage_version')
    meta.write_text(json.dumps(old), encoding='utf-8')
    repaired = ingest_document(mixed_pdf, store_dir=store)
    assert not repaired.cached and repaired.status == 'review_required'
    assert repaired.metadata['unread_pages'] == [2]


def test_selected_ocr_budget_applies_to_selected_physical_pages(mixed_pdf, monkeypatch):
    import sys
    from types import SimpleNamespace
    calls = []
    class Engine:
        def __call__(self, image):
            calls.append(image.shape)
            return [[None, 'recognized scan', .99]], None
    monkeypatch.setitem(sys.modules, 'rapidocr_onnxruntime', SimpleNamespace(RapidOCR=Engine))
    result = ocr_pdf(mixed_pdf, max_pages=1, page_numbers=[2])
    assert [page['page'] for page in result.pages] == [2] and len(calls) == 1
    with pytest.raises(OCRLimitExceeded):
        ocr_pdf(mixed_pdf, max_pages=1)
    for invalid in ([0], [4], [2,2], [True], []):
        with pytest.raises(ValueError):
            ocr_pdf(mixed_pdf, page_numbers=invalid)


def test_scan_plus_blank_page_only_ocrs_the_scan(mixed_pdf, tmp_path, monkeypatch):
    path = tmp_path/'scan-and-blank.pdf'
    with fitz.open(mixed_pdf) as original, fitz.open() as pdf:
        pdf.insert_pdf(original, from_page=1, to_page=2)
        pdf.save(path)
    def recognize(path, **options):
        assert options['page_numbers'] == [1]
        return OCRDocument([{'page':1,'text':'Advisor approval is required.'}], 'test-ocr', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    assert ingest_document(path, store_dir=tmp_path/'store', enable_ocr=True).status == 'succeeded'


def test_uploaded_mixed_pdf_cannot_enter_query_scope_while_unread(mixed_pdf, tmp_path):
    from campusai.api import CampusAIApplication
    from campusai.ingestion.jobs import IngestionJobManager
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app
    from tests.test_web_documents import upload_ready, call
    app = CampusAIApplication(
        CampusAIQueryService(HybridRetriever(tmp_path/'index'), GroundedAnswerGenerator(None)),
        jobs=IngestionJobManager(), ingestion_defaults={'store_dir':tmp_path/'store',
            'index_dir':tmp_path/'index', 'dense_model':'fallback-hash-256'})
    try:
        web = make_wsgi_app(app)
        job = upload_ready(web, mixed_pdf.read_bytes())
        assert job['state'] == 'review_required' and not job['ready']
        doc_id = job['document_id']
        assert not call(web, '/api/documents')['body']['documents'][0]['ready']
        result = call(web, '/api/query', 'POST', {'question':'What requires approval?', 'doc_ids':[doc_id]})
        assert result['status'] == 409 and result['body']['error_code'] == 'document_not_ready'
        # Emulate an older parser's success flag and retained incomplete index.
        # A restart/list/query must not trust it or silently serve partial data.
        from campusai.documents.registry import DocumentRegistry
        from campusai.schemas import Document
        registry = DocumentRegistry(tmp_path/'store'/'registry.json')
        old = registry.get(doc_id)
        old['status'], old['review_reason'] = 'succeeded', None
        old['metadata'].pop('text_coverage_version')
        old['metadata'].pop('unread_pages')
        registry.add(Document.from_dict(old))
        app.jobs.forget_document(doc_id)
        index = tmp_path/'index'/doc_id
        index.mkdir(parents=True, exist_ok=True)
        for name in ('bm25.json', 'dense.json'):
            (index/name).write_text('{}')
        audited = call(web, '/api/documents')['body']['documents'][0]
        assert not audited['ready'] and audited['unread_pages'] == [2]
        assert audited['review_reason'] == 'ocr_required'
        assert call(web, '/api/query', 'POST', {'question':'What requires approval?',
            'doc_ids':[doc_id]})['status'] == 409
    finally:
        app.close()
