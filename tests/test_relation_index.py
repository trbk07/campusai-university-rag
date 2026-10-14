"""Synthetic mechanics only; real-source quality is evaluated separately."""
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from campusai.rag.relation_index import RelationIndex, RelationUnavailable


def source(root, doc='alpha', rows=None, *, program='Program A'):
    rows = rows or [['CS101','Foundations','3',''], ['CS201','Systems','4','CS101'], ['CS301','Advanced','2','CS201']]
    base = root / doc
    base.mkdir(parents=True, exist_ok=True)
    item = dict(chunk_id=doc+'_p1_t1',doc_id=doc,page=1,content_type='table',
        content=json.dumps(dict(headers=['Course code','Course name','Credits','Prerequisite code'],rows=rows)),
        metadata=dict(source_hash=hashlib.sha256(doc.encode()).hexdigest(),source_name=doc+'.pdf',
                      table_id=doc+'_p1_t1',page_range=[1,1],program=program,language='en'))
    (base/'bm25.json').write_text(json.dumps(dict(items=[item])),encoding='utf-8')
    return item


def test_real_sqlite_edges_are_source_owned_and_directional(tmp_path):
    source(tmp_path)
    store=RelationIndex(tmp_path);first=store.rebuild(['alpha'])
    assert first['counts']['alpha']==dict(nodes=3,edges=2,conflicts=0,unsupported=0)
    assert store.path.stat().st_size < 1024**2
    second=store.rebuild(['alpha'])
    assert not second['rebuilt'] and first['db_sha256']==second['db_sha256']
    forward=store.lookup('alpha','CS301',kind='chain2')
    assert forward['trace']['problem'] is None
    assert [(a.code,b.code) for a,b in forward['edges']]==[('CS301','CS201'),('CS201','CS101')]
    assert forward['final'].code=='CS101' and forward['final'].credits==3
    assert forward['trace']['adjacency_lookups']==2
    assert forward['trace']['nodes_visited']==3 and forward['trace']['edges_visited']==2
    inverse=store.lookup('alpha','CS101',kind='inverse')
    assert [(a.code,b.code) for a,b in inverse['edges']]==[('CS201','CS101')]
    assert store.lookup('alpha','CS101')['trace']['problem']=='direct_edge_not_established'


def test_scope_is_separate_even_for_identical_codes_and_restart(tmp_path):
    source(tmp_path,'alpha')
    source(tmp_path,'beta',[['CS101','Foundations','9',''],['CS201','Systems','7','CS101']],program='Program B')
    store=RelationIndex(tmp_path);store.rebuild(['alpha','beta'])
    restarted=RelationIndex(tmp_path)
    assert restarted.lookup('beta','CS201')['final'].credits==9
    assert restarted.lookup('alpha','CS201')['final'].credits==3
    assert restarted.lookup('missing','CS201')['trace']['problem']
    with pytest.raises(ValueError):store.rebuild(['../outside'])


def test_code_spacing_dedup_and_conflicting_values_fail_closed(tmp_path):
    source(tmp_path,rows=[['CS 101','Foundations','3',''],['CS201','Systems','4','CS 101'],['CS201','Systems','4','CS 101']])
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    assert store.lookup('alpha','CS 201')['final'].code=='CS101'
    source(tmp_path,rows=[['CS101','Foundations','3',''],['CS101','Foundations','9',''],['CS201','Systems','4','CS101']])
    assert store.lookup('alpha','CS201')['trace']['problem']=='relation_source_stale'
    report=store.rebuild(['alpha'])
    assert report['counts']['alpha']['conflicts']==1 and report['counts']['alpha']['edges']==0
    assert store.lookup('alpha','CS201')['trace']['problem']=='direct_edge_not_established'


@pytest.mark.parametrize('cell',['CS101 CS102','CS101 or CS102','unresolved reference'])
def test_unsupported_cells_never_become_unique_edges_or_complete_inverse(tmp_path,cell):
    source(tmp_path,rows=[['CS101','First','3',''],['CS102','Second','4',''],['CS201','Systems','4',cell]])
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    assert store.lookup('alpha','CS201')['trace']['problem']=='direct_edge_not_established'
    assert store.lookup('alpha','CS101',kind='inverse')['trace']['problem']=='inverse_relation_incomplete'


