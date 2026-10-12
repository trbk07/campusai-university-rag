"""Incomplete provider pairs and empty claims cannot manufacture quality PASS."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import pytest

from evaluation.reranker.paired_answer_quality import answer_digest
from scripts.benchmarks.audit_phase7_dev_answer_pilot import recompute


def fixture():
    answer = {'answer': 'Insufficient evidence.', 'citations': [], 'confidence': 'low',
              'abstained': True, 'abstention_reason': 'provider_abstention',
              'claims': [], 'schema_version': 'grounding-public-v2'}
    packet, raw, reviews = [], [], []
    stamp = datetime.now(timezone.utc).isoformat()
    for qid in ('dev-1', 'dev-2'):
        for arm in ('historical_baseline', 'historical_reranked_cap20'):
            packet.append({'qid': qid, 'arm': arm, 'prompt': 'q\n\nEVIDENCE:\nsource',
                           'prompt_sha256': 'prompt-hash', 'gold_claims': ['gold-1', 'gold-2'], 'evidence': []})
            raw.append({'qid': qid, 'arm': arm, 'answer': deepcopy(answer), 'observed_at': stamp,
                'llm_calls': [{'provider_status': 'completed', 'cached': False, 'prompt_sha256': 'prompt-hash',
                              'selected_context': 'source', 'selected_context_sha256': hashlib.sha256(b'source').hexdigest(),
                              'usage': {'promptTokenCount': 2, 'candidatesTokenCount': 1}, 'usage_status': 'reported'}]})
            reviews.append({'qid': qid, 'arm': arm, 'answer_sha256': answer_digest(answer), 'observed_at': stamp,
                            'status': 'reviewed_public_output_diagnostic', 'claims': [],
                            'all_public_factual_claims_enumerated': True, 'rubric_satisfied': False, 'covered_gold_claim_ids': []})
    review = {'analyst': 'Codex AI assistant', 'reviewer_role': 'delegated_ai_analyst',
              'owner_manual_review_claim': False, 'independent_human_review_claim': False,
              'release_eligible': False, 'recorded_at': datetime.now(timezone.utc).isoformat(), 'reviews': reviews}
    return {'observations': raw, 'attempted_calls': 4}, {'pairs': packet, 'max_provider_calls': 4}, review


def test_empty_claims_are_null_and_positive_abstentions_stay_in_accuracy_denominator():
    raw, packet, review = fixture()
    r = recompute(raw, packet, review, {})
    for metrics in r['metrics_complete_pairs'].values():
        assert metrics['accuracy'] == {'numerator': 0, 'denominator': 2, 'value': 0.0}
        assert metrics['false_abstention']['value'] == 1.0
        assert metrics['citation_precision']['value'] is None
        assert metrics['groundedness']['value'] is None
        assert metrics['answer_fpr']['value'] is None


def test_provider_failure_excludes_both_quality_arms_but_remains_in_failure_totals():
    raw, packet, review = fixture()
    raw['observations'][-1]['llm_calls'][0].update(provider_status='failed', cached=None, usage=None, usage_status='unknown', provider_error_type='LLMRateLimitError')
    review['reviews'][-1]['status'] = 'not_quality_reviewable_provider_failure'
    r = recompute(raw, packet, review, {})
    assert r['complete_pairs'] == 1 and r['failed_calls'] == 1 and r['completed_calls'] == 3
    assert r['symmetrically_excluded_qids'] == ['dev-2']
    assert all(m['accuracy']['denominator'] == 1 for m in r['metrics_complete_pairs'].values())


@pytest.mark.parametrize('mutation', ['wrong_answer', 'wrong_prompt', 'human_claim', 'false_gold_coverage', 'false_approval'])
def test_changed_evidence_or_review_claims_fail_closed(mutation):
    raw, packet, review = fixture()
    if mutation == 'wrong_answer': raw['observations'][0]['answer']['answer'] = 'Changed output.'
    if mutation == 'wrong_prompt': raw['observations'][0]['llm_calls'][0]['selected_context'] = 'Changed source'
    if mutation == 'human_claim': review['independent_human_review_claim'] = True
    if mutation == 'false_gold_coverage': review['reviews'][0]['covered_gold_claim_ids'] = ['gold-1']
    if mutation == 'false_approval': review['reviews'][0]['rubric_satisfied'] = True
    with pytest.raises(ValueError):
        recompute(raw, packet, review, {})
