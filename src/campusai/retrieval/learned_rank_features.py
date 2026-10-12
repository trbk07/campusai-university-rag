"""Query/candidate features for a dev-trained, interpretable rerank fusion.

No query IDs, source IDs, page coordinates, golds or difficulty labels enter
the feature vector. Candidate coordinates are used only to look up their
measured cross-encoder score and baseline position.
"""
from __future__ import annotations

import math
import re

from .tokenizer_vi import normalize_retrieval_query, normalized_tokens, source_body
from .routing import detected_course_codes
from .reranker_inputs import render_table

VERSION = 'query-candidate-fusion-v1'
FEATURE_NAMES = ('ce_logit', 'ce_probability', 'baseline_rr', 'pool_rr',
    'query_body_overlap', 'query_heading_overlap', 'query_bigram_overlap',
    'query_code_coverage', 'body_code_density', 'table', 'log_body_length',
    'numeric_fraction', 'credit_table', 'semester_table', 'prerequisite_table',
    'total_numeric', 'body_overlap_times_table', 'heading_minus_body',
    'numeric_query_short_body', 'ce_times_body_overlap')
STOP = {'the','and','for','what','how','which','this','that','trong','cua','va','la',
        'bao','nhieu','the','nay','file','uploaded','document','documents','please',
        'chuong','trinh','mon','hoc','phan','toi','minh','duoc','theo'}


def tokens(text):
    return {word for word in normalized_tokens(text) if len(word) > 1 and word not in STOP}


def features(query, item, logit, baseline_rank, pool_rank):
    if not math.isfinite(logit) or pool_rank < 1 or baseline_rank < 0:
        raise ValueError('invalid measured ranking feature input')
    expanded = normalize_retrieval_query(query)
    body = source_body(item)
    rendered = render_table(body, query, True)
    if rendered is not None:
        body = rendered
    q, b = tokens(expanded), tokens(body)
    heading = ' '.join(item.get('metadata', {}).get('heading_path', []))
    h = tokens(heading)
    overlap = len(q & b) / max(1, len(q))
    head_overlap = len(q & h) / max(1, len(q))
    qwords = normalized_tokens(expanded)
    bwords = normalized_tokens(body)
    qb = set(zip(qwords, qwords[1:]));bb = set(zip(bwords, bwords[1:]))
    codes, body_codes = set(detected_course_codes(query)), set(detected_course_codes(body))
    code_coverage = len(codes & body_codes) / max(1, len(codes))
    table = float(item.get('content_type') == 'table')
    folded = ' '.join(normalized_tokens(query))
    credit = bool(re.search(r'\b(?:credits?|tc|tin)\b', folded))
    semester = bool(re.search(r'\b(?:semesters?|terms?|ky)\b', folded))
    prereq = bool(re.search(r'\b(?:prerequisites?|truoc|quyet)\b', folded))
    total = bool(re.search(r'\b(?:total|sum|tong|cong)\b', folded))
    numeric = sum(word.isdigit() for word in b) / max(1, len(b))
    logit = max(-20., min(20., logit))
    return [logit / 10., 1. / (1. + math.exp(-logit)),
        1. / baseline_rank if baseline_rank else 0., 1. / pool_rank,
        overlap, head_overlap, len(qb & bb) / max(1, len(qb)), code_coverage,
        len(body_codes) / max(1, len(b)), table, math.log1p(len(body)) / 10., numeric,
        float(credit) * table, float(semester) * table, float(prereq) * table,
        float(total) * numeric, overlap * table, head_overlap - overlap,
        float(credit or total) / max(1., math.log1p(len(body))), logit / 10. * overlap]
