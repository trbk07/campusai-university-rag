import json
import pytest

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.credit_sum import requested_sum_codes, credit_sum_claim_support
from campusai.retrieval.hybrid import RetrievalResult


def evidence(code='CS201', value='3', chunk='a', headers=None):
    content=json.dumps({'headers':headers or ['Course code','Credits','Hours'],
                        'rows':[[code,value,'30']]},ensure_ascii=False)
    return RetrievalResult(chunk,'scoped-document',2,content,'table',.9,'hybrid',{'table_id':chunk})


class NoGeneration:
    def generate_json(self,*_args,**_kwargs):
        raise AssertionError('course credit arithmetic must not call an LLM')


def test_two_hop_credit_sum_uses_both_source_rows_without_llm_or_invented_unit():
    answer=GroundedAnswerGenerator(NoGeneration()).answer('Tổng số tín chỉ của CS201 và CS202 là bao nhiêu?',
        [evidence(),evidence('CS202','4','b')])
    assert not answer.abstained and 'là 7.' in answer.answer
    assert answer.claims[-1].citation_ids==('a','b')
    assert {c.chunk_id for c in answer.citations}=={'a','b'}
    assert all(c.status=='supported' for c in answer.claims)


def test_english_sum_retains_language_and_source_proof():
    answer=GroundedAnswerGenerator(NoGeneration()).answer('What is the total credits for CS201 and CS202?',
        [evidence(),evidence('CS202','4','b')], 'en')
    assert not answer.abstained and 'Total credits for CS201 and CS202 are 7.' in answer.answer


@pytest.mark.parametrize('source', [[], [evidence()], [evidence(headers=['Course code','Hours','Other'])],
    [evidence(),evidence('CS202','not stated','b')],
    [evidence(),evidence('CS202','4','b'),evidence('CS202','5','c')]])
def test_missing_hop_missing_header_unknown_or_conflicting_value_abstains_without_generation(source):
    answer=GroundedAnswerGenerator(NoGeneration()).answer('Tổng số tín chỉ của CS201 và CS202 là bao nhiêu?',source)
    assert answer.abstained


def test_incorrect_addition_and_repeated_course_cannot_be_certified():
    source=[evidence(),evidence('CS202','4','b')]
    assert credit_sum_claim_support('Tổng số tín chỉ của CS201 và CS202 là 8.',source)[0] is False
    assert credit_sum_claim_support('Tổng số tín chỉ của CS201 và CS201 là 6.',source)[0] is False


@pytest.mark.parametrize('question',['Tổng số tín chỉ của CS201 và CS202 trước năm 2025 là bao nhiêu?',
    'Tổng số tín chỉ của CS201 và CS202 bắt buộc là bao nhiêu?',
    'CS201 và CS202 học trước môn gì?', 'Tổng số giờ của CS201 và CS202 là bao nhiêu?'])
def test_extra_scope_or_different_intent_is_never_silently_dropped(question):
    assert requested_sum_codes(question) is None


def test_duplicate_course_request_abstains_instead_of_double_counting():
    answer=GroundedAnswerGenerator(NoGeneration()).answer('Tổng số tín chỉ của CS201 và CS201 là bao nhiêu?',[evidence()])
    assert answer.abstained


def test_spaced_codes_sum_without_loosening_duplicate_or_value_checks():
    source = [evidence(), evidence('CS202', '4', 'b')]
    assert requested_sum_codes('What is the total credits for CS 201 and CS\u00a0202?') == ('CS201', 'CS202')
    assert credit_sum_claim_support('Total credits for CS 201 and CS202 are 7.', source)[0]
    assert not credit_sum_claim_support('Total credits for CS 201 and CS202 are 8.', source)[0]
    assert requested_sum_codes('Total credits for CS 201 and CS201?') == ()
    assert not credit_sum_claim_support('Total credits for CS 201 and CS201 are 6.', source)[0]
