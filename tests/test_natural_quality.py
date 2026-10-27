"""Model agreement cannot override missing fields or changed evidence/output."""
from copy import deepcopy

import pytest

from evaluation.grounding.natural_quality import assess_quality


def example():
    row = {'id': 'one', 'request': {'question': 'credits?', 'history': []}, 'retrieved_evidence': [],
           'public_response': {'answer': 'Môn XYZ456 có 7 tín chỉ.', 'abstained': False,
                               'citations': [], 'claims': []}}
    gold = {'row_reviews': {'one': {'answerable': True}},
            'claims': {'one': [{'claim_id': 'fact', 'field': 'credits', 'course_code': 'XYZ456', 'value': 7}]}}
    review = {'id': 'one', 'verdict': 'correct', 'covered_gold_claim_ids': ['fact'],
              'missing_required_gold_claim_ids': [], 'unsupported_spans': [], 'unknown_support_spans': [],
              'rationale': 'Exact credit field checked.'}
    return row, gold, review


def test_review_agreement_does_not_certify_wrong_required_field():
    row, gold, review = example(); row['public_response']['answer'] = 'Môn XYZ456 có 9 tín chỉ.'
    report = assess_quality([row], [deepcopy(row)], [review], gold)
    assert report['conservative_accuracy_lower_bound'] == 0
    assert not report['gates']['accuracy_at_least_90_percent']


def test_changed_unreviewed_public_prose_counts_as_unknown_support():
    before, gold, review = example(); current = deepcopy(before)
    current['public_response']['answer'] += ' Một thông tin mới chưa được kiểm chứng.'
    report = assess_quality([current], [before], [review], gold)
    assert report['conservative_hallucination_upper_bound'] == 1
    assert report['unknown_support_answer_ids'] == ['one']


def test_an_unexplained_incorrect_verdict_cannot_be_assumed_hallucination_free():
    row, gold, review = example(); review['verdict'] = 'incorrect'
    report = assess_quality([row], [deepcopy(row)], [review], gold)
    assert report['unknown_support_answer_ids'] == ['one']


def test_only_the_complete_literal_validated_definition_can_replace_review():
    from dataclasses import asdict
    from campusai.rag.grounding import Citation
    from campusai.retrieval.hybrid import RetrievalResult
    before, gold, review = example()
    quote = 'Danh hiệu “Sinh viên Nghiên cứu” được trao cho sinh viên có đóng góp tích cực.'
    source = RetrievalResult('c1', 'doc', 1, quote, 'text', 1., 'bm25', {})
    cite = Citation('c1', 'doc', 1, quote, page_range=(1, 1)).to_dict()
    before['retrieved_evidence'] = [asdict(source)]
    before['public_response']['citations'] = [cite]
    current = deepcopy(before)
    current['public_response']['answer'] = quote
    current['public_response']['claims'] = [{'text': quote, 'citation_ids': ['c1']}]
    report = assess_quality([current], [before], [review], gold)
    assert report['literal_source_delta_ids'] == ['one']
    assert not report['unknown_support_answer_ids']
    # A literal supported passage is not an answer to an unrelated credit
    # question; source support alone cannot manufacture required-field credit.
    assert report['certified_correct_lower_count'] == 0
    current['public_response']['answer'] += ' Thông tin mới không có trong nguồn.'
    assert assess_quality([current], [before], [review], gold)['unknown_support_answer_ids'] == ['one']


@pytest.mark.parametrize('change', ['request', 'evidence', 'gold_id', 'contradictory_review', 'missing', 'duplicate'])
def test_missing_changed_or_inconsistent_evidence_fails_closed(change):
    before, gold, review = example(); current = deepcopy(before); reviews = [review]
    if change == 'request': current['request']['question'] = 'Different question'
    elif change == 'evidence': current['retrieved_evidence'] = [{'doc_id': 'd', 'chunk_id': 'c', 'page': 1, 'content': 'new', 'content_type': 'text'}]
    elif change == 'gold_id': review['covered_gold_claim_ids'] = ['invented']
    elif change == 'contradictory_review': review['unsupported_spans'] = ['7 tín chỉ']
    elif change == 'missing': reviews = []
    elif change == 'duplicate': reviews.append(deepcopy(review))
    with pytest.raises(ValueError): assess_quality([current], [before], reviews, gold)
