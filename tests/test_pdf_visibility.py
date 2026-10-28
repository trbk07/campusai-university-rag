"""Invisible OCR cannot establish source text, tables, coverage or readiness."""
import hashlib
import json

import pymupdf as fitz
import pytest

from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION, parse_pdf, visible_page_text
from campusai.ingestion.pipeline import ingest_document


@pytest.fixture
def hidden_scan(tmp_path):
    with fitz.open() as visible:
        page = visible.new_page()
        page.insert_text((45, 100), 'CONTROLLED TEST - Visible course XYZ456 has 6 credits.', fontsize=15)
        page.insert_text((45, 150), 'Registration requires advisor approval.', fontsize=15)
        pixels = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes('png')
    path = tmp_path/'hidden-scan.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page(); page.insert_image(page.rect, stream=pixels)
        for y in (90, 420, 780):
            page.insert_text((35, y), 'FAKE999 HIDDEN OCR SAYS 999 CREDITS ARE REQUIRED.', fontsize=17, render_mode=3)
        pdf.save(path)
    return path


def test_hidden_search_layer_cannot_make_a_scan_look_like_native_text(hidden_scan):
    page = parse_pdf(hidden_scan)[0]
    assert page['text'] == '' and page['requires_ocr']
    assert page['ignored_invisible_spans'] == 3 and page['visible_characters'] == []
    with fitz.open(hidden_scan) as pdf:
        assert 'FAKE999' in pdf[0].get_text()
        assert visible_page_text(pdf[0]) == ''


def test_visible_stroked_text_survives_but_transparent_text_does_not(tmp_path):
    path = tmp_path/'opacity.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), 'Visible filled text')
        page.insert_text((72, 110), 'Visible stroked text', render_mode=1)
        page.insert_text((72, 150), 'FAKE999 transparent', fill_opacity=0)
        pdf.save(path)
    parsed = parse_pdf(path)[0]
    assert 'Visible filled text' in parsed['text'] and 'Visible stroked text' in parsed['text']
    assert 'FAKE999' not in parsed['text']


def test_hidden_scan_requires_review_until_fresh_ocr_and_never_reuses_old_overlay(hidden_scan, tmp_path):
    store = tmp_path/'store'; document = ingest_document(hidden_scan, store_dir=store)
    assert document.status == 'review_required' and document.metadata['unread_pages'] == [1]
    meta = store/document.doc_id/'meta.json'
    old = json.loads(meta.read_text(encoding='utf8'))
    old['metadata'].update(text_coverage_version=2, ocr={'page_numbers': [1]})
    old.update(status='succeeded', review_reason=None)
    meta.write_text(json.dumps(old), encoding='utf8')
    repaired = ingest_document(hidden_scan, store_dir=store)
    assert not repaired.cached and repaired.status == 'review_required'
    assert repaired.metadata['text_coverage_version'] == TEXT_COVERAGE_VERSION and not repaired.chunks


@pytest.mark.parametrize('old_version', [2, 3])
def test_visible_old_cache_upgrades_without_rebuilding_chunks(tmp_path, monkeypatch, old_version):
    path = tmp_path/'native.pdf'
    with fitz.open() as pdf:
        pdf.new_page().insert_text((72, 72), 'Native visible prerequisite policy.')
        pdf.save(path)
    store = tmp_path/'store'; document = ingest_document(path, store_dir=store)
    meta = store/document.doc_id/'meta.json'
    old = json.loads(meta.read_text(encoding='utf8')); old['metadata']['text_coverage_version'] = old_version
    meta.write_text(json.dumps(old), encoding='utf8')
    parsed = store/document.doc_id/'parsed.md'; digest = hashlib.sha256(parsed.read_bytes()).hexdigest()
    def no_rebuild(*args, **kwargs): raise AssertionError('Unaffected native cache must not rebuild')
    monkeypatch.setattr('campusai.ingestion.pipeline.make_chunks', no_rebuild)
    upgraded = ingest_document(path, store_dir=store)
    assert upgraded.cached and upgraded.chunks == document.chunks
    assert hashlib.sha256(parsed.read_bytes()).hexdigest() == digest
    assert json.loads(meta.read_text(encoding='utf8'))['metadata']['text_coverage_version'] == TEXT_COVERAGE_VERSION


def test_real_ocr_reads_visible_pixels_instead_of_hidden_garbage(hidden_scan, tmp_path):
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    data = '.cache/ocr/tessdata_fast'
    try: validate_tesseract_assets(data)
    except ValueError: pytest.skip('Optional pinned OCR assets unavailable')
    before = hashlib.sha256(hidden_scan.read_bytes()).hexdigest()
    doc = ingest_document(hidden_scan, store_dir=tmp_path/'store', enable_ocr=True,
                          ocr_backend='tesseract', ocr_data_dir=data)
    assert doc.status == 'succeeded'
    text = (tmp_path/'store'/doc.doc_id/'parsed.md').read_text(encoding='utf8')
    assert '6 credits' in text and 'advisor approval' in text and 'FAKE999' not in text
    assert hashlib.sha256(hidden_scan.read_bytes()).hexdigest() == before


def test_hybrid_merge_retains_genuine_native_text_and_discards_the_hidden_overlay(hidden_scan, tmp_path):
    from campusai.ingestion.pipeline import _merge_hybrid_page
    path = tmp_path/'mixed-overlay.pdf'
    with fitz.open(hidden_scan) as pdf:
        pdf[0].insert_text((45, 50), 'Visible native header')
        pdf[0].insert_text((45, 800), 'Visible native footer')
        pdf.save(path)
    page = parse_pdf(path)[0]
    assert page['requires_ocr'] and len(page['hybrid_layout']) == 2
    recognized = {'page':1, 'text':'Visible course XYZ456 has 6 credits.',
        'lines':[{'text':'Visible course XYZ456 has 6 credits.', 'bbox':[45, 85, 500, 105]}],
        'image_audit':[{'bbox':region, 'outcome':'recognized'} for region in page['ocr_regions']]}
    merged = _merge_hybrid_page(page, recognized)
    assert 'Visible native header' in merged['text'] and 'Visible native footer' in merged['text']
    assert '6 credits' in merged['text'] and 'FAKE999' not in merged['text']


