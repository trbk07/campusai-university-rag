import json

import pytest

from evaluation.benchmarks.source_course_rows import source_course_rows


def evidence(headers, cells):
    return {('catalog','table'):{'page':4,'content_type':'table',
        'content':'[Page: 4]\n'+json.dumps({'headers':headers,'rows':[cells]},ensure_ascii=False)}}


def test_explicit_sparse_columns_keep_credit_role_and_source_proof():
    headers = ['Số TT','Mã số','','','Học phần\n(ghi bằng tiếng Việt và tiếng Anh)',
               '', 'Số\ntín\nchỉ','Số giờ tín chỉ','Mã học\nphần tiên quyết']
    rows = evidence(headers, ['1','ABC1001','','','Orbital dynamics','','3','45','XYZ2002'])
    fact = source_course_rows(rows)[0]
    assert fact['credits'] == 3 and fact['columns']['credits'] == 6
    assert fact['prerequisite_codes'] == ['XYZ2002']
    assert fact['page'] == 4 and fact['table_row'] == 0
    changed = evidence(headers, ['1','ABC1001','','','Orbital dynamics','','4','45','XYZ2002'])
    assert source_course_rows(changed)[0]['cells_sha256'] != fact['cells_sha256']
    assert source_course_rows(changed)[0]['source_content_sha256'] != fact['source_content_sha256']


@pytest.mark.parametrize('headers,cells', [
    (['Course code','Course name','Hours'], ['ABC1001','Orbital dynamics','3']),
    (['Course code','Course name','Credits','Credits'], ['ABC1001','Orbital dynamics','3','4']),
    (['Course code','Course name','Credits'], ['ABC1001','Orbital dynamics','3/6']),
    (['Course code','Course name','Credits'], ['Group I','Compulsory subjects','30']),
    (['Course code','Course name','Credits'], ['ABC1001','Orbital dynamics',3]),
    (['Course code','Course name','Credits'], ['ABC1001']),
    ([None,'Course name','Credits'], ['ABC1001','Orbital dynamics','3']),
])
def test_missing_ambiguous_or_non_row_proof_is_rejected(headers,cells):
    assert source_course_rows(evidence(headers,cells)) == []


@pytest.mark.parametrize('cell,expected', [
    ('',None), ('Requires approval',None), ('ABC1001, XYZ2002',['ABC1001','XYZ2002']),
    ('No prerequisite',None), ('ABC1001 + approval',None),
])
def test_empty_or_conditional_prerequisite_cells_do_not_prove_no_prerequisite(cell,expected):
    rows = evidence(['Course code','Course name','Credits','Prerequisites'],
                    ['NEW3001','Orbital dynamics','3',cell])
    assert source_course_rows(rows)[0]['prerequisite_codes'] == expected


def test_bilingual_name_header_and_pdf_course_code_spacing():
    rows = evidence(['Mã\nhọc phần','Tên học phần\n(tiếng Việt và tiếng Anh)','Số\ntín\nchỉ'],
                    ['XYZ 6001','Điều khiển quỹ đạo\nOrbital Control','3'])
    fact = source_course_rows(rows)[0]
    assert fact['code'] == 'XYZ6001' and fact['credits'] == 3
    assert fact['name_lines'] == ['Điều khiển quỹ đạo','Orbital Control']


def test_official_prefixed_codes_and_pdf_nonbreaking_header_spaces():
    rows = evidence(
        ['STT', 'Mã\u00a0học\u00a0phần', 'Học phần', 'Số tín chỉ', 'Mã học phần tiên quyết'],
        ['38', 'UET.RBE3340', 'Các cơ cấu truyền động Actuators and Power-Train', '3', 'UET.MTE2111'],
    )
    fact = source_course_rows(rows)[0]
    assert fact['code'] == 'UET.RBE3340'
    assert fact['credits'] == 3
    assert fact['prerequisite_codes'] == ['UET.MTE2111']
