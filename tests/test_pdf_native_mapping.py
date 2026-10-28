"""A visible but broken font map must not become trusted native evidence."""
import hashlib
import json

import pymupdf as fitz
import pytest

from campusai.ingestion import docling_parser as parser
from campusai.ingestion.pipeline import ingest_document


@pytest.fixture
def broken_font(tmp_path, monkeypatch):
    path = tmp_path/'font-map.pdf'
    with fitz.open() as pdf:
        page = pdf.new_page()
        for index, text in enumerate((
            "University's program credits are verified from the source PDF.",
            "Student's course registration requires department approval.",
            "Council's course plan includes module XYZ456 worth 6 credits.",
        )):
            page.insert_text((40, 100+index*35), text, fontsize=12)
        pdf.save(path)
    original = parser._page_lines

    def corrupted(page):
        lines, layout, ignored, sizes = original(page)
        def corrupt(text):
            return ''.join('\uf003' if c == "'" else chr(ord(c)+0xfee0)
                           if '!' <= c <= '~' else c for c in text if c != ' ')
        return ([{**row, 'text': corrupt(row['text'])} for row in lines],
                [{**row, 'text': corrupt(row['text'])} for row in layout], ignored, sizes)
    monkeypatch.setattr(parser, '_page_lines', corrupted)
    return path


def test_bad_font_needs_pixels_and_cannot_supply_native_scope(broken_font):
    page = parser.parse_pdf(broken_font)[0]
    assert page['requires_ocr'] and page['untrusted_native_mapping']
    assert page['text'] == '' and page['visible_characters'] == []
    assert 'hybrid_layout' not in page  # Whole page, not only a decorative image.
    with fitz.open(broken_font) as pdf:
        assert parser.visible_page_text(pdf[0]) == ''


def test_typography_and_private_icons_alone_are_not_bad_font_maps():
    full = 'Ｆｕｌｌ ｗｉｄｔｈ ｔｙｐｏｇｒａｐｈｙ ｉｓ ｌｅｇｉｔｉｍａｔｅ. ' * 10
    assert not parser._untrusted_latin_mapping([{'text': full}])
    assert not parser._untrusted_latin_mapping([{'text': 'Course\uf003credits are source text. ' * 30}])
    assert not parser._untrusted_latin_mapping([{'text': '中文日本語\uf003字体 ' * 100}])


def test_bad_mapping_is_review_required_with_source_unchanged(broken_font, tmp_path):
    before = hashlib.sha256(broken_font.read_bytes()).hexdigest()
    document = ingest_document(broken_font, store_dir=tmp_path/'store')
    assert document.status == 'review_required' and not document.chunks
    assert document.metadata['untrusted_native_pages'] == [1]
    assert hashlib.sha256(broken_font.read_bytes()).hexdigest() == before


def test_old_partial_ocr_cache_cannot_hide_broken_native_mapping(broken_font, tmp_path, monkeypatch):
    store = tmp_path/'store'
    detector = parser._untrusted_latin_mapping
    monkeypatch.setattr(parser, '_untrusted_latin_mapping', lambda _lines: False)
    old = ingest_document(broken_font, store_dir=store)
    assert old.status == 'succeeded'
    metadata = store/old.doc_id/'meta.json'
    record = json.loads(metadata.read_text(encoding='utf-8'))
    record['metadata'].update(text_coverage_version=3, ocr={'page_numbers': [1]})
    metadata.write_text(json.dumps(record), encoding='utf-8')
    monkeypatch.setattr(parser, '_untrusted_latin_mapping', detector)
    repaired = ingest_document(broken_font, store_dir=store)
    assert not repaired.cached and repaired.status == 'review_required'
    assert not repaired.chunks and repaired.metadata['unread_pages'] == [1]


def test_opt_in_ocr_reads_pixels_not_the_fault_injected_font_map(broken_font, tmp_path):
    from campusai.ingestion.ocr_assets import validate_tesseract_assets
    try:
        validate_tesseract_assets('.cache/ocr/tessdata_fast')
    except ValueError:
        pytest.skip('Optional pinned OCR assets unavailable')
    store = tmp_path/'store'
    document = ingest_document(broken_font, store_dir=store, enable_ocr=True,
                              ocr_backend='tesseract', ocr_data_dir='.cache/ocr/tessdata_fast')
    assert document.status == 'succeeded'
    text = (store/document.doc_id/'parsed.md').read_text(encoding='utf-8')
    assert '6 credits' in text and 'department approval' in text
    assert not any(0xff01 <= ord(c) <= 0xff5e for c in text)
    assert document.metadata['untrusted_native_pages'] == [1]
    assert not document.tables  # No native cells from a rejected font map.


@pytest.mark.parametrize('backend', ['tesseract', 'rapidocr', 'vietocr'])
def test_version_three_jobs_remain_readable_but_new_identity_changes(backend):
    from campusai.ingestion.background.state import (
        accepted_job_identities, job_identity, normalize_options,
    )
    options = normalize_options({'ocr_backend': backend})
    payload = {'source_sha256': 'a'*64, 'options': options, 'text_coverage_version': 3}
    if backend == 'vietocr':
        from campusai.ingestion.ocr_tables import OCR_TABLE_POLICY
        payload['ocr_table_policy'] = OCR_TABLE_POLICY
    historical = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert historical in accepted_job_identities('a'*64, options)
    assert historical != job_identity('a'*64, options)


def test_old_registered_partial_ocr_is_not_ready(broken_font, tmp_path):
    from campusai.api import CampusAIApplication
    from campusai.documents.registry import DocumentRegistry
    from campusai.schemas import Document
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app
    from tests.test_web_documents import call
    identifier = hashlib.sha256(broken_font.read_bytes()).hexdigest()
    store = tmp_path/'managed'
    source = store/'uploads'/identifier/'source.pdf'
    source.parent.mkdir(parents=True)
    source.write_bytes(broken_font.read_bytes())
    index = tmp_path/'index'/identifier
    index.mkdir(parents=True)
    for name in ('bm25.json', 'dense.json'):
        (index/name).write_text('{}')
    DocumentRegistry(store/'registry.json').add(Document(identifier, str(source), 1,
        status='succeeded', metadata={'text_coverage_version': 3, 'ocr': {'page_numbers': [1]}}))
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(tmp_path/'index'), GroundedAnswerGenerator(None)),
        ingestion_defaults={'store_dir': store, 'index_dir': tmp_path/'index'})
    try:
        document = call(make_wsgi_app(app), '/api/documents')['body']['documents'][0]
        assert not document['ready'] and document['unread_pages'] == [1]
    finally:
        app.close()


def test_native_table_extractor_receives_empty_character_proof(broken_font, monkeypatch):
    from campusai.ingestion import table_extractor
    observed = []
    def inspect(_path, _doc, *, visibility=None):
        observed.append(visibility)
        return []
    monkeypatch.setattr(table_extractor, '_extract_pdfplumber', inspect)
    pages = parser.parse_pdf(broken_font)
    assert table_extractor.extract_tables(pages, 'source-id', pdf_path=broken_font) == []
    assert observed == [{1: []}]


def test_flat_ocr_cannot_reintroduce_unproved_native_table_structure(monkeypatch):
    from campusai.ingestion import table_extractor
    monkeypatch.setattr(table_extractor, '_extract_pdfplumber', lambda *a, **k: [])
    page = {'page': 1, 'text': 'Course | Credits\nABC123 | 9\nDEF456 | 6',
            'untrusted_native_mapping': True, 'visible_characters': []}
    assert table_extractor.extract_tables([page], 'source-id', pdf_path='unused.pdf') == []
