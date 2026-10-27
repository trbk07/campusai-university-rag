"""Performance probes must never delete a document they did not freshly create."""
import hashlib
import json
from copy import deepcopy

import pytest

from scripts.operations import benchmark_pdf_readiness as module


@pytest.mark.parametrize('condition',['preexisting','duplicate_race','wrong_identity'])
def test_probe_does_not_delete_preexisting_duplicate_or_unexpected_document(tmp_path,monkeypatch,condition):
    source=tmp_path/'QA-native100-test.pdf';source.write_bytes(b'owned local fixture')
    identifier=hashlib.sha256(source.read_bytes()).hexdigest();calls=[]
    def request(path,**options):
        calls.append((path,options.get('method')))
        if path=='/api/documents':
            return {'documents':[{'doc_id':identifier}] if condition=='preexisting' else [],'jobs':[]}
        if path=='/api/documents/upload':
            return {'job':{'document_id':'0'*64 if condition=='wrong_identity' else identifier},
                    'duplicate':condition=='duplicate_race'}
        if options.get('method')=='DELETE':
            pytest.fail('A probe must never delete a pre-existing or unexpected source')
        raise AssertionError('Unexpected network path')
    monkeypatch.setattr(module,'request',request)
    with pytest.raises(ValueError):module.measure(source,1,tmp_path/'report.json')
    assert not any(method=='DELETE' for _path,method in calls)


@pytest.mark.parametrize('defect',['none','page_loss','text_loss','missing_chunk','wrong_doc',
                                  'changed_index_text','missing_vector','hash_model','old_coverage'])
def test_native_readiness_requires_source_and_real_index_integrity(tmp_path,defect):
    from scripts.operations.benchmark_native_readiness import inspect_ingestion
    from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION
    identifier='c'*64; store=tmp_path/'store'/identifier; index=tmp_path/'index'/identifier
    store.mkdir(parents=True);index.mkdir(parents=True)
    item={'chunk_id':'c1','doc_id':identifier,'page':1,'content':'Expected source text.'}
    meta={'doc_id':identifier,'page_count':1,'metadata':{'text_coverage_version':TEXT_COVERAGE_VERSION},
          'chunks':[item]}
    bm25={'items':[deepcopy(item)]}
    dense={'items':[deepcopy(item)],'vectors':[[.1,.2]],'model_name':'BAAI/bge-m3',
           'manifest':{'provider':'sentence-transformers'}}
    expected='## Page 1\nExpected source text.'; parsed=expected
    if defect=='page_loss':meta['page_count']=0
    if defect=='text_loss':parsed=''
    if defect=='missing_chunk':bm25['items']=[]
    if defect=='wrong_doc':bm25['items'][0]['doc_id']='other'
    if defect=='changed_index_text':dense['items'][0]['content']='Incorrect credits:999.'
    if defect=='missing_vector':dense['vectors']=[]
    if defect=='hash_model':dense['model_name']='fallback-hash-256'
    if defect=='old_coverage':meta['metadata']['text_coverage_version']=2
    (store/'meta.json').write_text(json.dumps(meta));(store/'parsed.md').write_text(parsed)
    for name,data in [('bm25',bm25),('dense',dense)]: (index/(name+'.json')).write_text(json.dumps(data))
    if defect=='none': assert inspect_ingestion(tmp_path,identifier,{'page_count':1},expected,1)['exact_parsed_text']
    else:
        with pytest.raises(ValueError):inspect_ingestion(tmp_path,identifier,{'page_count':1},expected,1)
