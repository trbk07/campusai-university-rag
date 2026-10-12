"""No egress before exact authorization; consumed pilots cannot restart."""
import copy
import hashlib

import pytest

from evaluation.common.release_artifacts import sha256, write_json
from scripts.benchmarks.phase7_final_policy_pilot import Preflight, QIDS, collect, validate_authorization, validate_packet


def packet():
    pairs=[]
    for index,qid in enumerate(QIDS):
        positive=index<6
        for arm in ('current_enhanced_baseline','official_bge_nested_oof_replay'):
            pairs.append({'qid':qid,'arm':arm,'question':'fixture question','answerable':positive,
                'tags':[],'difficulty':'hard','gold_evidence':[],
                'gold_claims':[{'claim_id':'source-gold'}] if positive else [],
                'evidence':[{'chunk_id':'source-c'}] if positive else [],
                'planned_provider_call':positive,'prompt':'fixture prompt' if positive else None,
                'prompt_sha256':hashlib.sha256(b'fixture prompt').hexdigest() if positive else None})
    return {'pairs':pairs,'max_provider_calls':12,'max_retries':0,
        'endpoint_host':'generativelanguage.googleapis.com','minimum_call_start_interval_seconds':30,
        'release_eligible':False,'test_or_holdout_read':False}


def test_requires_new_exact_authorization_before_credential_access(tmp_path):
    path=tmp_path/'packet.json'
    write_json(path,packet())
    consent=tmp_path/'authorization.json'
    write_json(consent,{'explicit_user_authorization':True,'packet_sha256':'old-eight-call-packet',
        'max_provider_calls':8,'max_retries':0,'endpoint_host':'generativelanguage.googleapis.com'})
    with pytest.raises(ValueError,match='exact twelve-prompt'):
        collect(path,consent,tmp_path/'credential-must-not-be-read.yaml',tmp_path/'output.json')
    assert not (tmp_path/'output.json').exists()


def test_consumed_output_cannot_restart_even_with_unreadable_inputs(tmp_path):
    output=tmp_path/'output.json'
    output.write_text('retained original attempt',encoding='utf8')
    with pytest.raises(FileExistsError,match='never restart'):
        collect(tmp_path/'missing-packet',tmp_path/'missing-consent',tmp_path/'missing-key',output)
    assert output.read_text(encoding='utf8')=='retained original attempt'


@pytest.mark.parametrize('change',['prompt','extra_call','negative_context','pair_question','duplicate_arm'])
def test_rejects_scope_mutations(change):
    data=copy.deepcopy(packet())
    if change=='prompt':data['pairs'][0]['prompt']='different corpus prompt'
    elif change=='extra_call':data['max_provider_calls']=13
    elif change=='negative_context':data['pairs'][-1]['evidence']=[{'chunk_id':'unplanned-c'}]
    elif change=='pair_question':data['pairs'][0]['question']='changed question'
    else:data['pairs'][1]['arm']=data['pairs'][0]['arm']
    with pytest.raises(ValueError):validate_packet(data)


def test_exact_new_scope_is_validated(tmp_path):
    data=packet();path=tmp_path/'packet.json';write_json(path,data)
    validate_authorization(path,data,{'explicit_user_authorization':True,'packet_sha256':sha256(path),
        'max_provider_calls':12,'max_retries':0,'endpoint_host':'generativelanguage.googleapis.com'})


def test_preflight_observes_real_generator_schema_without_provider_output():
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import RetrievalResult
    preflight=Preflight()
    generator=GroundedAnswerGenerator(preflight)
    evidence=[RetrievalResult('source-c','source-d',1,'Registration closes on 12 October.',
        'text',.9,'hybrid',{})]
    answer=generator.answer('When does registration close?',evidence)
    assert answer.abstained and answer.reason=='llm_error'
    assert preflight.prompts==[generator.prompt('When does registration close?',evidence)]
    generator.answer('When does registration close?',[])
    assert len(preflight.prompts)==1
