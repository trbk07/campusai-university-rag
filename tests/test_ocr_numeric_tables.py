"""Geometry/worker regression controls; mocked recognition is not OCR accuracy."""
import copy
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pytest

from campusai.ingestion.ocr_numeric_tables import (
    NUMERIC_TABLE_POLICY, assemble_numeric_tables, physical_tables, read_cell_jobs)
from campusai.ingestion.ocr_tables import validate_tables


def fixture():
    image = Image.new('L', (840, 390), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=17)
    xs, ys = [20, 100, 360, 580, 810], [20, 85, 145, 205, 265, 325]
    for x in xs: draw.line((x, ys[0], x, ys[-1]), fill=0, width=2)
    for y in ys: draw.line((xs[0], y, xs[-1], y), fill=0, width=2)
    values = [['No.', 'Region', 'Stock (USD)', 'Share (%)'],
              ['1', 'North', '101.25', '10.1'], ['2', 'South', '88.50', '8.8'],
              ['3', 'East', '42.60', '4.2'], ['4', 'West', '19.70', '1.9']]
    words = []
    for row, line in enumerate(values):
        for col, value in enumerate(line):
            x, y = xs[col]+12, ys[row]+18
            box = list(draw.textbbox((x, y), value, font=font))
            draw.text((x, y), value, fill=0, font=font)
            words.append({'text': value, 'bbox': box, 'confidence': .99})
    return np.asarray(image).copy(), words, values


def run(gray=None, words=None, *, values=None, score=.99):
    original, original_words, expected = fixture()
    gray = original if gray is None else gray
    words = original_words if words is None else words
    values = expected if values is None else values
    calls = []
    def recognize(jobs):
        calls.extend(jobs)
        assert all(set(j) == {'bbox', 'multiline', 'word_bboxes'} for j in jobs)
        return [(value, score) for row in values for value in row]
    return assemble_numeric_tables(gray, words, recognize), calls


def test_closed_grid_reads_actual_cells_without_using_previous_value_as_recognition_input():
    gray, words, expected = fixture()
    words[6]['text'] = '999'  # A recognizer mistake must be read again from pixels.
    result, calls = run(gray, words)
    assert len(result['tables']) == 1 and len(calls) == 20
    table = result['tables'][0]
    assert table['headers'] == expected[0] and table['rows'] == expected[1:]
    assert table['identity_column'] == 1
    assert table['parser'] == NUMERIC_TABLE_POLICY
    assert len(table['row_bboxes']) == 4 and len(table['header_bboxes']) == 4
    assert not any(w['text'] == '999' for w in result['words'])
    assert words[6]['text'] == '999'  # Caller observations remain unchanged.
    assert validate_tables([table], [0, 0, 840, 390])


@pytest.mark.parametrize('fault', ['open_edge', 'broken_column', 'broken_row', 'missing_header',
                                  'missing_value', 'cross_column', 'cross_row', 'two_identities'])
def test_ambiguous_grid_stays_unpublished_without_cell_recognition(fault):
    gray, words, _ = fixture()
    if fault == 'open_edge': gray[18:329, 808:815] = 255
    elif fault == 'broken_column': gray[165:181, 358:364] = 255
    elif fault == 'broken_row': gray[202:209, 375:420] = 255
    elif fault == 'missing_header': words = words[1:]
    elif fault == 'missing_value': del words[6]
    elif fault == 'cross_column': words[6]['bbox'] = [340, 107, 390, 125]
    elif fault == 'cross_row': words[6]['bbox'] = [375, 132, 420, 158]
    elif fault == 'two_identities': words[6]['text'] = 'unsupported text'
    result, calls = run(gray, words)
    assert result['tables'] == [] and not calls and result['words'] is words


@pytest.mark.parametrize('fault', ['uncertain', 'duplicate_identity', 'non_numeric', 'empty',
                                  'duplicate_header', 'data_header'])
def test_unproved_second_pass_never_invents_a_default_cell(fault):
    _, words, values = fixture()
    if fault == 'duplicate_identity': values[2][1] = values[1][1]
    elif fault == 'non_numeric': values[2][2] = 'unreadable'
    elif fault == 'empty': values[2][2] = ''
    elif fault == 'duplicate_header': values[0][2] = values[0][3]
    elif fault == 'data_header': values[0][2] = '101.25'
    result, calls = run(words=words, values=values, score=.89 if fault == 'uncertain' else .99)
    assert calls and result['tables'] == [] and result['words'] is words


def test_unrelated_page_words_and_excluded_existing_course_grid_are_preserved():
    gray, words, _ = fixture()
    outside = {'text': 'Real page footer', 'bbox': [20, 348, 180, 367], 'confidence': .98}
    result, _ = run(gray, words+[outside])
    assert outside in result['words'] and len(result['tables']) == 1
    blocked = assemble_numeric_tables(gray, words, lambda _:pytest.fail('Existing table must not be re-read'),
                                     excluded_bboxes=[result['tables'][0]['bbox']])
    assert blocked['tables'] == []


