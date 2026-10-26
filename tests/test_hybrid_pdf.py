"""Native headers and footers must not hide raster text on the same page."""
import hashlib
import json

import fitz
import pytest

from campusai.ingestion.docling_parser import parse_pdf
from campusai.ingestion.ocr import OCRDocument
from campusai.ingestion.pipeline import ingest_document


@pytest.fixture
def hybrid_pdf(tmp_path):
    path = tmp_path / 'native-header-raster-body.pdf'
    with fitz.open() as raster:
        page = raster.new_page(width=500, height=500)
        page.insert_text((24, 100), 'Enrollment needs advisor approval.', fontsize=20)
        page.insert_text((24, 180), 'The course carries 4 credits.', fontsize=20)
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes('png')
    with fitz.open() as pdf:
        page = pdf.new_page(width=600, height=800)
        page.insert_text((50, 50), '1. Native catalog 2031', fontsize=20)
        page.insert_text((50, 75), '7. Registration requires approval', fontsize=12)
        page.insert_image(fitz.Rect(50, 100, 550, 600), stream=image)
        page.insert_text((50, 750), 'Native footer 7', fontsize=12)
        pdf.save(path)
    return path


def test_native_header_does_not_hide_raster_body(hybrid_pdf):
    page = parse_pdf(hybrid_pdf)[0]
    assert page['requires_ocr'], 'Native header alone does not cover the raster body'
    assert 'Native catalog 2031' in page['text'] and 'advisor' not in page['text']


def test_hybrid_without_ocr_is_review_required(hybrid_pdf, tmp_path):
    doc = ingest_document(hybrid_pdf, store_dir=tmp_path/'store')
    assert doc.status == 'review_required' and doc.metadata['unread_pages'] == [1]
    assert not doc.chunks


