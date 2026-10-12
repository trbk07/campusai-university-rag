import math
import pytest

from campusai.retrieval.learned_rank_features import features, FEATURE_NAMES


def candidate(**extra):
    return {'chunk_id':'chunk','doc_id':'document','page':2,'content_type':'text',
            'content':'Course CS201 has 3 credits.','metadata':{'heading_path':['Courses']},**extra}


def test_inference_features_never_use_benchmark_or_source_identifiers():
    a=features('How many credits for CS201?',candidate(),2.,1,1)
    b=features('How many credits for CS201?',candidate(qid='other',doc_id='different',
        chunk_id='unrelated',page=999,gold_evidence=['fabricated'],difficulty='hard'),2.,1,1)
    assert a==b and len(a)==len(FEATURE_NAMES) and all(math.isfinite(x) for x in a)


@pytest.mark.parametrize('score',[float('nan'),float('inf'),-float('inf')])
def test_invalid_provider_scores_fail_closed(score):
    with pytest.raises(ValueError):features('Course CS201?',candidate(),score,1,1)


def test_course_code_coverage_distinguishes_absent_identifier():
    a=features('CS201?',candidate(),1.,0,20)
    b=features('CS999?',candidate(),1.,0,20)
    assert a[FEATURE_NAMES.index('query_code_coverage')]==1
    assert b[FEATURE_NAMES.index('query_code_coverage')]==0
