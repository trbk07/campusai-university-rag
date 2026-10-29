"""Source geometry, lossless cells, ambiguous layouts and durable upgrade safety."""
from collections import Counter
import hashlib
import json
from types import SimpleNamespace

import pytest

from campusai.ingestion.leader_text_tables import leader_text_records
from campusai.ingestion.table_extractor import _page_packet
from tests.test_partial_numeric_tables import word


def grid():
    words = [word('Label', 65, 15, 95), word('Details', 220, 15, 260)]
    for y, label in [(60, 'Alpha'), (90, 'Beta'), (140, 'Gamma'), (170, 'Delta')]:
        words += [word(label, 20, y, 75), word('........', 80, y, 145),
                  word(label + '-source-value', 160, y, 225)]
    return SimpleNamespace(
        horizontal_edges=[{'x0': 10, 'x1': 330, 'top': y} for y in (10, 40, 190)],
        vertical_edges=[{'x0': 150, 'top': 10, 'bottom': 190}],
        extract_words=lambda: words, find_tables=lambda: [])


def test_borders_and_leaders_recover_cells_without_outer_vertical_rules():
    page = grid(); record, = leader_text_records(page)
    assert record['rows'] == [['Label', 'Details'],
        *[[label + ' ........', label + '-source-value'] for label in ['Alpha','Beta','Gamma','Delta']]]
    source = Counter(token for w in page.extract_words() for token in w['text'].split())
    assert Counter(' '.join(' '.join(row) for row in record['rows']).split()) == source
    assert record['edges'] == [10, 150, 330]
    assert len(record['proof']['row_bboxes']) == len(record['proof']['cell_bboxes']) == 4
    assert len(record['proof']['leader_bboxes']) == 4
    packet = _page_packet(page, 'actual-document', 7)
    assert packet['records'][0]['rows'] == record['rows']
    assert packet['page'] == 7


def test_hanging_primary_label_and_multiline_right_cell_keep_their_own_rows():
    page = grid(); words = page.extract_words()
    words[5:8] = [word('Long label reaches the edge',20,90,145),
                  word('second label line',28,100,110),
                  word('Source contact',160,90,225),word('123-456',168,100,200),
                  word('Source continuation paragraph',160,110,310),word('postcode 12345',168,120,250)]
    record, = leader_text_records(page)
    assert record['rows'][2] == ['Long label reaches the edge second label line',
        'Source contact 123-456 Source continuation paragraph postcode 12345']
    assert record['rows'][3][0].startswith('Gamma')
    assert record['rows'][4][0].startswith('Delta')


@pytest.mark.parametrize('with_leader', [False, True])
def test_indented_entry_with_a_new_value_cannot_be_merged_into_a_long_parent_label(with_leader):
    page = grid(); words = page.extract_words()
    words[5:8] = [word('Long parent label fills the source column',20,90,145),
                  word('Parent value',160,90,225),word('Child label',28,100,75),
                  *([word('........',80,100,145)] if with_leader else []),
                  word('Different child value',160,100,250)]
    assert leader_text_records(page) == []


@pytest.mark.parametrize('defect', [
    'bottom', 'header_rule', 'divider', 'short_divider', 'broken_divider', 'multiple_dividers',
    'crossed_column', 'missing_value', 'missing_header', 'uncentred_header', 'leaders',
    'unlabelled_right_paragraph', 'first_row_unlabelled', 'unvalued_footer', 'leader_ends',
])
def test_incomplete_or_ambiguous_layout_never_invents_a_cell_or_drops_a_row(defect):
    page = grid(); words = page.extract_words()
    if defect == 'bottom': page.horizontal_edges.pop()
    if defect == 'header_rule': page.horizontal_edges.pop(1)
    if defect == 'divider': page.vertical_edges = []
    if defect == 'short_divider': page.vertical_edges[0]['bottom'] = 180
    if defect == 'broken_divider': page.vertical_edges = [
        {'x0':150,'top':10,'bottom':80},{'x0':150,'top':90,'bottom':190}]
    if defect == 'multiple_dividers': page.vertical_edges.append({'x0':250,'top':10,'bottom':190})
    if defect == 'crossed_column': words[4]['x0'] = 145
    if defect == 'missing_value': words.pop(7)
    if defect == 'missing_header': words.pop(1)
    if defect == 'uncentred_header': words[1]['x0'], words[1]['x1'] = 155, 195
    if defect == 'leaders': words[:] = [w for w in words if w['text'] != '........']
    if defect == 'unlabelled_right_paragraph': words.append(word('A different unlabelled value',160,75,300))
    if defect == 'first_row_unlabelled': words.append(word('Unlabelled first value',160,50,300))
    if defect == 'unvalued_footer': words.append(word('Unvalued source label',20,180,130))
    if defect == 'leader_ends': words[3]['x1'] = 138
    assert leader_text_records(page) == []


def test_split_vertical_drawing_segments_are_not_mistaken_for_separate_rows():
    page = grid()
    page.vertical_edges = [{'x0':150,'top':a,'bottom':b} for a,b in
                           [(10,40),(40,80),(80,130),(130,175),(175,190)]]
    record, = leader_text_records(page)
    assert len(record['rows']) == 5


def test_existing_physical_tables_are_not_reinterpreted_by_the_new_fallback(monkeypatch):
    page = grid()
    page.find_tables = lambda: [SimpleNamespace(extract=lambda:[['Original','Header'],['Actual','Value']],
        cells=[(10,10,150,40),(150,10,330,40),(10,40,150,190),(150,40,330,190)])]
    def forbidden(*args): raise AssertionError('Do not reinterpret existing tables')
    monkeypatch.setattr('campusai.ingestion.leader_text_tables.leader_text_records',forbidden)
    record, = _page_packet(page,'actual-document',1)['records']
    assert record['rows'] == [['Original','Header'],['Actual','Value']]


def test_complex_layout_is_bounded_before_word_decoding():
    page = grid()
    page.horizontal_edges = [{'x0':10,'x1':330,'top':20*i} for i in range(32)]
    def forbidden(): raise AssertionError('Do not decode unbounded grid combinations')
    page.extract_words = forbidden
    assert leader_text_records(page) == []


@pytest.mark.parametrize('backend', ['rapidocr','tesseract','vietocr'])
@pytest.mark.parametrize('previous_version', ['table-v5-partial-numeric-grid','table-v6-leader-text-grid'])
def test_previous_jobs_remain_readable_but_new_upload_uses_new_identity(backend,previous_version):
    from campusai.ingestion.background.state import accepted_job_identities, job_identity, normalize_options
    options = normalize_options({'ocr_backend':backend})
    payload = {'source_sha256':'source','options':options,'text_coverage_version':4,
               'table_extractor_version':previous_version}
    if backend == 'vietocr':
        from campusai.ingestion.ocr_tables import OCR_TABLE_POLICY
        payload['ocr_table_policy'] = OCR_TABLE_POLICY
    fingerprint = lambda v: hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    previous = fingerprint(payload)
    assert previous in accepted_job_identities('source',options)
    assert previous != job_identity('source',options)
    assert fingerprint({**payload,'table_extractor_version':'unrecognized-producer'}) not in accepted_job_identities('source',options)
