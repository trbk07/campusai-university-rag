"""Transport fixtures prove replay integrity; they are never release evidence."""
from copy import deepcopy
import json

import pytest

from campusai.llm.client import GeminiClient
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from evaluation.grounding.checkpoint import (
    NativeCapturePool, CheckpointClient, CaptureMissing, digest, reprocess,
)
from evaluation.grounding.collect_native_predictions import collect, inference_request
from evaluation.grounding.native_artifacts import load_native_run
from evaluation.grounding.repair_benchmark import stable_hash
from tests.test_basic_rag import FakeRetriever, evidence, valid_payload


@pytest.fixture
def capture(tmp_path):
    client=GeminiClient(api_key='unit-test-placeholder',max_retries=0,cache=None)
    service=CampusAIQueryService(FakeRetriever([evidence()]),
        GroundedAnswerGenerator(client,source_citations=True))
    rows=[{'id':'unit-only','question':'Which prerequisite course is required?','language':'en'}]
    def transport(*args,**kwargs):
        payload=valid_payload()
        payload['citations']=[{'chunk_id':'c1'}]
        return {'candidates':[{'content':{'parts':[{'text':json.dumps(payload)}]}}]}
    directory=tmp_path/'capture'
    try:
        run=collect(service,rows,client,max_provider_calls=1,output=directory,transport=transport)
    finally:
        service.close()
    run.update(model=client.model,config_sha256='unit-config',index_manifest_sha256='unit-index',
               source_identity={'unit_fixture':True})
    (directory/'run.json').write_text(json.dumps(run),encoding='utf8')
    requests={row['id']:inference_request(row) for row in rows}
    pool=NativeCapturePool(client,config_sha256='unit-config',index_sha256='unit-index',requests=requests)
    pool.add(directory)
    return client,pool,directory,requests


def test_exact_response_uses_current_json_validation_without_transport(capture,monkeypatch):
    client,pool,directory,requests=capture
    raw=load_native_run(directory)[2][0]
    def forbidden(*args,**kwargs):raise AssertionError('Offline reuse attempted HTTP')
    monkeypatch.setattr('campusai.llm.client._request_json',forbidden)
    checkpoint=CheckpointClient(client,pool)
    checkpoint.begin('unit-only')
    actual=client.generate_json(raw['prompt'],schema=pool.schema)
    assert actual['answer']==valid_payload()['answer']
    assert len(checkpoint.uses)==1
    assert checkpoint.uses[0]['origin']['sha256']==digest(directory/'run.json')
    assert checkpoint.uses[0]['origin']['source_identity']=={'unit_fixture':True}


@pytest.mark.parametrize('mutation',['question','case','body','endpoint'])
def test_reuse_requires_exact_request_case_endpoint_and_body(capture,mutation):
    client,pool,directory,requests=capture
    raw=load_native_run(directory)[2][0]
    body=stable_hash(client.prepare_request(raw['prompt'],**raw['generation_arguments']))
    if mutation=='question':
        pool.requests['unit-only']['question']='Different question'
        service=CampusAIQueryService(FakeRetriever([evidence()]),GroundedAnswerGenerator(client))
        try:
            with pytest.raises(ValueError,match='bound user input'):
                reprocess(service,CheckpointClient(client,pool),'unit-only',requests['unit-only'])
        finally:service.close()
    else:
        with pytest.raises(CaptureMissing):
            pool.lookup('wrong' if mutation=='case' else 'unit-only',
                'wrong' if mutation=='endpoint' else client.endpoint,'wrong' if mutation=='body' else body)


@pytest.mark.parametrize('filename',['run.json','raw-model.jsonl','predictions.jsonl','provider-posts.jsonl'])
def test_mutated_original_capture_is_rejected_even_after_pool_loaded(capture,filename):
    client,pool,directory,requests=capture
    raw=load_native_run(directory)[2][0]
    path=directory/filename
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='changed'):
        pool.lookup('unit-only',client.endpoint,
                    stable_hash(client.prepare_request(raw['prompt'],**raw['generation_arguments'])))


@pytest.mark.parametrize('field',['gold_claims','answerable','expected_output','category','split'])
def test_benchmark_labels_cannot_enter_reprocessing(capture,field):
    client,pool,directory,requests=capture
    request={**requests['unit-only'],field:'forbidden'}
    with pytest.raises(ValueError,match='user-input inference projection'):
        NativeCapturePool(client,config_sha256='unit-config',index_sha256='unit-index',
                          requests={'unit-only':request})


@pytest.mark.parametrize('field',['model','config_sha256','index_manifest_sha256'])
def test_mismatched_capture_identity_is_not_reused(capture,field):
    client,old,directory,requests=capture
    path=directory/'run.json'
    run=json.loads(path.read_text());run[field]='other';path.write_text(json.dumps(run))
    pool=NativeCapturePool(client,config_sha256='unit-config',index_sha256='unit-index',requests=requests)
    pool.add(directory)
    assert not pool.records


def test_missing_input_is_not_a_provider_failure_or_negative_prediction(capture):
    client,pool,directory,requests=capture
    pool.records.clear()
    checkpoint=CheckpointClient(client,pool)
    service=CampusAIQueryService(FakeRetriever([evidence()]),
        GroundedAnswerGenerator(client,source_citations=True))
    try:
        with pytest.raises(CaptureMissing):
            reprocess(service,checkpoint,'unit-only',requests['unit-only'])
    finally:service.close()


def test_pool_selection_is_isolated_from_caller_mutation(capture):
    client,pool,directory,requests=capture
    raw=load_native_run(directory)[2][0]
    body=stable_hash(client.prepare_request(raw['prompt'],**raw['generation_arguments']))
    value=pool.lookup('unit-only',client.endpoint,body)
    original=deepcopy(value)
    value['capture']['raw_model_text']='invented'
    requests['unit-only']['question']='mutated'
    assert pool.lookup('unit-only',client.endpoint,body)==original
    assert pool.requests['unit-only']['question']!='mutated'
