"""Evaluator regressions: lexical overlap cannot prove entity-role alignment."""
import pytest

from evaluation.grounding.grounding_metrics import _text_similarity, evaluate_grounding


def metrics(predicted, gold):
    return evaluate_grounding([{'id': 'fictional-unit', 'answerable': True, 'abstained': False,
        'claims': [{'claim_id': 'same-id', 'text': predicted, 'status': 'supported', 'citation_ids': ['c1']}],
        'citations': [{'chunk_id': 'c1', 'doc_id': 'unit-source', 'page': 1}],
        'gold_claims': [{'claim_id': 'same-id', 'text': gold,
                         'evidence': [{'chunk_id': 'c1', 'doc_id': 'unit-source', 'page': 1}]}]}])


@pytest.mark.parametrize('predicted,gold', [
    ('CS201 requires CS101 as prerequisite.', 'CS101 requires CS201 as prerequisite.'),
    ('CS201 is a prerequisite of CS101.', 'CS101 is a prerequisite of CS201.'),
    ('CS201 là môn tiên quyết của CS101.', 'CS101 là môn tiên quyết của CS201.'),
    ('Học phần A là tiên quyết của học phần B.', 'Học phần B là tiên quyết của học phần A.'),
    ('CS101 has 4 credits; CS201 has 3 credits.', 'CS101 has 3 credits; CS201 has 4 credits.'),
    ('CS101 has 4 credits.', 'CS101 has 3 credits; CS201 has 4 credits.'),
    ('Môn CS101 có 4 tín chỉ; môn CS201 có 3 tín chỉ.', 'Môn CS101 có 3 tín chỉ; môn CS201 có 4 tín chỉ.'),
    ('CS101 has 3 credits.', 'CS101 has at least 3 credits.'),
    ('Course Advanced Networking has code CS201.', 'Course Introductory Networking has code CS201.'),
    ('CS201 yêu cầu CS101 là học phần tiên quyết trực tiếp.', 'CS201 yêu cầu CS101 là học phần tiên quyết.'),
])
def test_same_word_bag_and_citation_cannot_approve_wrong_roles(predicted, gold):
    result = metrics(predicted, gold)
    assert _text_similarity(predicted, gold) == 0
    assert result['grounded_claim_precision'] == 0
    assert result['unsupported_claim_leakage'] == 1


@pytest.mark.parametrize('predicted,gold', [
    ('CS201 requires CS101 as prerequisite.', 'CS101 is a prerequisite of CS201.'),
    ('CS101 is a prerequisite of CS201.', 'CS101 is a direct prerequisite of CS201.'),
    ('CS 101 has 3 credits.', 'CS101 has 3 credits.'),
    ('CS101 has 3.0 credits.', 'CS101 has 3 credits.'),
    ('3 credits', '3 credits'),
    ('The course Advanced Networking has code CS201.', 'Advanced Networking has course code CS201.'),
])
def test_correct_role_and_supported_weaker_relation_keep_matching(predicted, gold):
    assert metrics(predicted, gold)['grounded_claim_precision'] == 1


def test_unspecified_prerequisite_does_not_prove_directness():
    assert _text_similarity('CS101 is a direct prerequisite of CS201.',
                            'CS101 is a prerequisite of CS201.') == 0


@pytest.mark.parametrize('predicted,gold', [
    ('The corrected code for ELT3213 is ELT3067.', 'The corrected code for ELT3067 is ELT3213.'),
    ('ELT3213 is corrected to ELT3067.', 'ELT3067 is corrected to ELT3213.'),
    ('ELT3213 được đính chính thành ELT3067.', 'ELT3067 được đính chính thành ELT3213.'),
    ('ELT3213 replaces ELT3067.', 'ELT3213 is corrected to ELT3067.'),
    ('ELT3212E is corrected to ELT3046E.', 'ELT3046E is corrected to ELT3212E.'),
    ('ELT3213 is corrected to ELT3067; AER2002 is corrected to EMA2008.',
     'ELT3213 is corrected to EMA2008; AER2002 is corrected to ELT3067.'),
])
def test_code_correction_direction_and_source_binding_are_not_a_word_bag(predicted, gold):
    assert metrics(predicted, gold)['grounded_claim_precision'] == 0


@pytest.mark.parametrize('predicted,gold', [
    ('ELT3067 replaces ELT3213.', 'ELT3213 is corrected to ELT3067.'),
    ('ELT3213 was changed to ELT3067.', 'The corrected code for ELT3213 is ELT3067.'),
    ('ELT3213 được đổi thành ELT3067.', 'ELT3213 được đính chính thành ELT3067.'),
    ('ELT 3212E is corrected to ELT 3046E.', 'ELT3212E is corrected to ELT3046E.'),
])
def test_correct_code_correction_paraphrases_and_spaced_suffix_codes_match(predicted, gold):
    assert metrics(predicted, gold)['grounded_claim_precision'] == 1