def test_cycle_and_fanout_are_stopped_without_unbounded_materialization(tmp_path):
    source(tmp_path,rows=[['CS101','First','3','CS201'],['CS201','Second','4','CS101']])
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    cycle=store.lookup('alpha','CS101',kind='chain2')
    assert cycle['trace']['problem']=='relation_cycle' and cycle['trace']['adjacency_lookups']==2
    source(tmp_path,rows=[['CS101','First','3','']]+[[f'CS{i}','Child','4','CS101'] for i in range(200,240)])
    store.rebuild(['alpha']);wide=store.lookup('alpha','CS101',kind='inverse')
    assert wide['trace']['problem']=='relation_fanout_budget_exceeded'
    assert wide['trace']['nodes_visited']==1 and wide['trace']['edges_visited']==0


def test_filters_unknown_sources_and_deleted_sources_never_broaden_scope(tmp_path):
    source(tmp_path)
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    assert not store.lookup('alpha','CS201',filters={'program':'program a'})['trace']['problem']
    assert store.lookup('alpha','CS201',filters={'program':'Other'})['trace']['problem']=='missing_or_filtered_relation_node'
    assert store.lookup('alpha','CS201',filters={'not_a_filter':'x'})['trace']['problem']
    (tmp_path/'alpha/bm25.json').unlink()
    assert store.lookup('alpha','CS201')['trace']['problem']=='relation_source_stale'
    report=store.rebuild([]);assert report['counts']=={}


def test_database_corruption_and_source_mutation_require_rebuild(tmp_path):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    with sqlite3.connect(store.path) as db:db.execute("DELETE FROM edges")
    db.close()
    db.close()
    assert store.lookup('alpha','CS201')['trace']['problem']=='relation_index_corrupt'
    store.rebuild(['alpha'])
    assert not store.lookup('alpha','CS201')['trace']['problem']
    source(tmp_path,rows=[['CS101','Foundations','8',''],['CS201','Systems','4','CS101']])
    assert store.lookup('alpha','CS201')['trace']['problem']=='relation_source_stale'
    store.rebuild(['alpha'])
    assert store.lookup('alpha','CS201')['final'].credits==8


def test_build_interruption_retains_previous_ready_generation_and_cleans_temp(tmp_path,monkeypatch):
    source(tmp_path);store=RelationIndex(tmp_path);original=store.rebuild(['alpha'])
    source(tmp_path,rows=[['CS101','Foundations','8',''],['CS201','Systems','4','CS101']])
    import campusai.rag.relation_index as module
    replace=module.os.replace
    def interrupted(src,dst):raise OSError('interrupted publication')
    monkeypatch.setattr(module.os,'replace',interrupted)
    with pytest.raises(OSError,match='interrupted'):store.rebuild(['alpha'])
    assert hashlib.sha256(store.path.read_bytes()).hexdigest()==original['db_sha256']
    assert not list(tmp_path.glob('.relation-build-*'))
    assert store.lookup('alpha','CS201')['trace']['problem']=='relation_source_stale'
    monkeypatch.setattr(module.os,'replace',replace)
    store.rebuild(['alpha'])
    assert store.lookup('alpha','CS201')['final'].credits==8


def test_standalone_exact_statement_proves_edge_but_endpoint_overlap_and_negation_do_not(tmp_path):
    item=source(tmp_path,rows=[['CS101','Foundations','3',''],['CS201','Systems','4','']])
    statement=dict(item,chunk_id='alpha_p2_s1',page=2,content_type='text',
        content='Course CS101 is a direct prerequisite of CS201.',
        metadata={**item['metadata'],'table_id':None,'page_range':[2,2]})
    path=tmp_path/'alpha/bm25.json'
    path.write_text(json.dumps(dict(items=[item,statement])),encoding='utf-8')
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    found=store.lookup('alpha','CS201')
    assert found['trace']['problem'] is None
    assert found['edge_evidence'][('CS201','CS101')]['result'].page==2
    assert found['trace']['candidate_chunks']==2
    for text in ['CS101 and CS201 are listed here.','It is not true that Course CS101 is a direct prerequisite of CS201.']:
        statement['content']=text
        path.write_text(json.dumps(dict(items=[item,statement])),encoding='utf-8')
        store.rebuild(['alpha'])
        assert store.lookup('alpha','CS201')['trace']['problem']=='direct_edge_not_established'