def test_hybrid_ocr_preserves_native_lines_and_physical_reading_order(hybrid_pdf, tmp_path, monkeypatch):
    with fitz.open(hybrid_pdf) as source:
        header = list(source[0].search_for('Native catalog 2031')[0])
        footer = list(source[0].search_for('Native footer 7')[0])
    def recognize(*args, **kwargs):
        assert kwargs['page_numbers'] == [1] and kwargs['include_layout']
        return OCRDocument([{'page': 1, 'text': 'Native catelog 2031\nEnrollment needs advisor approval.\nNative footer 7',
            'lines': [{'text': 'Native catelog 2031', 'bbox': header},
                      {'text': 'Enrollment needs advisor approval.', 'bbox': [74, 185, 450, 205]},
                      {'text': 'Native footer 7', 'bbox': footer}]}], 'fixture', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    doc = ingest_document(hybrid_pdf, store_dir=tmp_path/'store', enable_ocr=True)
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert doc.status == 'succeeded'
    assert text.index('Native catalog 2031') < text.index('advisor approval') < text.index('Native footer 7')
    assert 'catelog' not in text and text.count('Native footer 7') == 1
    assert any('Native catalog 2031' in chunk.heading_path for chunk in doc.chunks)
    assert not any('Registration requires approval' in chunk.heading_path for chunk in doc.chunks)


def test_scanned_columns_keep_decoder_order_instead_of_interleaving_rows(hybrid_pdf):
    from campusai.ingestion.pipeline import _merge_hybrid_page
    native = parse_pdf(hybrid_pdf)[0]
    lines = [{'text': text, 'bbox': box} for text, box in [
        ('Left column first', [70, 150, 250, 170]), ('Left column second', [70, 250, 250, 270]),
        ('Right column first', [300, 150, 500, 170]), ('Right column second', [300, 250, 500, 270])]]
    merged = _merge_hybrid_page(native, {'text': '\n'.join(row['text'] for row in lines), 'lines': lines})
    assert merged['text'].index('Left column second') < merged['text'].index('Right column first')
    assert merged['text'].index('Native catalog') < merged['text'].index('Left column first')
    assert merged['text'].index('Right column second') < merged['text'].index('Native footer')


def test_overlapping_image_regions_do_not_repeat_the_same_fact(hybrid_pdf, tmp_path):
    from pathlib import Path
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    data = Path('.cache/ocr/tessdata_fast')
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('optional pinned local OCR models unavailable')
    source = tmp_path/'overlaid-same-image.pdf'
    with fitz.open(hybrid_pdf) as pdf:
        page = pdf[0]
        page.insert_image(fitz.Rect(50, 100, 550, 600), xref=page.get_images()[0][0])
        pdf.save(source)
    assert len(parse_pdf(source)[0]['ocr_regions']) == 1
    doc = ingest_document(source, store_dir=tmp_path/'store', enable_ocr=True,
                          ocr_backend='tesseract', ocr_data_dir=data)
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert doc.status == 'succeeded' and text.count('4 credits') == 1


def test_version_one_cache_cannot_hide_hybrid_body(hybrid_pdf, tmp_path):
    store = tmp_path/'store'
    doc = ingest_document(hybrid_pdf, store_dir=store)
    meta = store/doc.doc_id/'meta.json'
    old = json.loads(meta.read_text(encoding='utf-8'))
    old['metadata']['text_coverage_version'] = 1
    old.update(status='succeeded', review_reason=None)
    old['metadata'].pop('unread_pages', None)
    meta.write_text(json.dumps(old), encoding='utf-8')
    repaired = ingest_document(hybrid_pdf, store_dir=store)
    assert not repaired.cached and repaired.status == 'review_required'


def test_real_hybrid_tesseract_preserves_source_and_recovers_body(hybrid_pdf, tmp_path):
    from pathlib import Path
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    data = Path('.cache/ocr/tessdata_fast')
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('optional pinned local OCR models unavailable')
    before = hashlib.sha256(hybrid_pdf.read_bytes()).hexdigest()
    doc = ingest_document(hybrid_pdf, store_dir=tmp_path/'store', enable_ocr=True,
                          ocr_backend='tesseract', ocr_data_dir=data)
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert doc.status == 'succeeded' and 'advisor approval' in text and '4 credits' in text
    assert 'Native catalog 2031' in text and 'Native footer 7' in text
    assert hashlib.sha256(hybrid_pdf.read_bytes()).hexdigest() == before


def test_real_rapid_hybrid_uses_visible_regions_and_keeps_native_text(hybrid_pdf, tmp_path):
    doc = ingest_document(hybrid_pdf, store_dir=tmp_path/'store', enable_ocr=True)
    assert doc.status == 'succeeded'
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert 'advisor approval' in text and '4 credits' in text and 'Native catalog 2031' in text
    assert doc.metadata['ocr']['image_audits'][0]['regions'][0]['outcome'] == 'recognized'


def test_real_vietnamese_hybrid_keeps_native_accents_and_recovers_credits(tmp_path):
    from pathlib import Path
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    from scripts.operations.benchmark_ocr_quality import edits, normalized
    font = Path('C:/Windows/Fonts/arial.ttf')
    data = Path('.cache/ocr/tessdata_fast')
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('optional pinned local OCR models unavailable')
    if not font.is_file(): pytest.skip('Vietnamese test font unavailable')
    source = tmp_path/'vietnamese-hybrid.pdf'
    with fitz.open() as body:
        page = body.new_page(width=500, height=500)
        page.insert_font(fontname='source-font', fontfile=str(font))
        page.insert_text((24, 100), 'Sinh viên cần được cố vấn học tập đồng ý.', fontname='source-font', fontsize=18)
        page.insert_text((24, 180), 'Học phần có 4 tín chỉ.', fontname='source-font', fontsize=18)
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes('png')
    with fitz.open() as pdf:
        page = pdf.new_page(width=600, height=800)
        page.insert_font(fontname='source-font', fontfile=str(font))
        page.insert_text((50, 50), 'Kế hoạch học tập năm 2031', fontname='source-font', fontsize=20)
        page.insert_image(fitz.Rect(50, 100, 550, 600), stream=image)
        page.insert_text((50, 750), 'Trang gốc 7', fontname='source-font', fontsize=12)
        pdf.save(source)
    doc = ingest_document(source, store_dir=tmp_path/'store', enable_ocr=True,
                          ocr_backend='tesseract', ocr_data_dir=data)
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    gold = normalized('Sinh viên cần được cố vấn học tập đồng ý. Học phần có 4 tín chỉ.')
    body_text = normalized('\n'.join(line for line in text.splitlines() if line.startswith(('Sinh viên', 'Học phần'))))
    assert doc.status == 'succeeded' and '4 tín chỉ' in body_text
    assert 1 - edits(gold, body_text) / len(gold) >= .9  # Original OCR quality gate, not perfect transcription.
    assert normalized(text).count('Kế hoạch học tập năm 2031') == normalized(text).count('Trang gốc 7') == 1
    assert all(row['text'] in text for row in parse_pdf(source)[0]['hybrid_layout'])


def test_recognizing_only_native_header_cannot_hide_unread_body(hybrid_pdf, tmp_path, monkeypatch):
    def recognize(*args, **kwargs):
        with fitz.open(hybrid_pdf) as source:
            box = list(source[0].search_for('Native catalog 2031')[0])
        return OCRDocument([{'page': 1, 'text': 'Native catalog 2031',
            'lines': [{'text': 'Native catalog 2031', 'bbox': box}]}], 'fixture', .99, .1)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    doc = ingest_document(hybrid_pdf, store_dir=tmp_path/'store', enable_ocr=True)
    assert doc.status == 'review_required' and doc.metadata['unread_pages'] == [1]


def test_small_decorative_image_does_not_require_full_page_ocr(hybrid_pdf, tmp_path):
    path = tmp_path/'native-logo.pdf'
    with fitz.open(hybrid_pdf) as source, fitz.open() as pdf:
        image = source[0].get_pixmap().tobytes('png')
        page = pdf.new_page()
        page.insert_text((72, 100), 'All enrollment rules are native text.')
        page.insert_image(fitz.Rect(20, 20, 40, 45), stream=image)
        pdf.save(path)
    assert not parse_pdf(path)[0]['requires_ocr']


def test_cropped_textless_background_is_audited_without_blocking_native_content(tmp_path):
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    data = Path('.cache/ocr/tessdata_fast')
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('optional pinned local OCR models unavailable')
    stream = BytesIO();Image.new('RGB', (100, 1000), '#eeeeee').save(stream, format='PNG')
    source = tmp_path/'clipped-background.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page(width=600, height=800)
        page.insert_image(fitz.Rect(450, -200, 550, 800), stream=stream.getvalue())
        page.insert_text((50, 100), 'Native evidence remains complete and unchanged.')
        pdf.save(source)
    assert parse_pdf(source)[0]['requires_ocr']
    doc = ingest_document(source, store_dir=tmp_path/'store', enable_ocr=True,
                          ocr_backend='tesseract', ocr_data_dir=data)
    assert doc.status == 'succeeded'
    assert doc.metadata['ocr']['image_audits'][0]['regions'][0]['outcome'] == 'no_detected_text'
    assert 'Native evidence remains complete' in (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')


def test_image_soft_mask_cannot_reveal_invisible_bitmap_text(tmp_path):
    from io import BytesIO
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    data = Path('.cache/ocr/tessdata_fast')
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('optional pinned local OCR models unavailable')
    image = Image.new('RGB', (800, 300), 'white')
    ImageDraw.Draw(image).text((30, 80), 'INVISIBLE TEST TEXT Z9', fill='black', font=ImageFont.load_default(size=45))
    stream = BytesIO();image.save(stream, format='PNG')
    mask = BytesIO();Image.new('L', image.size, 0).save(mask, format='PNG')
    source = tmp_path/'masked-image.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page(width=800, height=600)
        page.insert_text((50, 50), 'Only this native content is visible.')
        page.insert_image(fitz.Rect(0, 100, 800, 400), stream=stream.getvalue(), mask=mask.getvalue())
        pdf.save(source)
    doc = ingest_document(source, store_dir=tmp_path/'store', enable_ocr=True,
                          ocr_backend='tesseract', ocr_data_dir=data)
    assert doc.status == 'succeeded'
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert 'Only this native content is visible.' in text and 'INVISIBLE' not in text and 'Z9' not in text


def test_native_watermark_inside_image_is_not_body_coverage(hybrid_pdf, tmp_path):
    path = tmp_path/'hybrid-watermark.pdf'
    with fitz.open(hybrid_pdf) as pdf:
        pdf[0].insert_text((70, 150), 'DRAFT', fontsize=14)
        pdf.save(path)
    assert parse_pdf(path)[0]['requires_ocr']


def test_distributed_native_text_layer_over_scan_is_not_forced_through_ocr(tmp_path):
    path = tmp_path/'searchable-scan.pdf'
    lines = [(20, y, 'Native evidence covers this exact raster line at position ' + str(i))
             for i, y in enumerate((30, 250, 480), 1)]
    with fitz.open() as original:
        page = original.new_page(width=500, height=500)
        for x, y, text in lines: page.insert_text((x, y), text, fontsize=16)
        image = page.get_pixmap().tobytes('png')
    with fitz.open() as pdf:
        page = pdf.new_page(width=500, height=500)
        page.insert_image(page.rect, stream=image)
        for x, y, text in lines: page.insert_text((x, y), text, fontsize=16, render_mode=3)
        pdf.save(path)
    assert not parse_pdf(path)[0]['requires_ocr']


@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
def test_rapid_layout_returns_unrotated_pdf_coordinates(hybrid_pdf, tmp_path, monkeypatch, rotation):
    import sys
    from types import SimpleNamespace
    from campusai.ingestion.ocr import ocr_pdf
    path = tmp_path/f'rotated-{rotation}.pdf'
    expected = fitz.Rect(74, 185, 450, 205)
    with fitz.open(hybrid_pdf) as pdf:
        pdf[0].set_rotation(rotation)
        rendered = expected * pdf[0].rotation_matrix
        pdf.save(path)
    class Engine:
        def __init__(self, **kwargs): pass
        def __call__(self, image):
            r = rendered * fitz.Matrix(1.5, 1.5)
            return [[[[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1]],
                     'Body from scanned region', .99]], None
    monkeypatch.setitem(sys.modules, 'rapidocr_onnxruntime', SimpleNamespace(RapidOCR=Engine))
    result = ocr_pdf(path, include_layout=True)
    assert result.pages[0]['lines'][0]['bbox'] == pytest.approx(list(expected))


def test_old_successful_ocr_does_not_require_reprocessing_already_covered_pages(hybrid_pdf, tmp_path):
    from campusai.api import CampusAIApplication
    from campusai.documents.registry import DocumentRegistry
    from campusai.schemas import Document
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app
    from tests.test_web_documents import call
    identifier = hashlib.sha256(hybrid_pdf.read_bytes()).hexdigest()
    source = tmp_path/'store/uploads'/identifier/'hybrid.pdf'
    source.parent.mkdir(parents=True);source.write_bytes(hybrid_pdf.read_bytes())
    index = tmp_path/'index'/identifier;index.mkdir(parents=True)
    for name in ('bm25.json', 'dense.json'): (index/name).write_text('{}')
    registry = DocumentRegistry(tmp_path/'store/registry.json')
    doc = Document(identifier, str(source), 1, status='succeeded', metadata={'text_coverage_version': 1,
        'parser_version': 'pymupdf-text-v1'})
    registry.add(doc)
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(tmp_path/'index'), GroundedAnswerGenerator(None)),
        ingestion_defaults={'store_dir': tmp_path/'store', 'index_dir': tmp_path/'index'})
    try:
        web = make_wsgi_app(app)
        result = call(web, '/api/documents')['body']['documents'][0]
        assert not result['ready'] and result['unread_pages'] == [1]
        assert call(web, '/api/query', 'POST', {'question': 'How many pages?', 'doc_ids': [identifier]})['status'] == 409
        # The old full-page OCR covers this physical page even with the old
        # policy marker. A new web instance must not force needless OCR again.
        doc.metadata.update(parser_version='tesseract-vie-eng-v1', ocr={'page_numbers': [1]})
        registry.add(doc)
        fresh = make_wsgi_app(app)
        assert call(fresh, '/api/documents')['body']['documents'][0]['ready']
    finally:
        app.close()


