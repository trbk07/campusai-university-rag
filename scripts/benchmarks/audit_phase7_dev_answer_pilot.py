"""Recompute diagnostic public-output/usage metrics, preserving provider failures.

Delegated AI source reviews are attributed accurately. This does not manufacture
the independent/owner human reviews required by the release answer validator.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from campusai.rag.grounding import validate_citation
from campusai.rag.schemas import validate_release_response
from campusai.retrieval.tokenizer_vi import source_body
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.paired_answer_quality import answer_digest
from scripts.benchmarks.phase7_dev_answer_pilot import results

BASE = Path('evaluation/results/phase7-completion-20261004')


def ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if denominator else None}


def recompute(raw, packet, review, evidence):
    if (review.get('analyst') != 'Codex AI assistant' or review.get('reviewer_role') != 'delegated_ai_analyst'
            or review.get('owner_manual_review_claim') is not False or review.get('independent_human_review_claim') is not False
            or review.get('release_eligible') is not False):
        raise ValueError('requires an accurately attributed, release-ineligible delegated review')
    assessed = {(x['qid'], x['arm']): x for x in review['reviews']}
    prepared = {(x['qid'], x['arm']): x for x in packet['pairs']}
    observed = {(x['qid'], x['arm']): x for x in raw['observations']}
    if (len(assessed) != len(review['reviews']) or len(prepared) != len(packet['pairs'])
            or len(observed) != len(raw['observations']) or set(assessed) != set(observed) or set(observed) != set(prepared)):
        raise ValueError('reviews and observations must uniquely cover the entire prepared packet')
    failed_qids = set()
    calls = []
    for key, obs in observed.items():
        decision, pair = assessed[key], prepared[key]
        if decision['answer_sha256'] != answer_digest(obs['answer']) or decision['observed_at'] != obs['observed_at']:
            raise ValueError('public review no longer binds the observed output')
        stamp = datetime.fromisoformat(review['recorded_at'])
        if stamp > datetime.now(timezone.utc) or stamp < datetime.fromisoformat(obs['observed_at']):
            raise ValueError('review must follow the actual output')
        if not validate_release_response(obs['answer'])[0]:
            raise ValueError('invalid public response')
        if len(obs['llm_calls']) != 1:
            raise ValueError('this fixed pilot requires one attempted call per prepared arm')
        call = obs['llm_calls'][0]
        context = pair['prompt'].partition('\n\nEVIDENCE:\n')[2]
        if (call['prompt_sha256'] != pair['prompt_sha256']
                or call['selected_context'] != context
                or call['selected_context_sha256'] != hashlib.sha256(context.encode()).hexdigest()):
            raise ValueError('actual prompt/context differs from the authorized packet')
        calls.append(call)
        if call['provider_status'] != 'completed':
            if decision['status'] != 'not_quality_reviewable_provider_failure':
                raise ValueError('provider failure cannot be certified as answer quality')
            failed_qids.add(key[0])
            continue
        if call['cached'] is not False or decision['status'] != 'reviewed_public_output_diagnostic':
            raise ValueError('completed output requires uncached attributable review')
        claims = {x['claim_id']: x for x in obs['answer']['claims']}
        reviewed = {x['claim_id']: x for x in decision['claims']}
        if (set(claims) != set(reviewed) or len(reviewed) != len(decision['claims'])
                or decision['all_public_factual_claims_enumerated'] is not True):
            raise ValueError('every emitted factual claim must be enumerated exactly')
        if obs['answer']['abstained'] and (decision['rubric_satisfied'] or decision['covered_gold_claim_ids']):
            raise ValueError('positive abstention cannot satisfy or cover positive gold claims')
        supplied = {x['chunk_id']: x for x in obs['answer']['citations']}
        selected = {x.chunk_id: x for x in results(pair['evidence'])}
        for claim_id, claim in reviewed.items():
            if claim['text'] != claims[claim_id]['text'] or type(claim['supported']) is not bool:
                raise ValueError('reviewed claim changed')
            if {x['chunk_id'] for x in claim['citations']} != set(claims[claim_id]['citation_ids']):
                raise ValueError('every emitted claim/citation pair needs an explicit verdict')
            for cite in claim['citations']:
                source = evidence[cite['doc_id'], cite['chunk_id']]
                if (cite['chunk_id'] not in supplied or cite['chunk_id'] not in selected
                        or source['page'] != cite['page']
                        or cite['source_body_sha256'] != hashlib.sha256(source_body(source).encode()).hexdigest()
                        or not validate_citation(supplied[cite['chunk_id']], selected[cite['chunk_id']], require_quote=True).valid
                        or type(cite['supports']) is not bool or not cite.get('reason')):
                    raise ValueError('citation review lacks exact selected-source binding')
    if len(calls) != raw['attempted_calls'] or len(calls) > packet['max_provider_calls']:
        raise ValueError('provider call ceiling or accounting mismatch')
    complete = [key for key in observed if key[0] not in failed_qids]
    metrics = {}
    for arm in sorted({key[1] for key in complete}):
        keys = [key for key in complete if key[1] == arm]
        claims = [claim for key in keys for claim in assessed[key]['claims']]
        pairs = [cite for claim in claims for cite in claim['citations']]
        required = [claim for claim in claims if claim['requires_citation']]
        metrics[arm] = {'positive_queries': len(keys), 'negative_queries': 0,
            'accuracy': ratio(sum(not observed[key]['answer']['abstained'] and assessed[key]['rubric_satisfied'] for key in keys), len(keys)),
            'false_abstention': ratio(sum(observed[key]['answer']['abstained'] for key in keys), len(keys)),
            'gold_claim_coverage': ratio(sum(len(assessed[key]['covered_gold_claim_ids']) for key in keys), sum(len(prepared[key]['gold_claims']) for key in keys)),
            'citation_precision': ratio(sum(c['supports'] for c in pairs), len(pairs)),
            'citation_recall': ratio(sum(any(c['supports'] for c in claim['citations']) for claim in required), len(required)),
            'groundedness': ratio(sum(c['supported'] for c in claims), len(claims)),
            'answer_fpr': ratio(0, 0), 'all_hop_support': ratio(0, 0)}
    usage = [call['usage'] for call in calls if call['usage_status'] == 'reported']
    tokens = {name: sum(item.get(name, 0) for item in usage)
              for name in ('promptTokenCount', 'candidatesTokenCount', 'thoughtsTokenCount', 'totalTokenCount')}
    return {'attempted_calls': len(calls), 'completed_calls': sum(c['provider_status'] == 'completed' for c in calls),
            'failed_calls': sum(c['provider_status'] != 'completed' for c in calls),
            'provider_error_types': [c.get('provider_error_type') for c in calls if c['provider_status'] != 'completed'],
            'complete_pairs': len(complete) // 2, 'symmetrically_excluded_qids': sorted(failed_qids),
            'metrics_complete_pairs': metrics, 'reported_usage_calls': len(usage), 'tokens_reported': tokens}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('retain prior diagnostic; use a new output')
    paths = {name: BASE / filename for name, filename in {
        'raw': 'p7-06-paired-pilot-actual-20261007.json', 'packet': 'p7-06-paired-pilot-egress-packet-20261007.json',
        'review': 'p7-06-paired-pilot-public-review-20261007.json', 'authorization': 'p7-06-paired-pilot-egress-authorization-20261007.json',
        'pricing': 'p7-06-gemini-pricing-reference-20261007.json'}.items()}
    raw, packet, review, authorization, pricing = (read_json(paths[name]) for name in ('raw', 'packet', 'review', 'authorization', 'pricing'))
    if (raw['packet_sha256'] != sha256(paths['packet']) or authorization['packet_sha256'] != sha256(paths['packet'])
            or review['raw_sha256'] != sha256(paths['raw']) or review['packet_sha256'] != sha256(paths['packet'])
            or review['egress_authorization_sha256'] != sha256(paths['authorization'])):
        raise ValueError('pilot raw/review/authorization bindings changed')
    index = Path('.tmp/phase7-curated-source-20261005-v2/index')
    if review['index_sha256'] != sha256(index / 'manifest.json'):
        raise ValueError('review source index changed')
    result = recompute(raw, packet, review, frozen_evidence(index))
    tokens = result['tokens_reported']
    estimate = (tokens['promptTokenCount'] * pricing['paid_standard_text_input']
                + (tokens['candidatesTokenCount'] + tokens['thoughtsTokenCount']) * pricing['paid_standard_output_including_thinking']) / pricing['per_tokens']
    result.update({'status': 'PILOT_FAIL_PROVIDER_AVAILABILITY_AND_ANSWER_ACCURACY', 'release_eligible': False,
        'test_used': False, 'holdout_used': False, 'reviewer_role': 'delegated_ai_analyst',
        'source_bindings': {name: {'path': path.as_posix(), 'sha256': sha256(path)} for name, path in paths.items()},
        'runner_sha256': sha256(Path(__file__)),
        'cost': {'actual_charge_usd': None, 'actual_charge_status': 'unknown',
                 'paid_standard_list_price_equivalent_known_usage_usd': estimate,
                 'failed_call_usage_known': False, 'billing_tier_known': False},
        'limitations': ['Three completed positive-only pairs; no negative or multi-hop quality denominator.',
                       'Empty claims/citations have null metrics, never a perfect score.',
                       'One failed provider pair is excluded from both semantic arms but retained in availability/cost.',
                       'Historical scorer and contexts; not current serving or official S4/S5 acceptance.',
                       'Provider final text/finish reason were not captured in this run and cannot be reconstructed.',
                       'The permitted eight calls are exhausted; no retries or additional packet transmission.']})
    write_json(args.output, result)
    print(result['status'], result['complete_pairs'], 'complete pairs;', result['completed_calls'], 'completed calls')


if __name__ == '__main__':
    main()