def test_relation_filters_apply_to_both_endpoints_and_statement_before_traversal(tmp_path):
    item=source(tmp_path,rows=[['CS101','Foundations','3','']])
    second={**item,'chunk_id':'alpha_p2_t1','page':2,
        'content':json.dumps(dict(headers=['Course code','Course name','Credits','Prerequisite code'],rows=[['CS201','Systems','4','CS101']])),
        'metadata':{**item['metadata'],'language':'vi','page_range':[2,2]}}
    path=tmp_path/'alpha/bm25.json';path.write_text(json.dumps(dict(items=[item,second])),encoding='utf-8')
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    outcome=store.lookup('alpha','CS101',kind='inverse',filters={'language':'en'})
    assert outcome['trace']['problem']=='direct_edge_not_established'
    assert outcome['trace']['nodes_visited']==1 and outcome['trace']['edges_visited']==0


def test_source_changed_during_proof_read_cannot_return_a_stale_complete_enumeration(tmp_path,monkeypatch):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    original=store._source;changed=[False]
    def racing(doc,trace=None):
        result=original(doc,trace)
        if trace is not None and not changed[0]:
            changed[0]=True
            source(tmp_path,rows=[['CS101','Foundations','3',''],['CS201','Systems','4','CS101'],['CS401','Extra','5','CS101']])
        return result
    monkeypatch.setattr(store,'_source',racing)
    outcome=store.lookup('alpha','CS101',kind='inverse')
    assert outcome['trace']['problem']=='relation_source_stale'
    assert not outcome['edges'] and not outcome['premises']


def test_unrelated_conflict_with_blank_variant_does_not_invent_global_uncertainty(tmp_path):
    source(tmp_path,rows=[['CS101','First','3',''],['CS201','Second','4','CS101'],
                         ['CS301','Third','4',''],['CS401','Fourth','2','CS301'],['CS401','Fourth','2','']])
    store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    found=store.lookup('alpha','CS101',kind='inverse')
    assert found['trace']['problem'] is None
    assert [(a.code,b.code) for a,b in found['edges']]==[('CS201','CS101')]
    assert store.lookup('alpha','CS301',kind='inverse')['trace']['problem']=='inverse_relation_incomplete'


def test_interrupted_manifest_publication_never_serves_a_partial_generation(tmp_path,monkeypatch):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    source(tmp_path,rows=[['CS101','Foundations','8',''],['CS201','Systems','4','CS101']])
    import campusai.rag.relation_index as module
    original=module.os.replace
    def interrupt_manifest(src,dst):
        if Path(dst)==store.manifest_path:raise OSError('manifest publication interrupted')
        return original(src,dst)
    monkeypatch.setattr(module.os,'replace',interrupt_manifest)
    with pytest.raises(OSError,match='manifest publication'):store.rebuild(['alpha'])
    assert store.lookup('alpha','CS201')['trace']['problem']=='relation_index_corrupt'
    assert not list(tmp_path.glob('.relation-build-*'))
    monkeypatch.setattr(module.os,'replace',original)
    store.rebuild(['alpha'])
    assert store.lookup('alpha','CS201')['final'].credits==8


def test_source_mutation_during_build_cannot_publish_mixed_rows(tmp_path,monkeypatch):
    source(tmp_path);store=RelationIndex(tmp_path);previous=store.rebuild(['alpha'])
    source(tmp_path,rows=[['CS101','Foundations','8',''],['CS201','Systems','4','CS101']])
    original=store._source
    def changed(doc,trace=None):
        result=original(doc,trace)
        source(tmp_path,rows=[['CS101','Foundations','9',''],['CS201','Systems','4','CS101']])
        return result
    monkeypatch.setattr(store,'_source',changed)
    with pytest.raises(RelationUnavailable,match='source_changed_during_relation_build'):store.rebuild(['alpha'])
    assert hashlib.sha256(store.path.read_bytes()).hexdigest()==previous['db_sha256']
    assert not list(tmp_path.glob('.relation-build-*'))