def test_manual_hybrid_ocr_becomes_searchable_without_reupload(hybrid_pdf, tmp_path):
    from pathlib import Path
    from campusai.api import CampusAIApplication
    from campusai.ingestion.jobs import IngestionJobManager
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app
    from tests.test_web_documents import call, upload_ready
    from tests.test_web_ocr import wait_job
    data = Path('.cache/ocr/tessdata_fast')
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('optional pinned local OCR models unavailable')
    retriever = HybridRetriever(tmp_path/'index')
    app = CampusAIApplication(CampusAIQueryService(retriever, GroundedAnswerGenerator(None)),
        jobs=IngestionJobManager(), ingestion_defaults={'store_dir': tmp_path/'store',
            'index_dir': tmp_path/'index', 'dense_model': 'fallback-hash-256',
            'ocr_backend': 'tesseract', 'ocr_data_dir': str(data.resolve())})
    try:
        web = make_wsgi_app(app)
        first = upload_ready(web, hybrid_pdf.read_bytes())
        identifier = first['document_id']
        assert first['state'] == 'review_required' and not first['ready']
        assert call(web, f'/api/documents/{identifier}/ocr', 'POST', {}, scope=[])['status'] == 404
        response = call(web, f'/api/documents/{identifier}/ocr', 'POST', {})
        assert response['status'] == 202
        job = wait_job(web, response['body']['job']['job_id'])
        assert job['state'] == 'succeeded' and job['ready']
        results = retriever.search('4 credits advisor approval', doc_ids=[identifier], mode='bm25')
        assert results and results[0].doc_id == identifier and results[0].page == 1
        assert '4 credits' in results[0].content
        info = call(web, '/api/query', 'POST', {'question': 'How many pages?', 'doc_ids': [identifier]})
        assert info['status'] == 200 and info['body']['document_info']['documents'][0]['page_count'] == 1
        assert call(web, f'/api/documents/{identifier}/file')['raw'] == hybrid_pdf.read_bytes()
        assert len(app.jobs.list()) == 2  # Original review remains in history.
    finally:
        app.close()
