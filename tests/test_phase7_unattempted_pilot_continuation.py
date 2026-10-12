"""An authorization continuation never includes an attempted prompt."""
import copy
import pytest
from scripts.benchmarks.continue_phase7_unattempted_pilot import remaining_pairs


def inputs():
    pairs=[{'qid':f'q{i}','arm':'baseline','planned_provider_call':True,'prompt_sha256':f'hash{i}'} for i in range(12)]
    prior={'status':'PARTIAL_PROVIDER_OR_PRECHECK_FAILURE','source_stable':True,'attempted_calls':1,
        'observations':[{'qid':'q0','arm':'baseline','llm_calls':[{'prompt_sha256':'hash0','provider_status':'failed'}]}]}
    return {'pairs':pairs},prior


def test_failed_first_prompt_is_excluded_and_total_stays_twelve():
    packet,prior=inputs();suffix=remaining_pairs(packet,prior)
    assert len(suffix)==11 and suffix[0]['qid']=='q1' and all(p['qid']!='q0' for p in suffix)
    assert prior['attempted_calls']+sum(p['planned_provider_call'] for p in suffix)==12


def test_chained_continuation_excludes_both_failed_prompts():
    packet,prior=inputs()
    prior['status']='CONTINUATION_PARTIAL_PROVIDER_OR_PRECHECK_FAILURE'
    prior['attempted_calls']=2
    prior['observations'].append({'qid':'q1','arm':'baseline',
        'llm_calls':[{'prompt_sha256':'hash1','provider_status':'failed'}]})
    suffix=remaining_pairs(packet,prior)
    assert len(suffix)==10 and suffix[0]['qid']=='q2'
    assert not {p['qid'] for p in suffix}&{'q0','q1'}
    assert prior['attempted_calls']+sum(p['planned_provider_call'] for p in suffix)==12


@pytest.mark.parametrize('status',['CONTINUATION_IN_PROGRESS','PENDING_SEMANTIC_REVIEW'])
def test_running_or_completed_journal_cannot_continue(status):
    packet,prior=inputs();prior['status']=status
    with pytest.raises(ValueError):remaining_pairs(packet,prior)


@pytest.mark.parametrize('tamper',['missing_accounting','wrong_hash','non_prefix','source_unstable','extra_call'])
def test_rejects_ambiguous_or_excess_prior_calls(tamper):
    packet,prior=inputs();prior=copy.deepcopy(prior)
    if tamper=='missing_accounting':prior['observations'][0]['llm_calls']=[]
    elif tamper=='wrong_hash':prior['observations'][0]['llm_calls'][0]['prompt_sha256']='different'
    elif tamper=='non_prefix':prior['observations'][0]['qid']='q1'
    elif tamper=='source_unstable':prior['source_stable']=False
    else:prior['attempted_calls']=2
    with pytest.raises(ValueError):remaining_pairs(packet,prior)
