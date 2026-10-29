"""Physical grids, incomplete sources and cache upgrades, without gold injection."""
from dataclasses import asdict
import hashlib
import json
from types import SimpleNamespace

import pytest

from campusai.ingestion.partial_numeric_tables import partial_numeric_records
from campusai.ingestion import table_extractor as extractor
from campusai.ingestion.pipeline import ingest_document
from tests.test_pdf_native_mapping import broken_font
from tests.test_pdf_visibility import hidden_scan


def word(text, x0, y, x1):
    return {'text': text, 'x0': x0, 'x1': x1, 'top': y, 'bottom': y + 7}


def grid():
    words = [word('Subject', 20, 15, 80), word('Total', 180, 15, 220),
             word('Reserve', 280, 15, 325), word('East', 165, 35, 195),
             word('West', 225, 35, 255)]
    for y, name, values in [(60, 'Alpha', ('10', '11', '12')),
                            (85, 'Beta', ('20', '21', '22')),
                            (110, 'Gamma', ('30', '31', '32'))]:
        words.append(word(name, 20, y, 90))
        words.extend(word(value, x, y, x + 20) for x, value in zip((180, 240, 300), values))
    return SimpleNamespace(
        horizontal_edges=[{'x0': 10, 'x1': 330, 'top': y} for y in (10, 50, 140)],
        vertical_edges=[{'x0': x, 'top': top, 'bottom': 50} for x, top in
                        [(150, 10), (210, 30), (270, 10)]],
        extract_words=lambda: words, find_tables=lambda: [])


def test_complete_grid_recovers_outer_columns_separate_rows_and_spanning_headers():
    record, = partial_numeric_records(grid())
    assert record['rows'] == [
        ['Subject', 'Total East', 'Total West', 'Reserve'],
        ['Alpha', '10', '11', '12'], ['Beta', '20', '21', '22'],
        ['Gamma', '30', '31', '32']]
    assert record['edges'] == [10, 150, 210, 270, 330]
    assert len(record['proof']['row_bboxes']) == len(record['proof']['cell_bboxes']) == 3
    span = next(s for s in record['proof']['header_spans'] if s['text'] == 'Total')
    assert span['columns'] == [1, 2]


def test_collapsed_inner_grid_is_replaced_without_changing_its_table_id():
    page = grid()
    old = [['East', 'West', 'Reserve'], ['10\n20\n30', '11\n21\n31', '12\n22\n32']]
    page.find_tables = lambda: [SimpleNamespace(extract=lambda: old,
        cells=[(150, 10, 210, 140), (210, 10, 270, 140), (270, 10, 330, 140)])]
    packet = extractor._page_packet(page, 'source', 1)
    record, = packet['records']
    assert record['number'] == 1 and len(record['rows']) == 4
    assert record['rows'][1] == ['Alpha', '10', '11', '12']


@pytest.mark.parametrize('defect', [
    'no_bottom', 'no_divider', 'missing_value', 'prose_value', 'crossing_column',
    'trailing_label', 'numeric_subject', 'missing_header',
])
def test_ambiguous_or_incomplete_grid_does_not_fill_or_publish_cells(defect):
    page = grid(); words = page.extract_words()
    if defect == 'no_bottom': page.horizontal_edges.pop()
    if defect == 'no_divider': page.vertical_edges = []
    if defect == 'missing_value': words.pop()
    if defect == 'prose_value': words[-1]['text'] = 'value not established'
    if defect == 'crossing_column': words[-1]['x0'] = 265
    if defect == 'trailing_label': words.append(word('Footnote', 20, 130, 80))
    if defect == 'numeric_subject': words[5]['text'] = '123'
    if defect == 'missing_header': words[:] = [w for w in words if w['text'] != 'Reserve']
    assert partial_numeric_records(page) == []


def test_wrapped_subject_requires_long_first_line_and_hanging_indent():
    page = grid(); words = page.extract_words()
    words[9:10] = [word('Long source label extends across subject', 20, 75, 145),
                   word('continuation', 28, 85, 110)]
    record, = partial_numeric_records(page)
    assert record['rows'][2][0] == 'Long source label extends across subject continuation'
    words[10]['x0'] = 20
    assert partial_numeric_records(page) == []


def test_subtotal_rule_does_not_truncate_later_source_rows():
    page = grid(); words = page.extract_words()
    page.horizontal_edges.insert(2, {'x0': 10, 'x1': 330, 'top': 100})
    record, = partial_numeric_records(page)
    assert record['rows'][-1] == ['Gamma', '30', '31', '32']
    assert record['bbox'][3] == 140


@pytest.mark.parametrize('missing', ['one_value', 'all_values'])
def test_subtotal_cannot_hide_an_incomplete_last_row(missing):
    page = grid(); words = page.extract_words()
    page.horizontal_edges.insert(2, {'x0': 10, 'x1': 330, 'top': 125})
    words.append(word('Delta', 20, 130, 90))
    if missing == 'one_value':
        words.extend([word('40', 180, 130, 200), word('41', 240, 130, 260)])
    assert partial_numeric_records(page) == []