def test_multiline_header_projection_keeps_separate_real_lines_in_one_cell():
    image = Image.new('L', (300, 120), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    draw.text((30, 15), 'Stock', fill=0, font=font)
    draw.text((30, 53), '(USD)', fill=0, font=font)
    seen = []
    def recognize(boxes):
        seen.extend(boxes)
        return [('Stock', .99), ('(USD)', .98)]
    values = read_cell_jobs(np.asarray(image), [{'bbox': [10, 5, 200, 95], 'multiline': True,
                                               'word_bboxes': []}], recognize)
    assert values == [('Stock (USD)', .98)] and len(seen) == 2 and seen[0][3] < seen[1][1]


@pytest.mark.parametrize('fault', ['identity', 'confidence', 'count', 'recognition', 'parser', 'bounds'])
def test_worker_numeric_payload_requires_bounded_cell_proof(fault):
    result, _ = run(); table = copy.deepcopy(result['tables'][0])
    if fault == 'identity': table['identity_column'] = True
    elif fault == 'confidence': table['cell_recognition_confidences'][0] = float('nan')
    elif fault == 'count': table['cell_recognition_confidences'].pop()
    elif fault == 'recognition': table['recognition'] = 'invented'
    elif fault == 'parser': table['parser'] = 'untrusted'
    elif fault == 'bounds': table['bbox'][0] = -10
    with pytest.raises(ValueError): validate_tables([table], [0, 0, 840, 390])


def test_transformed_pdf_boxes_retain_pixel_grid_and_literal_units():
    result, _ = run(); table = result['tables'][0]
    transformed = physical_tables([table], lambda box:[value/2+10 for value in box], 2, [20, 20])[0]
    assert transformed['headers'] == table['headers'] and transformed['rows'] == table['rows']
    assert transformed['bbox'] == [v/2+10 for v in table['bbox']]
    assert transformed['column_edges'] == table['column_edges']
    assert transformed['render_origin'] == [20, 20]


@pytest.mark.parametrize('backend', ['rapidocr', 'vietocr'])
def test_new_numeric_policy_invalidates_optical_jobs_but_reads_exact_previous_v7_identity(backend):
    from campusai.ingestion.background.state import normalize_options, job_identity, accepted_job_identities
    from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION
    from campusai.ingestion.table_extractor import TABLE_EXTRACTOR_VERSION
    from campusai.ingestion.ocr_tables import OCR_TABLE_POLICY
    options = normalize_options({'enable_ocr': True, 'ocr_backend': backend})
    previous = {'source_sha256': 'a'*64, 'options': options,
                'text_coverage_version': TEXT_COVERAGE_VERSION, 'table_extractor_version': TABLE_EXTRACTOR_VERSION}
    if backend == 'vietocr': previous['ocr_table_policy'] = OCR_TABLE_POLICY
    old = hashlib.sha256(json.dumps(previous, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert old != job_identity('a'*64, options) and old in accepted_job_identities('a'*64, options)
    assert job_identity('a'*64, options) in accepted_job_identities('a'*64, options)


@pytest.mark.parametrize('backend', ['rapidocr', 'vietocr'])
def test_completed_ocr_cache_refreshes_once_for_new_numeric_policy(backend, tmp_path, monkeypatch):
    from campusai.ingestion.ocr import OCRDocument
    from campusai.ingestion.pipeline import ingest_document
    from tests.test_mixed_pdf import mixed_pdf
    # Build the same representative native/scan/native fixture through its
    # public fixture factory without consulting a model or benchmark label.
    source = mixed_pdf.__wrapped__(tmp_path)
    calls = []
    def recognize(*args, **kwargs):
        calls.append(kwargs['backend'])
        return OCRDocument([{'page': 2, 'text': 'Source text from pixels.'}], 'test-'+backend, .99, .01)
    monkeypatch.setattr('campusai.ingestion.pipeline.ocr_pdf', recognize)
    store = tmp_path/'store'
    first = ingest_document(source, store_dir=store, enable_ocr=True, ocr_backend=backend)
    metadata = store/first.doc_id/'meta.json'
    old = json.loads(metadata.read_text(encoding='utf-8'));old['metadata'].pop('ocr_numeric_policy')
    metadata.write_text(json.dumps(old), encoding='utf-8')
    refreshed = ingest_document(source, store_dir=store, enable_ocr=True, ocr_backend=backend)
    reused = ingest_document(source, store_dir=store, enable_ocr=True, ocr_backend=backend)
    assert calls == [backend, backend] and not refreshed.cached and reused.cached
    assert refreshed.metadata['ocr_numeric_policy'] == NUMERIC_TABLE_POLICY
    assert refreshed.doc_id == first.doc_id and refreshed.page_count == 3
