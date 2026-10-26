"""Read-only document facts must be fresh and usable during expensive inference."""
import json
import os
import threading

import pytest

from campusai.documents.registry import DocumentRegistry
from campusai.web import make_wsgi_app
from tests.test_natural_conversation import document_app
from tests.test_web_documents import call


def test_structural_pdf_query_does_not_consume_a_model_query_slot(document_app):
    _web,app,identifier=document_app
    web=make_wsgi_app(app,max_concurrent_queries=1)
    entered,release=threading.Event(),threading.Event()
    def model_query(*args,**kwargs):
        entered.set();assert release.wait(5)
        return {'ok':True,'answer':{'answer':'Admission fixture','citations':[]}}
    app.query=model_query
    pending=threading.Thread(target=lambda:call(web,'/api/query','POST',{
        'question':'Explain enrollment','doc_ids':[identifier]}))
    pending.start();assert entered.wait(3)
    try:
        info=call(web,'/api/query','POST',{'question':'How many pages are in this PDF?','doc_ids':[identifier]})
        assert info['status']==200,'A local PDF fact must remain available while inference is busy'
        assert info['body']['document_info']['documents'][0]['page_count']==3
        for question in ('Explain enrollment','How many pages and explain enrollment?'):
            assert call(web,'/api/query','POST',{'question':question,'doc_ids':[identifier]})['status']==429
        assert call(web,'/api/query','POST',{'question':'How many pages?','doc_ids':[identifier]},scope=[])['status']==404
    finally:
        release.set();pending.join(3)


def fixture_registry(tmp_path):
    path=tmp_path/'registry.json'
    path.write_text(json.dumps({'doc':{'doc_id':'doc','source_path':'source.pdf','page_count':3,
        'metadata':{'program':'A'},'status':'succeeded','chunks':[{'content':'large text'}]*2000,'tables':[]}}),encoding='utf-8')
    return path,DocumentRegistry(path)


def test_metadata_reads_avoid_reparsing_unchanged_document_content(tmp_path,monkeypatch):
    _path,registry=fixture_registry(tmp_path)
    calls=[];original=registry._load
    def load():calls.append(1);return original()
    monkeypatch.setattr(registry,'_load',load)
    first=registry.metadata_list()
    for _ in range(20):assert registry.metadata_get('doc')['page_count']==3
    assert len(calls)<=1 and 'chunks' not in first[0] and 'tables' not in first[0]
    first[0]['metadata']['program']='mutated caller'
    assert registry.metadata_get('doc')['metadata']['program']=='A'


def test_metadata_cache_observes_same_size_atomic_replace_and_removal(tmp_path):
    path,registry=fixture_registry(tmp_path)
    assert registry.metadata_get('doc')['page_count']==3
    original_stat=path.stat();updated=path.read_text(encoding='utf-8').replace('"page_count": 3','"page_count": 7')
    replacement=tmp_path/'replacement.json';replacement.write_text(updated,encoding='utf-8')
    os.utime(replacement,ns=(original_stat.st_atime_ns,original_stat.st_mtime_ns))
    assert replacement.stat().st_size==original_stat.st_size
    os.replace(replacement,path)
    assert registry.metadata_get('doc')['page_count']==7
    other=DocumentRegistry(path);other.remove('doc')
    assert registry.metadata_get('doc') is None and registry.metadata_list()==[]


def test_corrupt_registry_never_falls_back_to_a_cached_ready_record(tmp_path):
    path,registry=fixture_registry(tmp_path)
    assert registry.metadata_get('doc')['status']=='succeeded'
    path.write_text('{invalid registry',encoding='utf-8')
    with pytest.raises(json.JSONDecodeError):registry.metadata_get('doc')


def test_selected_pdf_fact_does_not_audit_an_unselected_unavailable_source(document_app, monkeypatch):
    from pathlib import Path
    from campusai.schemas import Document
    from campusai.web_documents import WebDocuments, WebError
    web, app, identifier = document_app
    other = 'f' * 64
    registry = DocumentRegistry(Path(app.ingestion_defaults['store_dir'])/'registry.json')
    registry.add(Document(other, 'not-selected.pdf', 1, status='review_required'))
    original = WebDocuments.public_document
    inspected = []
    def inspect(self, record, **kwargs):
        inspected.append(record['doc_id'])
        if record['doc_id'] == other:
            raise WebError('source_unavailable', 503)
        return original(self, record, **kwargs)
    monkeypatch.setattr(WebDocuments, 'public_document', inspect)
    result = call(web, '/api/query', 'POST', {'question': 'How many pages?', 'doc_ids': [identifier]})
    assert result['status'] == 200
    assert result['body']['document_info']['documents'][0]['doc_id'] == identifier
    assert inspected == [identifier]


def test_metadata_selection_returns_only_requested_records_and_remains_isolated(tmp_path):
    path, registry = fixture_registry(tmp_path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['other'] = {**data['doc'], 'doc_id': 'other'}
    path.write_text(json.dumps(data), encoding='utf-8')
    selected = registry.metadata_list(doc_ids=['doc'])
    assert [row['doc_id'] for row in selected] == ['doc']
    selected[0]['metadata']['program'] = 'caller mutation'
    assert registry.metadata_get('doc')['metadata']['program'] == 'A'
    assert registry.metadata_list(doc_ids=[]) == []


def test_job_history_reuses_validation_only_within_the_response(document_app, monkeypatch):
    import campusai.web_documents as module
    _web, app, identifier = document_app
    documents = module.WebDocuments(app)
    jobs = app.jobs_snapshot()['jobs']
    source = jobs[0]['source_path']
    rows = [{**jobs[0], 'job_id': str(i)} for i in range(20)]
    calls = []
    original = module.contained
    def validate(root, path):
        if str(path) == source: calls.append(1)
        return original(root, path)
    monkeypatch.setattr(module, 'contained', validate)
    assert len(documents.jobs({}, job_rows=rows)) == 20 and len(calls) == 1
    assert documents.jobs({'campusai.authorized_doc_ids': []}, job_rows=rows) == []
    assert len(calls) == 2
    def redirected(*args): raise module.WebError('not_found', 404)
    monkeypatch.setattr(module, 'contained', redirected)
    with pytest.raises(module.WebError): documents.public_job(rows[0], {})
