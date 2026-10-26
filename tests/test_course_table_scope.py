"""Inherited PDF columns must retain every raw row and its actual scope."""
from collections import Counter
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pdfplumber
import pytest

from campusai.ingestion.table_extractor import _extract_pdfplumber


SOURCE = Path('data/corpus/university/uet_mai_joint_curriculum_2022.pdf')
HEADERS = ['No.', 'Discipline', 'Credits', 'Resources']


def test_physical_source_rows_markers_and_subtotals_are_never_dropped_or_relabelled():
    with pdfplumber.open(SOURCE) as pdf:
        raw = [[['' if c is None else str(c).strip() for c in row] for row in table.extract()]
               for page in pdf.pages for table in page.find_tables()]
    expected = Counter(tuple(row) for i, rows in enumerate(raw)
                       for row in (rows[1:] if i == 0 else rows) if any(row))
    tables = _extract_pdfplumber(SOURCE, 'physical')
    actual = Counter(tuple(row) for table in tables for row in table.rows)
    assert actual == expected
    assert all(table.headers == tables[0].headers for table in tables)
    assert all(table.schema.get('section') not in {'Semester 29', 'Semester 31', 'Semester 32'} for table in tables)
    for table in tables:
        markers = {cell.replace(' ', '') for row in table.rows for cell in row
                   if cell.casefold().startswith('semester')}
        if len(markers) > 1:
            assert not table.schema.get('section')
        if table.schema.get('parser') == 'pdfplumber-inherited-course-columns-v2':
            assert table.schema['header_source']['page'] == 1
            assert table.schema['header_source']['table_id'] == 'physical_p1_t1'
            assert len(table.schema['column_edges']) == 5


class Grid:
    def __init__(self, rows, widths=(40, 220, 55, 70), offset=0):
        self.raw = rows
        edges = [offset]
        for width in widths:
            edges.append(edges[-1] + width)
        self.cells = [(edges[c], r * 20, edges[c + 1], (r + 1) * 20)
                      for r in range(len(rows)) for c in range(len(widths))]

    def extract(self):
        return self.raw


def fake_pdf(monkeypatch, grids):
    pages = [SimpleNamespace(find_tables=lambda tables=tables: tables, extract_words=lambda: [])
             for tables in grids]
    monkeypatch.setattr(pdfplumber, 'open', lambda _path: nullcontext(SimpleNamespace(pages=pages)))


def test_translated_grid_can_inherit_headers_without_mixing_multiple_semesters(monkeypatch):
    first = Grid([HEADERS, ['Semester 1', '', '', ''], ['1', 'Alpha', '3', 'Institute X']])
    next_grid = Grid([['Semester 2', '', '', ''], ['1', 'Beta', '4', 'Institute Y'],
                      ['', 'Credits per semester', '4', ''], ['Semester3', '', '', ''],
                      ['1', 'Gamma', '5', 'Institute Z']], offset=6)
    fake_pdf(monkeypatch, [[first], [next_grid]])
    tables = _extract_pdfplumber('fake.pdf', 'doc')
    assert tables[1].headers == HEADERS and tables[1].rows == next_grid.raw
    assert 'section' not in tables[1].schema
    assert tables[1].schema['header_source']['page'] == 1


@pytest.mark.parametrize('widths', [(40, 100, 175, 70), (40, 220, 55, 100)])
def test_changed_column_geometry_cannot_borrow_units_from_another_table(monkeypatch, widths):
    first = Grid([HEADERS, ['Semester 1', '', '', ''], ['1', 'Alpha', '3', 'Institute X']])
    other = Grid([['Semester 2', '', '', ''], ['1', 'Beta', '45', 'Other']], widths=widths)
    fake_pdf(monkeypatch, [[first], [other]])
    tables = _extract_pdfplumber('fake.pdf', 'doc')
    assert tables[1].schema['parser'] == 'pdfplumber'
    assert tables[1].headers != HEADERS


def test_an_unrelated_explicit_header_resets_inherited_column_state(monkeypatch):
    first = Grid([HEADERS, ['Semester 1', '', '', ''], ['1', 'Alpha', '3', 'Institute X']])
    unrelated = Grid([['Index', 'Item', 'Hours', 'Location'], ['1', 'Other', '45', 'Lab']])
    later = Grid([['Semester 2', '', '', ''], ['1', 'Beta', '45', 'Lab']])
    fake_pdf(monkeypatch, [[first], [unrelated], [later]])
    tables = _extract_pdfplumber('fake.pdf', 'doc')
    assert tables[-1].schema['parser'] == 'pdfplumber'
    assert tables[-1].headers != HEADERS


