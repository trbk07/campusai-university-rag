"""A requested credit difference needs both source columns and signed arithmetic."""
from dataclasses import replace
import pytest
from campusai.rag.claims import Claim, align_claims
from campusai.rag.credit_sum import credit_difference_claim_support
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.grounding import GroundedAnswerGenerator
from tests.test_grounding_policies import credit_table
from tests.test_grounding import LLM


def sources():
    return [credit_table('B', '2'), credit_table('A', '3')]


def test_signed_same_code_comparison_has_all_hops():
    values = sources()
    text = 'Credit difference for CS101 minus CS101 is 2 - 3 = -1 credits.'
    claims = align_claims([Claim('difference', text, citation_ids=('B-c', 'A-c'))], EvidenceRegistry(values), {})
    assert claims[0].status == 'supported' and claims[0].required_citations == 2
    assert claims[0].citation_ids == ('B-c', 'A-c')


@pytest.mark.parametrize('failure', ['missing', 'reversed', 'wrong_result', 'hours', 'other_row', 'duplicate', 'same_document'])
def test_incomplete_or_invented_calculation_is_not_supported(failure):
    values = sources()
    text = 'Credit difference for CS101 minus CS101 is 2 - 3 = -1 credits.'
    if failure == 'missing': values.pop()
    elif failure == 'reversed': values.reverse()
    elif failure == 'wrong_result': text = text.replace('= -1', '= 1')
    elif failure == 'hours': text = text.replace('2 - 3 = -1', '30 - 3 = 27')
    elif failure == 'other_row': text = text.replace('2 - 3 = -1', '4 - 3 = 1')
    elif failure == 'duplicate': values[1] = values[0]
    else: values[1] = replace(values[1], doc_id=values[0].doc_id)
    assert credit_difference_claim_support(text, values)[0] is False


def test_equal_values_still_require_two_sources():
    values = [credit_table('B', '3'), credit_table('A', '3')]
    text = 'Chênh lệch tín chỉ của CS101 trừ CS101 là 3 - 3 = 0 tín chỉ.'
    assert credit_difference_claim_support(text, values)[0]
    assert not credit_difference_claim_support(text, values[:1])[0]


@pytest.mark.parametrize('text', ['The credit difference is 1 credit.',
    'Credit difference for CS101 minus CS101 is 2 - 3 = 1 credits, approximately.'])
def test_unproved_credit_difference_does_not_fall_back_to_number_overlap(text):
    values = sources()
    aligned = align_claims([Claim('difference', text, citation_ids=('B-c', 'A-c'))], EvidenceRegistry(values), {})
    assert aligned[0].status == 'contradicted'


@pytest.mark.parametrize('wrong', [False, True])
def test_generator_keeps_correct_comparison_and_redacts_wrong_math(wrong):
    values = sources()
    text = f'Credit difference for CS101 minus CS101 is 2 - 3 = {1 if wrong else -1} credits.'
    payload = {'answer': text, 'confidence': 'high', 'abstained': False,
        'claims': [{'claim_id': 'difference', 'text': text, 'citation_ids': ['B-c', 'A-c']}],
        'citations': [{'chunk_id': r.chunk_id, 'page': 1, 'quote': 'CS101'} for r in values]}
    answer = GroundedAnswerGenerator(LLM(payload)).answer('Compare CS101 credits in A versus B.', values, 'en')
    assert answer.abstained is wrong
    if wrong:
        assert not answer.to_public_dict()['claims'] and not answer.to_public_dict()['citations']


def test_arithmetic_instructions_only_apply_to_requested_credit_comparisons():
    generator = GroundedAnswerGenerator()
    assert 'operand order' in generator.prompt('Compare CS101 credits in A versus B.', sources(), 'en')
    assert 'operand order' not in generator.prompt('How many credits does CS101 have?', sources(), 'en')


@pytest.mark.parametrize('code', ['CS 101', 'CS\n101', 'CS\u00a0101'])
@pytest.mark.parametrize('wrong', [False, True])
def test_spaced_codes_keep_operand_order_and_signed_result_checks(code, wrong):
    text = f'Credit difference for {code} minus CS101 is 2 - 3 = {1 if wrong else -1} credits.'
    assert credit_difference_claim_support(text, sources())[0] is (not wrong)
    assert not credit_difference_claim_support(text, list(reversed(sources())))[0]
    assert not credit_difference_claim_support(text, sources()[:1])[0]
