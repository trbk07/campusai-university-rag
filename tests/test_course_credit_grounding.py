"""Credit grounding must bind the asserted code to its own headed column."""
import json
import pytest

from campusai.rag.claims import Claim, align_claims
from campusai.rag.course_credits import course_credit_support
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult
from tests.test_grounding import LLM


def table(headers=None, rows=None):
    return json.dumps({'headers': headers or ['Mã học\nphần', 'Học phần', 'Số\ntín\nchỉ', 'Hours', 'Prerequisites'],
                       'rows': rows or [['CS201', 'Computing', '3', '30', 'CS101'],
                                        ['CS101', 'Intro', '4', '3', '']]}, ensure_ascii=False)


def test_native_table_credit_answer_passes_without_inventing_unit_from_bare_number():
    content = table()
    result = RetrievalResult('table-chunk', 'document', 2, content, 'table', .9, 'hybrid', {'table_id': 'table-2'})
    text = 'Course CS201 has 3 credits.'
    answer = GroundedAnswerGenerator(LLM({'answer': text, 'confidence': 'high', 'abstained': False,
        'claims': [{'claim_id': '1', 'text': text, 'citation_ids': ['table-chunk']}],
        'citations': [{'chunk_id': 'table-chunk', 'page': 2, 'quote': 'CS201'}]})).answer('How many credits?', [result])
    assert not answer.abstained
    assert answer.claims[0].status == 'supported'


@pytest.mark.parametrize('text', ['Course CS201 has 4 credits.', 'Course CS201 has 30 credits.',
                                 'Course CS101 has 3 credits.'])
def test_other_rows_hours_and_prerequisite_numbers_cannot_establish_credits(text):
    result = RetrievalResult('table-chunk', 'document', 2, table(), 'table', .9, 'hybrid', {})
    aligned = align_claims([Claim('1', text, citation_ids=('table-chunk',))], EvidenceRegistry([result]), {'1': ('table-chunk',)})
    assert aligned[0].status != 'supported'


@pytest.mark.parametrize('content', [
    'CS201\nComputing\n3\n30\n15',
    table(['Course code', 'Hours'], [['CS201', '3']]),
    table(['Course code', 'Credits', 'Credits'], [['CS201', '3', '4']]),
    table(rows=[['CS201', 'Computing', '3', '30', ''], ['CS201', 'Computing', '4', '30', '']]),
    table(rows=[['CS202', 'Computing', '3', '30', 'CS201']]),
    '{"headers": broken',
])
def test_missing_or_ambiguous_column_proof_is_not_guessed(content):
    assert course_credit_support('Course CS201 has 3 credits.', content) is None


@pytest.mark.parametrize('text', ['Course CS201 has at least 3 credits.', 'Course CS201 has 3 percent.',
                                 'Course CS201 has 3 credits in 2025.', 'Course CS201 has 3 credits and is compulsory.'])
def test_simple_credit_proof_never_approves_extra_qualifiers_or_units(text):
    assert course_credit_support(text, table()) is None


def test_credit_claim_publishes_only_its_headed_column_proof():
    headed = RetrievalResult('headed', 'document', 2, table(), 'table', .9, 'hybrid', {})
    bare = RetrievalResult('bare', 'document', 2, 'CS201\nComputing\n3\n30\n15', 'text', .8, 'hybrid', {})
    text = 'Course CS201 has 3 credits.'
    aligned = align_claims([Claim('1', text, citation_ids=('headed', 'bare'))],
                          EvidenceRegistry([headed, bare]), {'1': ('headed', 'bare')})
    assert aligned[0].status == 'supported'
    assert aligned[0].citation_ids == ('headed',)


def test_conflicting_headed_credit_values_are_not_pruned_to_manufacture_support():
    first = RetrievalResult('a', 'document', 2, table(), 'table', .9, 'hybrid', {})
    second = RetrievalResult('b', 'document', 3, table(rows=[['CS201', 'Computing', '4', '30', '']]), 'table', .8, 'hybrid', {})
    aligned = align_claims([Claim('1', 'Course CS201 has 3 credits.', citation_ids=('a','b'))],
                          EvidenceRegistry([first,second]), {'1': ('a','b')})
    assert aligned[0].status == 'contradicted' and aligned[0].numeric_conflict


@pytest.mark.parametrize('code', ['CS201', 'CS 201', 'CS\n201', 'CS\u00a0201'])
@pytest.mark.parametrize('value, supported', [('3', True), ('4', False), ('30', False)])
def test_code_prefix_spacing_preserves_exact_credit_column_proof(code, value, supported):
    result = RetrievalResult('table-chunk', 'document', 2, table(), 'table', .9, 'hybrid', {})
    text = f'Course {code} has {value} credits.'
    aligned = align_claims([Claim('1', text, citation_ids=('table-chunk',))],
                          EvidenceRegistry([result]), {})
    assert (aligned[0].status == 'supported') is supported


@pytest.mark.parametrize('code', ['C S201', 'CS20 1', 'CS-201', 'CS 2010', 'CS 201A'])
def test_spacing_correction_does_not_merge_different_or_malformed_codes(code):
    assert course_credit_support(f'Course {code} has 3 credits.', table()) is not True


def test_code_spacing_policy_does_not_reuse_pre_fix_abstention_cache():
    from campusai.rag.cache import GROUNDING_POLICY_VERSION, build_rag_cache_key
    args = dict(question='How many credits?', language='en', doc_ids=['document'],
                filters=None, top_k=5, mode='hybrid', corpus_version='index',
                model='model', context_budget={})
    # Old false abstentions cannot hide the correction in a warm answer cache.
    assert GROUNDING_POLICY_VERSION == 'grounding-v5'
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, grounding_policy_version='grounding-v1')
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, grounding_policy_version='grounding-v2')
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, grounding_policy_version='grounding-v3')
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, grounding_policy_version='grounding-v4')


