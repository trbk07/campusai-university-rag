"""Controlled transport tests only; no native predictions or accuracy evidence."""
import hashlib
import json

import pytest

from scripts.release.blind_holdout import commitment
from scripts.release.collect_native import collect, preflight


def setup_protocol(root):
    def write(name, value):
        path=root/name
        path.write_text(json.dumps(value),encoding='utf-8')
        return hashlib.sha256(path.read_bytes()).hexdigest()
    cases=[{'id':f'case-{i}','doc_ids':['a'*64],'language':'en',
            'turns':[f'Documented policy number {i}?']+(['And its exceptions?'] if i==0 else []),
            'family_commitments':['b'*64]} for i in range(200)]
    bank=write('public.json',{'cases':cases})
    review=write('review.json',{'development_gold_ready':True,'peer_review_validation':[
        {'case_id':c['id'],'status':'SOURCE_BOUND_AI_APPROVAL'} for c in cases]})
    runtime=write('runtime.json',{'revision':1})
    retained=write('old-native.json',{'attempts':[]})
    write('registry.json',{'question_lock_registry':{'entries':{}}})
    scope={'public_bank_sha256':bank,'cases':200,'turns':201,
           'frozen_files_fingerprint':commitment({'runtime.json':runtime}),
           'source_review_sha256':review,'failure_policy':'stop'}
    protocol={'external_request_scope':scope,'external_request_scope_sha256':commitment(scope),
              'public_bank_path':'public.json','public_bank_sha256':bank,
              'source_review_path':'review.json','source_review_sha256':review,
              'frozen_files_sha256':{'runtime.json':runtime},'expected_cases':200,'expected_turns':201,
              'base_url':'http://127.0.0.1:8001','failure_policy':'stop',
              'question_lock_registry_path':'registry.json','retained_native_files_sha256':{'old-native.json':retained}}
    return protocol


def test_native_collection_controlled_transport_keeps_context_and_remains_ungraded(tmp_path):
    protocol=setup_protocol(tmp_path);calls=[]
    def controlled(base,body,case,turn):
        assert set(body)=={'question','doc_ids','language','history'}
        if case=='case-0' and turn==1:
            assert body['history']==[{'role':'user','content':'Documented policy number 0?'},
                                     {'role':'assistant','content':'Actual recorded transport output case-0:0'}]
        elif turn==0:
            assert body['history']==[]
        calls.append((case,turn))
        return 200,{'ok':True,'answer':{'answer':f'Actual recorded transport output {case}:{turn}'}},f'{case}:{turn}'
    output=tmp_path/'out'
    result=collect(tmp_path,protocol,protocol['external_request_scope_sha256'],output,send=controlled)
    assert len(calls)==201 and result['status']=='COLLECTED_UNGRADED' and result['accuracy_percent'] is None
    assert len(json.loads((tmp_path/'registry.json').read_text())['question_lock_registry']['entries'])==201
    # Same candidate resumes without any resend, including a complete CTX.
    again=collect(tmp_path,protocol,protocol['external_request_scope_sha256'],output,send=controlled)
    assert len(calls)==201 and again['attempted_turns']==201
    assert not (tmp_path/'.native-collection.lock').exists()


def test_native_collection_source_change_aborts_before_next_question_but_saves_first_lock(tmp_path):
    protocol=setup_protocol(tmp_path);calls=[]
    def changed(base,body,case,turn):
        calls.append((case,turn));(tmp_path/'runtime.json').write_text('changed')
        return 200,{'ok':True,'answer':{'answer':'Controlled response'}},'first-request'
    with pytest.raises(ValueError,match='binding_mismatch'):
        collect(tmp_path,protocol,protocol['external_request_scope_sha256'],tmp_path/'out',send=changed)
    assert calls==[('case-0',0)]
    saved=json.loads((tmp_path/'out/results.json').read_text())
    assert saved['status']=='ABORTED_EXCEPTION' and saved['attempted_turns']==1
    assert len(json.loads((tmp_path/'registry.json').read_text())['question_lock_registry']['entries'])==1


def test_native_collection_timeout_locked_no_fake_context_no_automatic_resend(tmp_path):
    protocol=setup_protocol(tmp_path);calls=[]
    def timeout(base,body,case,turn):
        calls.append((case,turn));raise TimeoutError('controlled infrastructure failure')
    result=collect(tmp_path,protocol,protocol['external_request_scope_sha256'],tmp_path/'out',send=timeout)
    assert result['status']=='STOPPED_ON_ERROR' and result['attempted_turns']==1
    assert result['predictions'][0]['status']=='failed'
    def next_case(base,body,case,turn):
        assert case!='case-0' and not body['history']
        calls.append((case,turn));return 200,{'ok':True,'answer':{'answer':'Controlled output'}},'next'
    result=collect(tmp_path,protocol,protocol['external_request_scope_sha256'],tmp_path/'out',send=next_case)
    assert calls.count(('case-0',0))==1 and ('case-0',1) not in calls
    assert result['attempted_turns']==200 and result['expected_turns']==201
    assert result['accuracy_percent'] is None and result['status']=='COLLECTION_INCOMPLETE'


def test_native_collection_rejects_unreviewed_bank_unauthorized_scope_and_live_session(tmp_path):
    protocol=setup_protocol(tmp_path)
    with pytest.raises(ValueError,match='exact_egress_scope'):
        preflight(tmp_path,protocol,'0'*64)
    (tmp_path/'.native-collection.lock').write_text('unresolved existing process')
    with pytest.raises(ValueError,match='session_active_or_unresolved'):
        collect(tmp_path,protocol,protocol['external_request_scope_sha256'],tmp_path/'out')
    (tmp_path/'.native-collection.lock').unlink()
    review=json.loads((tmp_path/'review.json').read_text());review['peer_review_validation'].pop()
    (tmp_path/'review.json').write_text(json.dumps(review))
    digest=hashlib.sha256((tmp_path/'review.json').read_bytes()).hexdigest()
    protocol['source_review_sha256']=digest;protocol['external_request_scope']['source_review_sha256']=digest
    protocol['external_request_scope_sha256']=commitment(protocol['external_request_scope'])
    with pytest.raises(ValueError,match='whole_cohort_source_review_required'):
        collect(tmp_path,protocol,protocol['external_request_scope_sha256'],tmp_path/'out')
    assert not (tmp_path/'out/attempts.sqlite3').exists()
