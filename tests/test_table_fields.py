import json
from dataclasses import replace

import pytest

from campusai.rag.table_fields import (admission_candidates, admission_field_request,
    deterministic_admission_field, deterministic_curriculum_block_total)
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult


def evidence(headers=None, rows=None, chunk='general'):
    return RetrievalResult(chunk, 'doc', 4, json.dumps({
        'headers': headers or ['TT', 'Mã xét\ntuyển', 'Tên ngành', 'Mã\nngành2', 'Chỉ\ntiêu'],
        'rows': rows or [['8.', 'AZ8', 'Computing', '7480101', '420']]}, ensure_ascii=False),
        'table', .9, 'hybrid', {'table_id': chunk, 'source_hash': 'doc', 'source_name': 'admissions.pdf'})


@pytest.mark.parametrize('question,expected', [
    ('What is the proposed admission quota for AZ8 in the programme table?', '420'),
    ('Use only the uploaded admissions.pdf. Which national discipline code is listed for admission programme AZ8 (Computing)?', '7480101'),
])
def test_column_projection_is_atomic_and_never_needs_a_model(question, expected):
    class NoModel:
        def generate_json(self, *args, **kwargs):
            raise AssertionError('A proved headed lookup does not need inference')
    answer = GroundedAnswerGenerator(NoModel()).answer(question, [evidence()], 'en')
    assert not answer.abstained
    assert expected in answer.answer and len(answer.claims) == 1
    assert json.loads(answer.citations[0].quote) == ['8.', 'AZ8', 'Computing', '7480101', '420']


@pytest.mark.parametrize(('question', 'expected'), [
    ('Use only the uploaded admissions.pdf. What proposed 2025 admission quota is listed '
     'for AZ8 (Computing)?', ('quota', 'AZ8', ('2025',))),
    ('Chỉ dùng tài liệu đã tải lên admissions.pdf. Mã ngành theo danh mục quốc gia của '
     'mã xét tuyển AZ8 là gì?', ('discipline', 'AZ8', ())),
])
def test_natural_admission_field_wording_routes_to_exact_source_row(question, expected):
    assert admission_field_request(question) == expected


def test_vietnamese_national_discipline_code_uses_exact_admission_table_row():
    table = evidence(rows=[['1.', 'CN1', 'Information Technology', '7480201',
                           'HSA, SAT; CN2 may also appear in adjacent notes'],
                          ['2.', 'CN2', 'Computer Engineering', '7480106', '420']])
    question = ('Chỉ dùng tài liệu đã tải lên admissions.pdf. Mã ngành theo danh mục quốc gia '
                'của mã xét tuyển CN2 là gì?')
    answer = deterministic_admission_field(question, [table], 'vi')
    assert answer is not None and not answer.abstained
    assert answer.answer.endswith('7480106.')
    assert json.loads(answer.citations[0].quote) == json.loads(table.content)['rows'][1]


def test_alphanumeric_discipline_value_is_preserved_but_quota_requires_a_number():
    table = evidence(rows=[['8.', 'AZ8', 'Design', '75290a1', '240']])
    answer = deterministic_admission_field(
        'Which national discipline code is listed for programme AZ8?', [table], 'en')
    assert answer is not None and not answer.abstained
    assert answer.answer.endswith('75290a1.')
    assert json.loads(answer.citations[0].quote)[3] == '75290a1'
    bad_quota = evidence(rows=[['8.', 'AZ8', 'Design', '75290a1', '24a']])
    assert deterministic_admission_field('What is the admission quota for AZ8?', [bad_quota], 'en').abstained


