"""Reject stale context, source and reviewer attribution in negative dev review."""
from copy import deepcopy

import pytest

from evaluation.benchmarks.phase7_negative_review import validate_review


@pytest.fixture
def packet():
    review = {'reviewed_at': '2026-10-07T00:00:00+00:00', 'status': 'source_context_reviewed_dev_only',
        'analyst': 'Codex AI assistant', 'owner_manual_row_review_claim': False,
        'independent_human_review_claim': False, 'index_sha256': 'index', 'method': 'scoped review',
        'groups': [{'qids': list(range(1, 46)), 'category': 'missing_subject',
                    'reason': 'No subject in the question/context', 'expected_behavior': 'clarify_or_abstain'}]}
    rows = [{'qid': f'human-candidate-{i:04d}', 'split': 'dev', 'answerable': False,
             'release_eligible': False, 'gold_evidence': [], 'context': [], 'selected_text': '',
             'document_context': {}, 'filters': {}, 'doc_ids': ['doc']} for i in range(1, 46)]
    sources = {('doc', 'chunk'): {'page': 1, 'content': 'general curriculum'}}
    return review, rows, sources


@pytest.mark.parametrize('field,value', [('context', [{'role': 'user', 'content': 'some subject'}]),
    ('answerable', True), ('gold_evidence', [{'doc_id': 'doc', 'chunk_id': 'chunk'}]),
    ('split', 'test'), ('release_eligible', True), ('doc_ids', ['missing']),
    ('document_context', {'scope': 'seed_corpus_upload_fixture', 'uploaded_documents': ['transcript']})])
def test_changed_input_cannot_retain_negative_approval(packet, field, value):
    review, rows, sources = deepcopy(packet)
    rows[0][field] = value
    with pytest.raises(ValueError):
        validate_review(review, rows, sources, 'index')


@pytest.mark.parametrize('field,value', [('owner_manual_row_review_claim', True),
    ('independent_human_review_claim', True), ('index_sha256', 'stale'),
    ('reviewed_at', '2099-01-01T00:00:00+00:00'), ('analyst', 'invented human')])
def test_false_review_identity_rejected(packet, field, value):
    review, rows, sources = deepcopy(packet)
    review[field] = value
    with pytest.raises(ValueError):
        validate_review(review, rows, sources, 'index')


@pytest.mark.parametrize('numbers', [list(range(1, 45)), list(range(1, 46)) + [1], list(range(1, 46)) + [46]])
def test_missing_duplicate_or_out_of_scope_decisions_rejected(packet, numbers):
    review, rows, sources = deepcopy(packet)
    review['groups'][0]['qids'] = numbers
    with pytest.raises(ValueError):
        validate_review(review, rows, sources, 'index')