@pytest.mark.parametrize('course', ['UET.RBE1072', 'UET.RBE 1072'])
def test_institution_prefixed_credit_identity_is_proved_from_its_own_row(course):
    content = table(['Course code', 'Credits', 'Hours'],
                    [['UET.RBE1072', '3', '30'], ['RBE1072', '2', '3']])
    assert course_credit_support(f'Course {course} has 3 credits.', content) is True
    assert course_credit_support(f'Course {course} has 2 credits.', content) is False
    assert course_credit_support('Course RBE1072 has 2 credits.', content) is True
    assert course_credit_support('Course RBE1072 has 3 credits.', content) is False
    assert course_credit_support('Course OTHER.RBE1072 has 3 credits.', content) is None


def test_prefixed_credit_difference_keeps_two_source_operand_order():
    from campusai.rag.credit_sum import credit_difference_claim_support
    first = RetrievalResult('new', 'new-document', 1,
        table(['Course code', 'Credits'], [['UET.RBE1072', '3']]), 'table', .9, 'hybrid', {})
    second = RetrievalResult('old', 'old-document', 2,
        table(['Course code', 'Credits'], [['RBE2031', '2']]), 'table', .9, 'hybrid', {})
    text = 'Credit difference for RBE2031 minus UET.RBE1072 is 2 - 3 = -1 credits.'
    assert credit_difference_claim_support(text, [second, first])[0]
    assert not credit_difference_claim_support(text, [first, second])[0]
    assert not credit_difference_claim_support(text.replace('= -1', '= 1'), [second, first])[0]


def named_table():
    return table(['№', 'Discipline', 'Credits', 'Hours'],
                 [['1', 'Algebra', '4', '30'], ['2', 'Algebra 1', '3', '4'],
                  ['3', 'Solid mechanics', '3', '30']])


@pytest.mark.parametrize('text', ['Course Algebra has 4 credits.', 'Môn Algebra có 4 tín chỉ.',
                                 'Course Solid mechanics has 3 credits.'])
def test_named_course_credits_use_exact_name_and_credit_column(text):
    assert course_credit_support(text, named_table()) is True
    result = RetrievalResult('named', 'document', 1, named_table(), 'table', .9, 'hybrid', {})
    answer = GroundedAnswerGenerator(LLM({'answer': text, 'confidence': 'high', 'abstained': False,
        'claims': [{'claim_id': '1', 'text': text, 'citation_ids': ['named']}],
        'citations': [{'chunk_id': 'named', 'page': 1, 'quote': 'Algebra'}]})).answer('Credits?', [result])
    assert not answer.abstained
    assert answer.claims[0].status == 'supported'


@pytest.mark.parametrize('text', ['Course Algebra has 3 credits.', 'Course Algebra has 30 credits.',
                                 'Course Algebra 1 has 4 credits.', 'Course Solid mechanics has 4 credits.'])
def test_named_course_rejects_other_rows_hours_and_prefix_matches(text):
    assert course_credit_support(text, named_table()) is False
    item = RetrievalResult('named', 'document', 1, named_table(), 'table', .9, 'hybrid', {})
    aligned = align_claims([Claim('1', text, citation_ids=('named',))], EvidenceRegistry([item]), {})
    assert aligned[0].status == 'contradicted'


@pytest.mark.parametrize('content', [
    'Algebra 4 30',
    table(['Discipline', 'Hours'], [['Algebra', '4']]),
    table(['Discipline', 'Credits', 'Credits'], [['Algebra', '4', '3']]),
    table(['Discipline', 'Credits'], [['Algebra', '4'], ['Algebra', '3']]),
    table(['Discipline', 'Credits'], [['Algèbra', '4']]),
    table(['Discipline', 'Credits'], [['Algebra 1', '4']]),
])
def test_named_course_missing_ambiguous_or_different_identity_is_not_guessed(content):
    assert course_credit_support('Course Algebra has 4 credits.', content) is None


@pytest.mark.parametrize('text', ['Course Algebra has at least 4 credits.',
                                 'Course Algebra has 4 credits in 2025.',
                                 'Course Algebra has 4 credits and is compulsory.'])
def test_named_proof_does_not_approve_extra_claims(text):
    assert course_credit_support(text, named_table()) is None


@pytest.mark.parametrize('source, supported', [
    ('Tập thể Xuất sắc có từ 10% sinh viên trở lên đạt danh hiệu Sinh viên Giỏi.', True),
    ('Tập thể Xuất sắc có từ 20% sinh viên trở lên đạt danh hiệu Sinh viên Giỏi.', False),
    ('Tập thể Xuất sắc có đúng 10% sinh viên đạt danh hiệu Sinh viên Giỏi.', False),
    ('Tập thể Xuất sắc có từ 10% sinh viên trở xuống đạt danh hiệu Sinh viên Giỏi.', False),
])
def test_percentage_minimum_idiom_preserves_exact_value_and_direction(source, supported):
    item = RetrievalResult('rule', 'document', 1, source, 'text', .9, 'hybrid', {})
    text = 'Tỷ lệ tối thiểu sinh viên đạt danh hiệu Sinh viên Giỏi trong tập thể Xuất sắc là từ 10% trở lên.'
    aligned = align_claims([Claim('1', text, citation_ids=('rule',))], EvidenceRegistry([item]), {})
    assert (aligned[0].status == 'supported') is supported