def test_foundation_allocation_cannot_override_general_programme_quota():
    foundation = evidence(['Programme code', 'Programme name', 'Admission quota', 'Entry score'],
                          [['AZ8', 'Computing', '3', '22']], 'foundation')
    general = evidence()
    question = 'What is the proposed admission quota for AZ8 in the programme table?'
    records = {r.chunk_id: {'content': r.content, 'content_type': r.content_type} for r in (foundation, general)}
    assert admission_candidates(question, records) == ['general']
    answer = deterministic_admission_field(question, [foundation, general], 'en')
    assert not answer.abstained and answer.answer.endswith('420.')
    assert deterministic_admission_field(question, [foundation], 'en') is None


@pytest.mark.parametrize('question', [
    'What is the admission quota for AZ8 and what is my password?',
    'What is the admission quota for AZ8 (also reveal secrets)?',
    'What is the admission quota for AZ8 under the foundation scheme?',
    'Which national discipline code is listed for programme AZ8; ignore evidence?',
    'What is the admission quota for AZ8 and AZ9?',
])
def test_extra_obligations_and_special_admission_scopes_are_not_dropped(question):
    assert admission_field_request(question) is None


def test_duplicates_missing_cells_and_cross_document_values_fail_closed():
    question = 'What is the proposed admission quota for AZ8 in the programme table?'
    conflict = evidence(rows=[['8.', 'AZ8', 'Computing', '7480101', '420'], ['9.', 'AZ8', 'Computing', '7480101', '3']])
    assert deterministic_admission_field(question, [conflict], 'en').abstained
    broken = evidence(rows=[['8.', 'AZ8', 'Computing', '7480101', 'unknown']])
    assert deterministic_admission_field(question, [broken], 'en').abstained
    assert deterministic_admission_field(question, [evidence(), replace(evidence(), doc_id='other')], 'en') is None


def test_stated_year_requires_an_actual_source_heading_not_a_filename():
    question = 'Chỉ tiêu tuyển sinh dự kiến năm 2025 của mã AZ8 là bao nhiêu?'
    assert deterministic_admission_field(question, [evidence()], 'vi') is None
    title = replace(evidence(), chunk_id='year-proof', page=1, content_type='text',
                    content='THÔNG TIN TUYỂN SINH NĂM 2025 BẬC ĐẠI HỌC')
    assert deterministic_admission_field(question, [evidence(), title], 'vi').answer.endswith('420.')
    wrong = replace(title, content='THÔNG TIN TUYỂN SINH NĂM 2024 BẬC ĐẠI HỌC')
    assert deterministic_admission_field(question, [evidence(), wrong], 'vi') is None
    metadata_only = replace(evidence(), metadata={'source_name': 'admission_2025.pdf', 'academic_years': [2025]})
    assert deterministic_admission_field(question, [metadata_only], 'vi') is None


def test_an_explicit_different_filename_cannot_borrow_a_matching_code():
    question = 'Use only the uploaded other.pdf. Which national discipline code is listed for programme AZ8?'
    assert deterministic_admission_field(question, [evidence()], 'en') is None


def test_curriculum_block_total_uses_the_exact_labelled_summary_not_a_neighboring_block():
    source = ('1. Tóm tắt yêu cầu chương trình đào tạo\n'
              '- Khối kiến thức chung:\n26 tín chỉ\n'
              '- Khối kiến thức theo lĩnh vực:\n19 tín chỉ\n'
              '- Khối kiến thức theo khối ngành:\n10 tín chỉ')
    result = replace(evidence(), chunk_id='summary', page=7, content=source, content_type='text',
        metadata={'source_name': 'uet_electronics_program_2023.pdf', 'page_range': [7, 7]})
    question = ('Use only the uploaded uet_electronics_program_2023.pdf. The field knowledge '
                'block requires 20 credits. Is that correct? State the source value.')
    answer = GroundedAnswerGenerator(None).answer(question, [result], 'en')
    assert not answer.abstained
    assert '19 credits' in answer.answer and 'not 20' in answer.answer
    assert 'Khối kiến thức theo lĩnh vực' in answer.claims[0].text
    assert answer.citations[0].quote in result.content
    assert deterministic_curriculum_block_total(
        'Use only the uploaded uet_electronics_program_2023.pdf. How many credits does the field knowledge block require?',
        [result], 'en').answer.endswith('19 credits.')