def test_subtotal_cannot_become_a_scope_or_transfer_scope_to_following_rows(monkeypatch):
    first = Grid([HEADERS, ['Semester 1', '', '', ''], ['1', 'Alpha', '3', 'Institute X']])
    tail = Grid([['Semester 2', '', '', ''], ['1', 'Beta', '4', 'Institute Y'],
                 ['', 'Credits per semester', '4', '']])
    after = Grid([['2', 'Unknown scope', '5', 'Institute Z']])
    fake_pdf(monkeypatch, [[first], [tail, after]])
    tables = _extract_pdfplumber('fake.pdf', 'doc')
    assert tail.raw == tables[1].rows
    assert not tables[-1].schema.get('section')
    assert all(t.schema.get('section') != 'Semester 4' for t in tables)


@pytest.mark.parametrize('unknown', [
    ['Semester unknown', '', '', ''],
    ['Index', 'Item', 'Hours', 'Location'],
])
def test_unknown_scope_or_changed_inline_header_prevents_column_inheritance(monkeypatch, unknown):
    first = Grid([HEADERS, ['Semester 1', '', '', ''], ['1', 'Alpha', '3', 'Institute X']])
    other = Grid([['Semester 2', '', '', ''], unknown, ['1', 'Beta', '45', 'Lab']])
    fake_pdf(monkeypatch, [[first], [other]])
    tables = _extract_pdfplumber('fake.pdf', 'doc')
    assert tables[-1].schema['parser'] == 'pdfplumber'
    assert tables[-1].headers != HEADERS
    assert not tables[-1].schema.get('section')


def test_chunk_batches_keep_the_actual_nearest_marker_without_losing_course_rows():
    from campusai.ingestion.chunker import _table_row_batches
    rows = [['Semester 2', '', '', '']]
    rows += [[str(i), f'Long discipline name {i} ' * 3, '4', 'Institute Y'] for i in range(12)]
    rows += [['Semester 3', '', '', '']]
    rows += [[str(i), f'Other discipline name {i} ' * 3, '5', 'Institute Z'] for i in range(12)]
    batches = _table_row_batches(HEADERS, rows, 400)
    assert len(batches) > 4
    original = {id(row): index for index, row in enumerate(rows)}
    for batch in batches:
        for index, row in enumerate(batch):
            if row[1]:
                preceding = rows[:original[id(row)] + 1]
                expected = next(r for r in reversed(preceding) if r[0].startswith('Semester'))
                assert expected in batch[:index]
    assert Counter(tuple(r) for b in batches for r in b if r[1]) == Counter(tuple(r) for r in rows if r[1])


def test_full_source_chunks_retain_inherited_header_and_original_row_provenance():
    import pymupdf
    from campusai.ingestion.chunker import make_chunks
    with pymupdf.open(SOURCE) as doc:
        pages = [{'page': i, 'text': p.get_text()} for i, p in enumerate(doc, 1)]
    tables = _extract_pdfplumber(SOURCE, 'physical')
    chunks = make_chunks(pages, 'physical', {}, tables)
    by_id = {t.table_id: t for t in tables}
    for chunk in chunks:
        if chunk.content_type != 'table':
            continue
        table = by_id[chunk.metadata['table_id']]
        assert chunk.metadata['table_header_source'] == table.schema['header_source']
        body = __import__('json').loads(chunk.content[chunk.content.index('{"headers"'):])
        assert body['rows'] == [table.rows[i] for i in chunk.metadata['table_row_indices']]
        assert len(chunk.content) <= 2400


def test_a_chunk_cannot_carry_a_marker_past_its_closing_subtotal():
    from campusai.ingestion.chunker import _table_row_batches
    marker = ['Semester 2', '', '', '']
    unknown = ['2', 'Course after closed scope', '5', 'Institute Z']
    rows = [marker, ['1', 'Beta', '4', 'Institute Y'],
            ['', 'Credits per semester', '4', ''], unknown]
    batches = _table_row_batches(HEADERS, rows, 2000)
    last = next(batch for batch in batches if unknown in batch)
    assert marker not in last
