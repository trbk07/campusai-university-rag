"""A code in prerequisites or copied metadata is not a primary row identity."""
import json

from campusai.retrieval.table_links import primary_course_tables
from campusai.retrieval.table_links import course_table_fields_requested
import pytest


def source(headers, rows):
    return {'content': json.dumps({'headers': headers, 'rows': rows}, ensure_ascii=False)}


def test_primary_course_table_uses_explicit_column_not_prerequisites_or_header():
    records = {
        'primary': source(['Mã học\nphần', 'Học phần', 'Mã số học phần tiên quyết'], [['CS201', 'Computing', 'CS101']]),
        'prerequisite': source(['Course code', 'Course name', 'Prerequisites'], [['CS301', 'Advanced', 'CS201']]),
        'metadata': {'content': '[Section: CS201]\nUnrelated text'},
        'bare': {'content': 'CS201\n21.'},
    }
    assert primary_course_tables('CS201', records) == {'primary'}


def test_ambiguous_or_unknown_column_and_malformed_rows_are_not_guessed():
    records = {
        'duplicate': source(['Course code', 'Course code'], [['CS201', 'CS301']]),
        'unknown': source(['Prerequisites', 'Course name'], [['CS201', 'Computing']]),
        'malformed': source(['Course code'], [None, [], [None]]),
        'bad_json': {'content': '{"headers": broken'},
    }
    assert primary_course_tables('CS201', records) == set()


def test_split_code_cell_and_case_preserve_exact_identity():
    records = {'primary': source(['Course code'], [['CS\n201']]),
               'adjacent': source(['Course code'], [['CS2011']])}
    assert primary_course_tables('cs201', records) == {'primary'}


@pytest.mark.parametrize('query',[
    'Môn CS201 có bao nhiêu tín chỉ?', 'CS201 học kỳ nào?',
    'What is the course name and credits for CS201?',
    'CS201 requires which prerequisites?', 'CS201 là môn gì?',
])
def test_explicit_course_fields_prefer_headed_rows(query):
    assert course_table_fields_requested(query)


@pytest.mark.parametrize('query',[
    'Cho biết thông tin về EMA3071E Ứng dụng máy tính lường điều khiển; mục 6.',
    'Describe the subject CS201 and its applications.',
    'Cho biết bảng hoặc số liệu về EMA2028; dòng tham chiếu 62.',
])
def test_generic_information_does_not_promote_all_repeated_code_tables(query):
    assert not course_table_fields_requested(query)
