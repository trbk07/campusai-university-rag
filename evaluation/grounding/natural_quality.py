"""Combine source-bound external review with conservative gold-field checks."""
from .natural_accuracy import score_required_fields
from .natural_context import normal
from campusai.rag.grounding import validate_citation
from campusai.retrieval.hybrid import RetrievalResult


def _indexed(rows):
    result = {r['id']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate case identity')
    return result


def _literal_definition(row):
    """Prove changed prose by its complete literal, already validated source."""
    public = row['public_response']
    if public['abstained'] or len(public['citations']) != 1 or len(public['claims']) != 1:
        return False
    cite = public['citations'][0]; value = normal(cite['quote'])
    if (normal(public['answer']) != value or normal(public['claims'][0]['text']) != value
            or 'danh hiệu ' not in value or 'được trao cho ' not in value
            or public['claims'][0]['citation_ids'] != [cite['chunk_id']]):
        return False
    evidence = next((r for r in row['retrieved_evidence'] if r['chunk_id'] == cite['chunk_id']), None)
    return bool(evidence and evidence['content_type'] == 'text' and
        validate_citation(cite, RetrievalResult(**evidence), require_quote=True).valid)


def assess_quality(rows, reviewed_rows, reviews, gold):
    current, original, external = _indexed(rows), _indexed(reviewed_rows), _indexed(reviews)
    if not current or current.keys() != original.keys() or current.keys() != external.keys():
        raise ValueError('Every current case requires its exact original reviewed case')
    fields = score_required_fields(rows, gold)
    field_map = {r['id']: r for r in fields['checks']}
    certified, unsupported, unknown, literal, reused = [], [], [], [], []
    for identifier, row in current.items():
        before = original[identifier]; review = external[identifier]
        if row['request'] != before['request']:
            raise ValueError('Reviewed user input changed')
        source = lambda r: {(e['doc_id'], e['chunk_id']): (e['page'], e['content'], e['content_type'])
                            for e in r['retrieved_evidence']}
        if source(row) != source(before):
            raise ValueError('Reviewed evidence scope changed')
        known = {c['claim_id'] for c in gold['claims'][identifier]}
        covered = review['covered_gold_claim_ids']; missing = review['missing_required_gold_claim_ids']
        if (set(covered) - known or set(missing) - known or set(covered) & set(missing)
                or len(covered) != len(set(covered)) or len(missing) != len(set(missing))):
            raise ValueError('Review names unknown, duplicated or contradictory gold IDs')
        if review['verdict'] not in {'correct', 'incorrect', 'review_required'} or not review['rationale'].strip():
            raise ValueError('An explicit review verdict and rationale are required')
        for span in review['unsupported_spans'] + review['unknown_support_spans']:
            if not span or span not in before['public_response']['answer']:
                raise ValueError('Review span is not literal public output')
        if review['verdict'] == 'correct' and (missing or review['unsupported_spans'] or review['unknown_support_spans']):
            raise ValueError('Correct verdict contradicts its own factual findings')
        unchanged = row['public_response'] == before['public_response']
        if unchanged:
            reused.append(identifier)
            if review['unsupported_spans']:
                unsupported.append(identifier)
            if (review['unknown_support_spans'] or review['verdict'] == 'review_required'
                    or review['verdict'] == 'incorrect' and not missing and not review['unsupported_spans']):
                unknown.append(identifier)
            safe = review['verdict'] == 'correct' and not review['unsupported_spans'] and not review['unknown_support_spans']
        elif _literal_definition(row):
            # This is a local source proof, never a rewritten provider review.
            literal.append(identifier); safe = True
        else:
            unknown.append(identifier); safe = False
        if safe and field_map[identifier]['established_correct']:
            certified.append(identifier)
    count = len(rows); positive = sum(c['positive'] for c in fields['checks'])
    correct_positive = sum(field_map[key]['positive'] for key in certified)
    accuracy_lower = len(certified)/count
    hallucination_upper = len(set(unsupported) | set(unknown))/count
    return {'cases': count, 'positive_cases': positive, 'negative_cases': count-positive,
        'certified_correct_lower_count': len(certified), 'conservative_accuracy_lower_bound': accuracy_lower,
        'positive_accuracy_lower_bound': correct_positive/positive if positive else None,
        'not_certified_ids': sorted(set(current)-set(certified)),
        'reviewed_unsupported_answer_ids': unsupported, 'unknown_support_answer_ids': unknown,
        'review_detected_hallucination_rate': len(unsupported)/count,
        'conservative_hallucination_upper_bound': hallucination_upper,
        'exact_public_review_reuse_count': len(reused), 'literal_source_delta_ids': literal,
        'required_fields': fields,
        'gates': {'accuracy_at_least_90_percent': accuracy_lower >= .9,
                  'hallucination_at_most_2_percent': hallucination_upper <= .02},
        'scope': 'Exposed internal natural100 qualification; source/gold field checks plus a separate external Gemini semantic audit. No human review, independent-base-model validation, fresh-holdout or population guarantee is claimed.'}
