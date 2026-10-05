from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import shutil

import pytest

from evaluation.benchmarks.dev_inheritance import (
    consumed_candidate_rows, file_bindings, inheritance_audit, inheritance_review_error,
    preserved_index, safe_reference, validate_inheritance,
)
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.benchmarks.owner_generation import course_facts, generated_audit, generated_row
from evaluation.common.release_artifacts import sha256, write_json
from evaluation.reranker.supplemental_gates import review_audit_errors


def write_rows(path, rows):
    path.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf8')


def fixture(tmp_path, monkeypatch):
    old=tmp_path/'old'; new=tmp_path/'new'; benchmark=tmp_path/'parent'
    benchmark.mkdir(); (old/'doc').mkdir(parents=True)
    table={'headers':['STT','Mã học phần','Học phần','Số tín chỉ'],
           'rows':[['1','ABC1001','Đại số','4'],['2','XYZ1002','Vật lý','3']]}
    evidence={('doc','table'):{'doc_id':'doc','chunk_id':'table','content_type':'table','page':1,
                             'content':json.dumps(table,ensure_ascii=False),'metadata':{'document_type':'curriculum'}}}
    write_json(old/'doc/bm25.json',{'items':list(evidence.values())})
    write_json(old/'manifest.json',{'documents':['doc'],'document_manifests':[
        {'document_id':'doc','bm25_sha256':sha256(old/'doc/bm25.json'),'item_count':1}]})
    shutil.copytree(old,new)
    policy={'owner_identity':'Owner','owner_self_review_allowed':True,'project_scope':'single_owner_personal_project'}
    write_json(benchmark/'phase7_review_policy.json',policy)
    auth={'profile':'personal_owner_source_checked_ai','owner_identity':'Owner',
          'approval_source':'project_owner_chat_instruction','approval_statement':'t duyệt hết nên bạn cứ nhập tên tác giải là t',
          'generation_statement':'nếu k có thì tự tạo đi, t cho phép','independent_human_review_claim':False,
          'recorded_at':(datetime.now(timezone.utc)-timedelta(seconds=5)).isoformat()}
    spec={'qid':'human-legacy','family':'legacy-facts','kind':'sum','facts':course_facts(evidence)}
    generated={spec['qid']:generated_row(spec,auth)}
    report_path=tmp_path/'candidate.json'
    report={'status':'conditional','index_sha256':sha256(old/'manifest.json'),'splits':{}}
    all_rows=[]
    for split in ('dev','test','holdout'):
        split_row={**generated[spec['qid']],'qid':'human-'+split,'split':split}
        generated[split_row['qid']]={**split_row,'split':'dev'}
        all_rows.append(split_row)
        write_rows(benchmark/f'human_retrieval_{split}.jsonl',[split_row])
        report['splits']['human_'+split]={'benchmark_sha256':sha256(benchmark/f'human_retrieval_{split}.jsonl'),
                                         'caps':{'40':{'per_query':[{'qid':split_row['qid'],'candidates':[]}]}}}
    write_rows(benchmark/'human_retrieval.jsonl',all_rows)
    generated.pop(spec['qid'])
    write_rows(benchmark/'human_retrieval_review_audit.jsonl',generated_audit(auth,generated))
    write_json(report_path,report)
    from evaluation.benchmarks import owner_generation, owner_review
    monkeypatch.setattr(owner_generation,'load_generation',lambda *_:(auth,generated))
    monkeypatch.setattr(owner_review,'load_confirmation',lambda _:({'owner_identity':'Owner'},[]))
    manifest={'schema_version':1,'profile':'legacy_source_checked_dev_inheritance_v1',
        'recorded_at':datetime.now(timezone.utc).isoformat(),'owner_identity':'Owner',
        'dev_only':True,'new_heldout_claim':False,'index_sha256':sha256(new/'manifest.json'),'records':3,
        'parents':[{'benchmark_dir':'parent','index_dir':'old','benchmark_files':file_bindings(benchmark),
            'index_files':file_bindings(old),'mode':'consumed_candidate_splits','candidate_report':'candidate.json',
            'candidate_report_sha256':sha256(report_path),'qids':sorted(generated)}]}
    return old,new,benchmark,policy,manifest,auth,generated


def test_failed_candidate_measurement_consumes_exact_inputs_and_preserves_origin(tmp_path,monkeypatch):
    old,new,parent,policy,manifest,auth,generated=fixture(tmp_path,monkeypatch)
    bundle=validate_inheritance(manifest,new,policy,root=tmp_path)
    assert set(bundle['rows'])==set(generated)
    assert {r['split'] for r in bundle['rows'].values()}=={'dev'}
    assert {o['original_split'] for o in bundle['origins'].values()}=={'dev','test','holdout'}
    assert all(row['author_type']=='ai' and row['generation_authorization_sha256']==digest_record(auth)
               for row in bundle['rows'].values())
    authorization={**auth,'_validated_dev_inheritance':bundle}
    audit=inheritance_audit(bundle)
    assert review_audit_errors(list(bundle['rows'].values()),audit,new,owner_identity='Owner',
                              generation_authorization=authorization,generated_records=bundle['rows'])==[]
    assert all(not inheritance_review_error(bundle['rows'][item['qid']],item,authorization) for item in audit)


