"""Small transport fixtures cannot become an internal/public acceptance PASS."""
import json

import pytest

from evaluation.grounding.checkpoint import PROTOCOL,digest
from evaluation.grounding.checkpoint_release import load_checkpoint,prediction_rows
from evaluation.grounding.validate_grounding_release import validate


def runtime_report():
    return {'mode':'runtime','schema_version':2,'rows':[],'metrics':{},
            'generation':{'kind':'native_checkpoint','protocol':PROTOCOL,'gold_seeded':False}}


@pytest.fixture
def checkpoint(tmp_path):
    files={'source-pool.json':{'runs':[]},'predictions.jsonl':[],
           'pending.jsonl':[{'id':'unit-pending'}]}
    for name,value in files.items():
        text=json.dumps(value) if name.endswith('pool.json') else ''.join(json.dumps(v)+'\n' for v in value)
        (tmp_path/name).write_text(text,encoding='utf8')
    run={'protocol':PROTOCOL,'generation_kind':'native_checkpoint','pipeline_predictions':0,
         'pending':1,'fresh_provider_posts':0,'fresh_model_outputs':0,'official_predictions':0,
         'artifacts':{name:digest(tmp_path/name) for name in files}}
    (tmp_path/'run.json').write_text(json.dumps(run),encoding='utf8')
    return tmp_path,run


def save(path,run):
    (path/'run.json').write_text(json.dumps(run),encoding='utf8')


@pytest.mark.parametrize('field,value',[
    ('generation_kind','native'),('protocol','unverified'),('fresh_provider_posts',1),
    ('fresh_model_outputs',1),('official_predictions',1),('pipeline_predictions',1),('pending',0),
    ('fresh_provider_posts',False),('official_predictions',False),('pipeline_predictions',False),
])
def test_forged_protocol_population_or_fresh_counts_fail_closed(checkpoint,field,value):
    path,run=checkpoint;run[field]=value;save(path,run)
    with pytest.raises(ValueError):load_checkpoint(path)


@pytest.mark.parametrize('name',['source-pool.json','predictions.jsonl','pending.jsonl'])
def test_altered_checkpoint_artifact_cannot_be_scored(checkpoint,name):
    path,run=checkpoint
    (path/name).write_bytes((path/name).read_bytes()+b' ')
    with pytest.raises(ValueError,match='artifacts'):load_checkpoint(path)


def test_offline_miss_is_kept_pending_not_a_negative_prediction(checkpoint):
    path,run=checkpoint
    actual,predictions,pending=load_checkpoint(path)
    assert not predictions and pending==[{'id':'unit-pending'}]


def test_duplicate_or_both_pending_and_completed_ids_fail_closed(checkpoint):
    path,run=checkpoint
    predictions=[{'id':'unit-pending','protocol':PROTOCOL,'fresh_provider_posts':0,'fresh_model_outputs':0}]
    (path/'predictions.jsonl').write_text(json.dumps(predictions[0])+'\n')
    run['pipeline_predictions']=1;run['artifacts']['predictions.jsonl']=digest(path/'predictions.jsonl');save(path,run)
    with pytest.raises(ValueError,match='population'):load_checkpoint(path)


def test_checkpoint_cannot_use_a_benchmark_label_in_request(tmp_path):
    gold={'id':'unit','question':'What is required?','language':'en','answerable':True}
    benchmark=tmp_path/'benchmark.jsonl';benchmark.write_text(json.dumps(gold)+'\n')
    with pytest.raises(ValueError,match='user-input-only'):
        prediction_rows(benchmark,[{'id':'unit','request':{'question':gold['question'],'language':'en','answerable':True}}])


def test_checkpoint_requires_physical_verification_even_without_a_root():
    report=runtime_report()
    report['generation']={'kind':'native_checkpoint','protocol':PROTOCOL,'gold_seeded':False}
    errors=validate(report,acceptance_scope='phase5_acceptance')
    assert 'checkpoint_requires_physical_verification' in errors


def test_internal_checkpoint_never_qualifies_public_release():
    report=runtime_report()
    report['generation']={'kind':'native_checkpoint','protocol':PROTOCOL,'gold_seeded':False}
    assert 'checkpoint_is_internal_acceptance_only' in validate(report)


def test_physical_verifier_failure_cannot_turn_into_an_acceptance_pass(monkeypatch,tmp_path):
    import evaluation.grounding.checkpoint_release as module
    calls=[]
    def reject(report,root):
        calls.append(root)
        raise ValueError('Altered capture or output mismatch')
    monkeypatch.setattr(module,'verify_checkpoint_report',reject)
    errors=validate(runtime_report(),root=tmp_path,acceptance_scope='phase5_acceptance')
    assert calls==[tmp_path] and errors==['report_structure_invalid']
