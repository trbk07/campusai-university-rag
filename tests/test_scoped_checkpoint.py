"""Synthetic transports test provenance integrity, never model quality."""
from dataclasses import replace
import json

import pytest

from campusai.llm.client import GeminiClient
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from evaluation.grounding.checkpoint import NativeCapturePool, CaptureMissing, digest
from evaluation.grounding.scoped_checkpoint import ScopedCapturePool
from evaluation.grounding.collect_native_predictions import collect, inference_request
from tests.test_basic_rag import FakeRetriever, evidence, valid_payload


DOC = 'a' * 64
OTHER = 'b' * 64


def index(root, *, selected='same selected source', unrelated='old unrelated source'):
    records = []
    for doc, content in [(DOC, selected), (OTHER, unrelated)]:
        folder = root/doc
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'bm25.json').write_text(json.dumps({'content':content}),encoding='utf-8')
        (folder/'dense.json').write_text('dense:'+content,encoding='utf-8')
        records.append({'document_id':doc,'bm25_sha256':digest(folder/'bm25.json')})
    (root/'manifest.json').write_text(json.dumps({'documents':[DOC,OTHER],'document_manifests':records,
        'index_type':'unit-only','model_name':'unit-encoder','model_revision':'unit-revision',
        'embedding_dimension':3}),encoding='utf-8')


@pytest.fixture
def capture(tmp_path):
    old, current = tmp_path/'old', tmp_path/'current'
    index(old); index(current,unrelated='repaired unrelated source')
    client = GeminiClient(api_key='unit-test-placeholder',max_retries=0,cache=None)
    service = CampusAIQueryService(FakeRetriever([replace(evidence(),doc_id=DOC)]),
                                  GroundedAnswerGenerator(client,source_citations=True))
    rows = [{'id':'unit-only','question':'Which prerequisite course is required?',
             'language':'en','selected_doc_ids':[DOC]}]
    def transport(*_a, **_kw):
        payload = valid_payload(); payload['citations']=[{'chunk_id':'c1'}]
        return {'candidates':[{'content':{'parts':[{'text':json.dumps(payload)}]}}]}
    folder = tmp_path/'capture'
    try: run = collect(service,rows,client,max_provider_calls=1,output=folder,transport=transport)
    finally: service.close()
    run.update(model=client.model,config_sha256='unit-config',index_manifest_sha256=digest(old/'manifest.json'),
               index_path=str(old),source_identity={'unit_fixture':True})
    (folder/'run.json').write_text(json.dumps(run),encoding='utf-8')
    requests = {row['id']:inference_request(row) for row in rows}
    return client,old,current,folder,requests


def pool(capture):
    client,old,current,folder,requests = capture
    result = ScopedCapturePool(client,index_root=current,index_sha256=digest(current/'manifest.json'),
                              config_sha256='unit-config',requests=requests)
    result.add(folder)
    return result


def test_unchanged_selected_bytes_reuse_exact_http_but_keep_original_identity(capture):
    client,old,current,folder,requests = capture
    before = (folder/'run.json').read_bytes()
    p = pool(capture)
    assert len(p.records)==1
    key = next(iter(p.records))
    value = p.lookup(*key)
    proof = value['origin']['selected_index_scope']
    assert proof['source_manifest_sha256']!=proof['target_manifest_sha256']
    assert set(proof['selected_files'])=={DOC}
    assert value['origin']['source_identity']=={'unit_fixture':True}
    assert (folder/'run.json').read_bytes()==before
    strict = NativeCapturePool(client,index_sha256=digest(current/'manifest.json'),
                               config_sha256='unit-config',requests=requests)
    strict.add(folder)
    assert not strict.records
    for field in (0,1,2):
        changed = list(key); changed[field]='wrong'
        with pytest.raises(CaptureMissing):p.lookup(*changed)


@pytest.mark.parametrize('mutation',['selected_bm25','selected_dense','missing_dense','model','source_manifest','missing_scope','expanded_scope','unsafe_scope'])
def test_changed_or_unproven_selected_scope_is_not_reused(capture,mutation):
    client,old,current,folder,requests = capture
    if mutation=='selected_bm25':index(current,selected='changed selected source')
    elif mutation=='selected_dense':(current/DOC/'dense.json').write_text('changed vector bytes')
    elif mutation=='missing_dense':(current/DOC/'dense.json').unlink()
    elif mutation=='model':
        path=current/'manifest.json'; manifest=json.loads(path.read_text()); manifest['model_revision']='different'
        path.write_text(json.dumps(manifest))
    elif mutation=='source_manifest':(old/'manifest.json').write_bytes((old/'manifest.json').read_bytes()+b' ')
    else:
        request = requests['unit-only']
        if mutation=='missing_scope':request.pop('doc_ids')
        elif mutation=='expanded_scope':request['doc_ids']=[DOC,OTHER]
        else:request['doc_ids']=['../escape']
    assert not pool(capture).records


@pytest.mark.parametrize('target',['source_manifest','target_manifest','source_bm25','target_bm25','source_dense','target_dense'])
def test_scope_proof_is_revalidated_after_pool_load(capture,target):
    client,old,current,folder,requests = capture
    p=pool(capture); key=next(iter(p.records))
    root=old if target.startswith('source') else current
    kind=target.split('_')[1]
    path=root/'manifest.json' if kind=='manifest' else root/DOC/(kind+'.json')
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='changed'):p.lookup(*key)


def test_target_manifest_identity_is_checked_before_reuse(capture):
    client,old,current,folder,requests = capture
    with pytest.raises(ValueError,match='manifest'):
        ScopedCapturePool(client,index_root=current,index_sha256='incorrect',config_sha256='unit-config',requests=requests)


def test_missing_retrieval_model_identity_is_not_equivalence_evidence(capture):
    client,old,current,folder,requests = capture
    for root in (old,current):
        path=root/'manifest.json'; data=json.loads(path.read_text()); data.pop('model_revision')
        path.write_text(json.dumps(data))
    # Synthetic fixture producer without this identity cannot establish it.
    path=folder/'run.json'; run=json.loads(path.read_text()); run['index_manifest_sha256']=digest(old/'manifest.json')
    path.write_text(json.dumps(run))
    assert not pool(capture).records