def test_mixed_new_and_inherited_audit_keeps_distinct_authorizations(tmp_path,monkeypatch):
    _,new,_,policy,manifest,old_auth,_=fixture(tmp_path,monkeypatch)
    bundle=validate_inheritance(manifest,new,policy,root=tmp_path)
    auth={**old_auth,'dev_inheritance_sha256':'a'*64}
    fresh={**next(iter(bundle['rows'].values())),'qid':'fresh',
           'generation_authorization_sha256':digest_record(auth)}
    expected={**bundle['rows'],'fresh':fresh}
    validated={**auth,'_validated_dev_inheritance':bundle}
    audit=generated_audit(validated,expected)
    assert len(audit)==4
    assert review_audit_errors(list(expected.values()),audit,new,owner_identity='Owner',
                              generation_authorization=validated,generated_records=expected)==[]
    expected['human-test']={**expected['human-test'],'split':'holdout'}
    with pytest.raises(ValueError,match='inherited export differs'):
        generated_audit(validated,expected)


def test_inherited_review_cannot_use_a_different_owner(tmp_path,monkeypatch):
    _,new,_,policy,manifest,auth,_=fixture(tmp_path,monkeypatch)
    bundle=validate_inheritance(manifest,new,policy,root=tmp_path)
    errors=review_audit_errors(list(bundle['rows'].values()),inheritance_audit(bundle),new,
        owner_identity='Another owner',generation_authorization={**auth,'_validated_dev_inheritance':bundle},
        generated_records=bundle['rows'])
    assert errors and all(error.startswith('invalid_dev_inheritance:') for error in errors)


def test_dev_absence_selection_validates_only_the_selected_original_records(tmp_path,monkeypatch):
    _,new,parent,policy,manifest,auth,generated=fixture(tmp_path,monkeypatch)
    dev_auth={**auth,'dev_only':True,'new_heldout_claim':False}
    for qid in generated:
        generated[qid].update(generation_authorization_sha256=digest_record(dev_auth),
                              source_validation={'kind':'dev_absent_field'})
    auth['_validated_dev_authorization']=dev_auth
    write_rows(parent/'human_retrieval_dev.jsonl',list(generated.values()))
    audit=generated_audit(auth,generated)
    audit.append({'qid':'unselected-legacy','review_evidence_kind':'owner_directed_generation'})
    write_rows(parent/'human_retrieval_review_audit.jsonl',audit)
    manifest['parents'][0].update(mode='dev_only_absent_fields',benchmark_files=file_bindings(parent))
    bundle=validate_inheritance(manifest,new,policy,root=tmp_path)
    assert len(bundle['rows'])==3 and 'unselected-legacy' not in bundle['rows']


@pytest.mark.parametrize('change',['split','question','origin_hash','manifest_hash','export_hash','missing_bundle'])
def test_inheritance_review_rejects_semantic_mutation_or_heldout(tmp_path,monkeypatch,change):
    _,new,_,policy,manifest,auth,_=fixture(tmp_path,monkeypatch)
    bundle=validate_inheritance(manifest,new,policy,root=tmp_path)
    item=deepcopy(inheritance_audit(bundle)[0]); row=deepcopy(bundle['rows'][item['qid']])
    authorization={**auth,'_validated_dev_inheritance':bundle}
    if change=='split': row['split']='holdout'
    elif change=='question': row['question']+=' changed'
    elif change=='origin_hash': item['original_record_sha256']='f'*64
    elif change=='manifest_hash': item['inheritance_manifest_sha256']='f'*64
    elif change=='export_hash': item['exported_record_sha256']='f'*64
    else: authorization=auth
    assert inheritance_review_error(row,item,authorization)


@pytest.mark.parametrize('change',['selected_qids','current_index','parent_file','duplicate_parent','future','heldout_claim'])
def test_inheritance_rejects_changed_proof_or_scope(tmp_path,monkeypatch,change):
    _,new,parent,policy,manifest,_,_=fixture(tmp_path,monkeypatch)
    if change=='selected_qids': manifest['parents'][0]['qids'].pop()
    elif change=='current_index': manifest['index_sha256']='f'*64
    elif change=='parent_file': (parent/'human_retrieval.jsonl').write_text('{}\n')
    elif change=='duplicate_parent': manifest['parents'].append(deepcopy(manifest['parents'][0]))
    elif change=='future': manifest['recorded_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    else: manifest['new_heldout_claim']=True
    with pytest.raises(ValueError): validate_inheritance(manifest,new,policy,root=tmp_path)


def test_current_index_cannot_change_historical_document_bytes(tmp_path,monkeypatch):
    old,new,_,_,manifest,_,_=fixture(tmp_path,monkeypatch)
    (new/'doc/bm25.json').write_text('{}\n')
    with pytest.raises(ValueError,match='historical document bytes'):
        preserved_index(old,new,manifest['parents'][0]['index_files'])


def test_missing_candidate_pairs_are_not_exposure_proof(tmp_path,monkeypatch):
    old,_,parent,_,_,_,_=fixture(tmp_path,monkeypatch)
    path=tmp_path/'candidate.json'; report=json.loads(path.read_text())
    report['splits']['human_test']['caps']['40']['per_query']=[]
    write_json(path,report)
    with pytest.raises(ValueError,match='exact frozen split'):
        consumed_candidate_rows(parent,path,sha256(old/'manifest.json'))


def test_artifact_cannot_inject_verified_inheritance_metadata(tmp_path):
    from evaluation.benchmarks.owner_generation import load_generation
    write_json(tmp_path/'phase7_review_policy.json',{})
    write_json(tmp_path/'phase7_generation_authorization.json',{'_validated_dev_inheritance':{'dev_only':True}})
    with pytest.raises(ValueError,match='internal generation validation metadata'):
        load_generation(tmp_path,tmp_path/'missing-index')


@pytest.mark.parametrize('name',['../outside','C:/outside','/outside','\\\\host\\share'])
def test_inheritance_paths_cannot_escape_workspace(tmp_path,name):
    with pytest.raises(ValueError,match='unsafe'): safe_reference(tmp_path,name)
