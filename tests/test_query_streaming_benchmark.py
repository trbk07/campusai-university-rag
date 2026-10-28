"""The latency gate retains errors/tails and rejects cached/incomplete cohorts."""
from copy import deepcopy
import math
import pytest
from scripts.operations.benchmark_query_streaming import censored_percentile, summarize


def cohort():
    ids=[str(i) for i in range(20)]
    rows=[{'case_id':i,'client_first_model_progress_ms':1000.,'verified_answer_ms':2000.,
           'verified_source_fact':True,'response':{'ok':True,'answer':{'abstained':False}}} for i in ids]
    traces=[{'case_id':i,'trace':{'cache_hit':False,'model_stream':{'calls':[
        {'status':'complete','first_text_delta_ms':900.}]}}} for i in ids]
    attempts=[{'case_id':i} for i in ids]
    return rows,traces,attempts,ids


def failed(rows,traces,index):
    rows[index].update(client_first_model_progress_ms=None,verified_source_fact=False)
    rows[index]['response']={'ok':False,'error_code':'provider_timeout'}
    traces[index]['trace']['model_stream']['calls'][0].update(status='incomplete',first_text_delta_ms=None)


def test_one_timeout_is_infinite_tail_not_removed_or_counted_correct():
    rows,traces,attempts,ids=cohort();failed(rows,traces,6)
    metrics,passed=summarize(rows,traces,attempts,ids,True)
    assert passed and metrics['sample_count']==20 and metrics['verified_source_facts']==19
    assert metrics['provider_first_text_censored']==1
    assert metrics['provider_first_text_p95_ms']==900.
    assert metrics['provider_first_text_max_ms'] is None and metrics['provider_first_text_max_censored']


def test_two_timeouts_make_p95_unbounded_and_fail():
    rows,traces,attempts,ids=cohort();failed(rows,traces,6);failed(rows,traces,15)
    metrics,passed=summarize(rows,traces,attempts,ids,True)
    assert not passed and metrics['provider_first_text_p95_ms'] is None
    assert metrics['provider_first_text_censored']==2 and metrics['sample_count']==20


def test_one_timeout_plus_one_slow_query_fails_without_trimming():
    rows,traces,attempts,ids=cohort();failed(rows,traces,6)
    traces[5]['trace']['model_stream']['calls'][0]['first_text_delta_ms']=6000.
    metrics,passed=summarize(rows,traces,attempts,ids,True)
    assert not passed and metrics['provider_first_text_p95_ms']==6000.


def test_a_published_uncertified_fact_never_becomes_an_allowed_error_tail():
    rows,traces,attempts,ids=cohort();rows[0]['verified_source_fact']=False
    metrics,passed=summarize(rows,traces,attempts,ids,True)
    assert not passed and metrics['uncertified_published_answers']==1


@pytest.mark.parametrize('defect',['partial','cache','fake_progress','duplicate','changed_runtime','quality'])
def test_missing_provenance_or_quality_cannot_pass(defect):
    rows,traces,attempts,ids=cohort();unchanged=True
    if defect=='partial':rows.pop();traces.pop();attempts.pop()
    if defect=='cache':traces[0]['trace']['cache_hit']=True
    if defect=='fake_progress':traces[0]['trace']['model_stream']['calls']=[]
    if defect=='duplicate':attempts[-1]['case_id']=attempts[0]['case_id']
    if defect=='changed_runtime':unchanged=False
    if defect=='quality':
        for r in rows[:3]:r['verified_source_fact']=False
    _metrics,passed=summarize(rows,traces,attempts,ids,unchanged)
    assert not passed


@pytest.mark.parametrize('values',[[],[True],[math.nan],[math.inf],[-1],['2']])
def test_censoring_never_accepts_invalid_numbers(values):
    with pytest.raises(ValueError):censored_percentile(values)