def test_complex_rule_layout_does_not_start_unbounded_word_grid_search():
    page = grid()
    page.horizontal_edges = [{'x0': 10, 'x1': 330, 'top': 20*i} for i in range(32)]
    def forbidden(): raise AssertionError('Complex layouts stay with the existing parser')
    page.extract_words = forbidden
    assert partial_numeric_records(page) == []


@pytest.mark.parametrize('backend', ['rapidocr', 'tesseract', 'vietocr'])
@pytest.mark.parametrize('coverage', [3, 4])
def test_v4_fully_optical_cache_keeps_completed_ocr_and_exact_chunks(hidden_scan, tmp_path, monkeypatch, backend, coverage):
    def recognize(*args, **kwargs):
        return SimpleNamespace(pages=[{'page': 1, 'text': 'Verified optical source text.'}],
            engine='controlled OCR', average_confidence=.99, elapsed_seconds=.1,
            model_identity={'fixture': True})
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    store = tmp_path/'store'
    first = ingest_document(hidden_scan, store_dir=store, enable_ocr=True, ocr_backend=backend)
    path = store/first.doc_id/'meta.json'
    data = json.loads(path.read_text(encoding='utf8'))
    data['metadata']['table_extractor_version'] = 'table-v4-physical-course-scope'
    data['metadata']['text_coverage_version'] = coverage
    path.write_text(json.dumps(data), encoding='utf8')
    source_before = hashlib.sha256(hidden_scan.read_bytes()).hexdigest()
    def forbidden(*args, **kwargs): raise AssertionError('Completed optical content must not be recomputed')
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', forbidden)
    monkeypatch.setattr('campusai.ingestion.pipeline.extract_tables', forbidden)
    cached = ingest_document(hidden_scan, store_dir=store, enable_ocr=True, ocr_backend=backend)
    assert cached.cached and cached.metadata['table_extractor_version'] == extractor.TABLE_EXTRACTOR_VERSION
    assert cached.metadata['table_extractor_reused_from'] == 'table-v4-physical-course-scope'
    assert [asdict(c) for c in cached.chunks] == [asdict(c) for c in first.chunks]
    assert cached.metadata['ocr'] == first.metadata['ocr']
    assert cached.metadata['text_coverage_version'] == 4
    assert hashlib.sha256(hidden_scan.read_bytes()).hexdigest() == source_before


@pytest.mark.parametrize('defect', ['incomplete_ocr', 'newly_visible_native', 'backend_change', 'coverage_three_new_mapping'])
def test_old_optical_cache_is_not_reused_without_native_and_coverage_proof(broken_font, tmp_path, monkeypatch, defect):
    calls = []
    def recognize(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(pages=[{'page': 1, 'text': 'Optical source text.'}],
            engine='controlled OCR', average_confidence=.99, elapsed_seconds=.1,
            model_identity={'fixture': True})
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    store = tmp_path/'store'
    first = ingest_document(broken_font, store_dir=store, enable_ocr=True)
    path = store/first.doc_id/'meta.json'
    data = json.loads(path.read_text(encoding='utf8'))
    data['metadata']['table_extractor_version'] = 'table-v4-physical-course-scope'
    if defect == 'incomplete_ocr': data['metadata']['ocr']['page_numbers'] = []
    if defect == 'coverage_three_new_mapping': data['metadata']['text_coverage_version'] = 3
    path.write_text(json.dumps(data), encoding='utf8')
    if defect == 'newly_visible_native':
        monkeypatch.setattr('campusai.ingestion.pipeline.parse_pdf', lambda *a, **k:
            [{'page': 1, 'text': 'Native source now supplies cells.', 'requires_ocr': False, 'lines_meta': []}])
    refreshed = ingest_document(broken_font, store_dir=store, enable_ocr=True,
                               ocr_backend='tesseract' if defect == 'backend_change' else 'rapidocr')
    assert not refreshed.cached and 'table_extractor_reused_from' not in refreshed.metadata
    assert len(calls) == (1 if defect == 'newly_visible_native' else 2)


@pytest.mark.parametrize('backend', ['rapidocr', 'tesseract', 'vietocr'])
def test_old_job_ledger_remains_readable_but_new_upload_cannot_reuse_old_table_identity(backend):
    from campusai.ingestion.background.state import job_identity, accepted_job_identities, normalize_options
    from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION
    options = normalize_options({'ocr_backend': backend})
    old = {'source_sha256': 'source', 'options': options, 'text_coverage_version': TEXT_COVERAGE_VERSION}
    if backend == 'vietocr':
        from campusai.ingestion.ocr_tables import OCR_TABLE_POLICY
        old['ocr_table_policy'] = OCR_TABLE_POLICY
    old_identity = hashlib.sha256(json.dumps(old, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert old_identity in accepted_job_identities('source', options)
    assert old_identity != job_identity('source', options)