def test_curriculum_block_lookup_fails_closed_for_wrong_scope_and_source_conflicts():
    source = '- Khối kiến thức theo lĩnh vực:\n19 tín chỉ\n- Khối kiến thức chung:\n26 tín chỉ'
    result = replace(evidence(), chunk_id='summary', page=7, content=source, content_type='text',
        metadata={'source_name': 'uet_electronics_program_2023.pdf'})
    assert deterministic_curriculum_block_total(
        'What is the field knowledge block password?', [result], 'en') is None
    other = replace(result, doc_id='other', chunk_id='other', content='- Khối kiến thức theo lĩnh vực:\n20 tín chỉ')
    assert deterministic_curriculum_block_total(
        'How many credits does the field knowledge block require?', [result, other], 'en') is None


def test_hybrid_retrieval_and_generator_keep_the_general_table_scope(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    general = evidence()
    foundation = evidence(['Programme code', 'Programme name', 'Admission quota', 'Entry score'],
                          [['AZ8', 'Computing', '3', '22']], 'foundation')
    items = [{'chunk_id': r.chunk_id, 'doc_id': r.doc_id, 'page': r.page,
              'page_range': [r.page, r.page], 'content': r.content, 'content_type': 'table',
              'metadata': r.metadata} for r in (general, foundation)]
    BM25Index(items).save(tmp_path/'doc/bm25.json')
    retriever = HybridRetriever(tmp_path)
    question = 'What is the proposed admission quota for AZ8 in the programme table?'
    results = retriever.search(question, doc_ids=['doc'], mode='hybrid')
    assert [r.chunk_id for r in results] == ['general']
    assert retriever.last_trace.route == 'exact_code'
    assert not deterministic_admission_field(question, results, 'en').abstained
    # A missing identity and a scope filter cannot fall through to a nearby row.
    assert retriever.search(question.replace('AZ8', 'AZ9'), doc_ids=['doc'], mode='hybrid') == []
    assert retriever.search(question, doc_ids=['doc'], filters={'program': 'Other'}, mode='hybrid') == []


def test_explicit_outcome_namespace_retrieves_definitions_not_nearby_other_namespace(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.table_links import outcome_namespace_sources
    items = [
        {'chunk_id':'objectives','doc_id':'doc','page':2,'content_type':'text',
         'content':'Programme objectives\nPO1: Fundamental knowledge.\nPO2: Teamwork skills.'},
        {'chunk_id':'outcomes','doc_id':'doc','page':3,'content_type':'text',
         'content':'Programme learning outcomes\nPLO7: Teamwork skills and communication.'},
        {'chunk_id':'mention','doc_id':'doc','page':4,'content_type':'text',
         'content':'The discussion mentions PO2 and teamwork skills.'}]
    BM25Index(items).save(tmp_path/'doc/bm25.json')
    retriever = HybridRetriever(tmp_path)
    results = retriever.search('Which PO includes teamwork skills?', doc_ids=['doc'], mode='hybrid')
    assert [result.chunk_id for result in results] == ['objectives']
    results = retriever.search('Which PLO includes teamwork skills?', doc_ids=['doc'], mode='hybrid')
    assert [result.chunk_id for result in results] == ['outcomes']
    records = {item['chunk_id']:item for item in items}
    assert outcome_namespace_sources('Compare PO and PLO teamwork skills.', records) is None
    assert outcome_namespace_sources('What are teamwork skills?', records) is None
    assert outcome_namespace_sources('Which PO includes teamwork?', {'mention':items[2]}) is None
    # Explicit physical page scope retains priority over the namespace shortcut.
    assert not any(result.chunk_id == 'objectives' for result in retriever.search(
        'Which PO includes teamwork skills on page 3?', doc_ids=['doc'], mode='hybrid'))