@pytest.mark.parametrize('old_version, expected_ready', [(2, False), (3, True)])
def test_legacy_visibility_audit_respects_completed_ocr_policy(hidden_scan, tmp_path, old_version, expected_ready):
    from campusai.api import CampusAIApplication
    from campusai.documents.registry import DocumentRegistry
    from campusai.schemas import Document
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app
    from tests.test_web_documents import call
    identifier = hashlib.sha256(hidden_scan.read_bytes()).hexdigest()
    source = tmp_path/'store/uploads'/identifier/'source.pdf'; source.parent.mkdir(parents=True)
    source.write_bytes(hidden_scan.read_bytes())
    index = tmp_path/'index'/identifier; index.mkdir(parents=True)
    for name in ('bm25.json', 'dense.json'): (index/name).write_text('{}')
    DocumentRegistry(tmp_path/'store/registry.json').add(Document(identifier, str(source), 1,
        status='succeeded', metadata={'text_coverage_version': old_version, 'ocr': {'page_numbers': [1]}}))
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(tmp_path/'index'), GroundedAnswerGenerator(None)),
        ingestion_defaults={'store_dir':tmp_path/'store', 'index_dir':tmp_path/'index'})
    try:
        document = call(make_wsgi_app(app), '/api/documents')['body']['documents'][0]
        assert document['ready'] is expected_ready
        assert document['unread_pages'] == ([] if expected_ready else [1])
    finally: app.close()


def test_complete_scope_does_not_publish_hidden_text_as_citation_evidence(tmp_path):
    from campusai.rag.document_scope import RegisteredDocumentScopeReader
    from tests.test_document_scope import source
    store, _identifier, path = source(tmp_path, texts=('Visible policy header.',), image=True)
    with fitz.open(path) as pdf:
        pdf[0].insert_text((72, 200), 'FAKE999 HIDDEN COURSE', render_mode=3)
        updated = pdf.tobytes()
    identifier = hashlib.sha256(updated).hexdigest()
    new_path = path.parent.parent/identifier/'source.pdf'; new_path.parent.mkdir(); new_path.write_bytes(updated)
    (store/'registry.json').write_text(json.dumps({identifier: {'doc_id':identifier, 'source_path':str(new_path),
        'page_count':1, 'status':'succeeded'}}), encoding='utf8')
    scope = RegisteredDocumentScopeReader(store, allow_pdf_scope=True).read([identifier])
    assert scope.pdf_documents and 'Visible policy header' in scope.results[0].content
    assert all('FAKE999' not in r.content for r in scope.results)


def test_explicit_page_queries_and_quote_locations_cannot_use_the_hidden_layer(hidden_scan):
    from types import SimpleNamespace
    from campusai.web_documents import WebDocuments
    web = WebDocuments.__new__(WebDocuments)
    def unexpected_model(*args, **kwargs):
        raise AssertionError('An unread image page must not send hidden text to the model')
    web.application = SimpleNamespace(query_service=SimpleNamespace(
        reset_request_state=lambda: None, ask_source_pages=unexpected_model))
    web.source_bytes = lambda *_: hidden_scan.read_bytes()
    record = {'doc_id':'source', 'name':'source.pdf', 'page_count':1}
    web.record = lambda *_: record
    answer = web.answer_physical_pages('Summarize page 1', [record], {'language':'en'}, {})
    assert answer['answer']['abstained'] and answer['document_info']['kind'] == 'page_text_unavailable'
    location = web.locate_quote('source', {'quote':'FAKE999 HIDDEN OCR', 'page_range':[1,1]}, {})
    assert not location['matched']


@pytest.mark.parametrize('rotation,crop', [(0, False), (90, False), (180, False), (270, False), (0, True), (90, True)])
def test_visible_table_characters_survive_hidden_overlays_and_view_transforms(tmp_path, rotation, crop):
    import pdfplumber
    from campusai.ingestion.table_extractor import _visible_native_page, extract_tables
    path = tmp_path/'table.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page()
        xs, ys = (40, 170, 250, 470), (80, 110, 140, 170)
        for x in xs: page.draw_line((x, ys[0]), (x, ys[-1]))
        for y in ys: page.draw_line((xs[0], y), (xs[-1], y))
        for y, row in zip((100, 130, 160), [('Course code','Credits','Course name'), ('XYZ456','6','Visible course'), ('MAT789','4','Second course')]):
            for x, value in zip((50, 180, 260), row): page.insert_text((x, y), value, fontsize=10)
        page.insert_text((180, 130), '999', fontsize=10, render_mode=3)
        page.insert_text((50, 200), 'FAKE999 HIDDEN OCR', fontsize=10, render_mode=3)
        if crop: page.set_cropbox(fitz.Rect(20, 20, 540, 800))
        page.set_rotation(rotation); pdf.save(path)
    parsed = parse_pdf(path)[0]
    with pdfplumber.open(path) as pdf:
        visible = _visible_native_page(pdf.pages[0], parsed['visible_characters'])
        text = ''.join(c['text'] for c in visible.chars)
        assert 'XYZ456' in text and 'MAT789' in text and '999' not in text and 'FAKE' not in text
    if rotation == 0:
        tables = extract_tables([parsed], 'table', path)
        assert any(row[:2] == ['XYZ456','6'] for table in tables for row in table.rows)
