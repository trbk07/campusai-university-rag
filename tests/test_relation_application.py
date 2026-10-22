"""Real service/cache/grounding mechanics; no synthetic quality numerator."""
from datetime import date
import json

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator,validate_citation
from campusai.rag.service import CampusAIQueryService
from campusai.rag.cache import RAGAnswerCache
from campusai.rag.relation_index import RelationIndex
from campusai.rag.relations import plan_relation
from campusai.retrieval.hybrid import HybridRetriever
from tests.test_relation_index import source


class NoModel:
    model='never-used'
    generation_config={'maxOutputTokens':1024}
    def generate_json(self,*args,**kwargs):raise AssertionError('Unexpected generation')


def service(root,*,enabled=True,cache=None,max_chars=12000,store=None):
    retriever=HybridRetriever(root)
    def no_search(*args,**kwargs):raise AssertionError('Unexpected search or encoder')
    retriever.search=no_search
    return CampusAIQueryService(retriever,GroundedAnswerGenerator(NoModel(),max_context_chars=max_chars),
        cache=cache,default_mode='hybrid',temporal_clock=lambda:date(2026,10,14),
        relation_index=store or RelationIndex(root) if enabled else None)


@pytest.mark.parametrize('question,edges',[
 ('In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have?',1),
 ('In alpha.pdf, which courses list CS101 as a direct prerequisite? List all of them with source evidence.',1),
 ('In alpha.pdf, follow two consecutive direct prerequisite links from CS301. State both links and the credit value of the last course.',2),
 ('In alpha.pdf, follow two consecutive direct prerequisite links from CS301. State both links and the name of the last course.',2),
])
def test_actual_local_composition_uses_grounding_public_schema_and_source_coordinates(tmp_path,question,edges):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    app=service(tmp_path,store=store)
    answer=app.ask(question,doc_ids=['alpha'],language='en')
    assert not answer.abstained,answer.to_dict()
    assert len([c for c in answer.claims if 'prerequisite' in c.text])==edges
    assert all(c.status=='supported' for c in answer.claims)
    public=answer.to_public_dict()
    assert not public['abstained'] and public['schema_version']=='grounding-public-v2'
    assert all(c['doc_id']=='alpha' and c['page']==1 for c in public['citations'])
    for c in answer.citations:
        assert validate_citation(c,next(r for r in app.last_retrieval if r.chunk_id==c.chunk_id),require_quote=True).valid
    trace=app._request_local.relation_trace
    assert trace['adjacency_lookups']<=2 and trace['nodes_visited']<=3 and trace['candidate_chunks']==1
    app.close()


def test_relation_answer_cache_separates_same_version_calibrators(tmp_path):
    from campusai.rag.calibration import IsotonicCalibrator
    source(tmp_path)
    store = RelationIndex(tmp_path)
    store.rebuild(['alpha'])
    app = service(tmp_path, store=store)
    question = 'In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have?'
    try:
        app.answer_generator.calibrator = IsotonicCalibrator((1.0,), (0.2,))
        first = app.ask(question, doc_ids=['alpha'], language='en')
        assert not first.abstained and first.confidence_score == 0.2
        app.answer_generator.calibrator = IsotonicCalibrator((1.0,), (0.9,))
        second = app.ask(question, doc_ids=['alpha'], language='en')
        assert not second.abstained and second.confidence_score == 0.9 and not app.last_cache_hit
        assert app.ask(question, doc_ids=['alpha'], language='en').confidence_score == 0.9
        assert app.last_cache_hit
    finally:
        app.close()


def test_feature_off_keeps_legacy_local_abstention_and_does_not_read_sidecar(tmp_path):
    source(tmp_path)
    app=service(tmp_path,enabled=False)
    answer=app.ask('In alpha.pdf, which courses list CS101 as a direct prerequisite? List all of them with source evidence.',doc_ids=['alpha'])
    assert answer.abstained and app._request_local.relation_trace is None
    app.close()


def test_authorization_empty_scope_unknown_source_and_filters_are_checked_before_traversal(tmp_path):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha']);app=service(tmp_path,store=store)
    question='In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have?'
    with pytest.raises(ValueError,match='authorization'):app.ask(question,doc_ids=['alpha'],authorized_doc_ids=['beta'])
    assert app._request_local.relation_trace is None
    for options in [dict(doc_ids=[]),dict(doc_ids=['alpha'],filters={'program':'Other'})]:
        answer=app.ask(question,**options);assert answer.abstained and not app.last_retrieval
        assert app._request_local.relation_trace['adjacency_lookups']==0
    app.close()


def test_incomplete_hop_cycle_and_truncated_context_never_publish_partial_claims(tmp_path):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha']);app=service(tmp_path,store=store)
    q='In alpha.pdf, follow two consecutive direct prerequisite links from CS201. State both links and the credit value of the last course.'
    answer=app.ask(q,doc_ids=['alpha'],language='en')
    assert answer.abstained and not answer.to_public_dict()['claims']
    app.close()
    source(tmp_path,rows=[['CS101','Long name '+'x'*1400,'3',''],['CS201','Systems','4','CS101']]);store.rebuild(['alpha'])
    app=service(tmp_path,store=store,max_chars=1000)
    answer=app.ask('In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have?',doc_ids=['alpha'])
    assert answer.abstained and not answer.to_public_dict()['citations']
    app.close()


def test_extra_hops_or_conditions_cannot_be_silently_dropped(tmp_path):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha']);app=service(tmp_path,store=store)
    for q in [
        'In alpha.pdf, follow three direct prerequisite links from CS301 and state the credit value of the last course.',
        'In alpha.pdf, follow two consecutive direct prerequisite links from CS301. State both links and the credit value of the last course, and recommend a degree plan.',
        'In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have, and recommend a degree plan?',
    ]:
        answer=app.ask(q,doc_ids=['alpha']);assert answer.abstained
        assert app._request_local.relation_trace['adjacency_lookups']==0
    app.close()


def test_persistent_cache_binds_both_source_generation_and_answer_policy(tmp_path,monkeypatch):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha'])
    cache_path=str(tmp_path/'answers.sqlite3')
    question='In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have?'
    app=service(tmp_path,store=store,cache=RAGAnswerCache(cache_path))
    answer=app.ask(question,doc_ids=['alpha'],language='en');assert not answer.abstained and not app.last_cache_hit
    assert not app.ask(question,doc_ids=['alpha'],language='en').abstained and app.last_cache_hit
    assert not app.last_retrieval and app._request_local.relation_trace['cache_hit']
    app.close()
    app=service(tmp_path,cache=RAGAnswerCache(cache_path))
    assert not app.ask(question,doc_ids=['alpha'],language='en').abstained and app.last_cache_hit
    import campusai.rag.relations as module
    monkeypatch.setattr(module,'answer_policy_fingerprint',lambda:'different-policy')
    assert not app.ask(question,doc_ids=['alpha'],language='en').abstained and not app.last_cache_hit
    source(tmp_path,rows=[['CS101','Foundations','8',''],['CS201','Systems','4','CS101']])
    # A missing/stale sidecar delegates supported direct intent to legacy. Test
    # that it cannot return the old graph cache; rebuild restores local delivery.
    app.relation_index.rebuild(['alpha'])
    changed=app.ask(question,doc_ids=['alpha'],language='en')
    assert not changed.abstained and not app.last_cache_hit and '8 credits' in changed.answer
    app.close()


def test_missing_sidecar_has_only_a_zero_graph_work_bounded_legacy_fallback(tmp_path):
    source(tmp_path);app=service(tmp_path)
    seen=[]
    def search(*args,**kwargs):
        seen.append(kwargs)
        from campusai.retrieval.hybrid import RetrievalResult
        item=json.loads((tmp_path/'alpha/bm25.json').read_text())['items'][0]
        return [RetrievalResult(item['chunk_id'],'alpha',1,item['content'],'table',1,'hybrid',item['metadata'])]
    app.retriever.search=search
    app.answer_generator.llm=None
    answer=app.ask('In alpha.pdf, what is the direct prerequisite of CS201 and how many credits does it have?',doc_ids=['alpha'])
    assert answer.abstained and 0<len(seen)<=2
    assert all(k['top_k']<=20 and k['doc_ids']==['alpha'] for k in seen)
    assert app._request_local.relation_trace['fallback']=='legacy_composition_no_graph_work'
    seen.clear()
    answer=app.ask('In alpha.pdf, follow two consecutive direct prerequisite links from CS301. State both links and the credit value of the last course.',doc_ids=['alpha'])
    assert answer.abstained and not seen
    app.close()


def test_retrieve_uses_identical_graph_evidence_without_generation(tmp_path):
    source(tmp_path);store=RelationIndex(tmp_path);store.rebuild(['alpha']);app=service(tmp_path,store=store)
    result=app.retrieve('In alpha.pdf, follow two consecutive direct prerequisite links from CS301. State both links and the credit value of the last course.',doc_ids=['alpha'])
    assert result and all(r.doc_id=='alpha' for r in result)
    assert app._request_local.relation_trace['edges_visited']==2
    app.close()


@pytest.mark.parametrize('code',['CS201','BIO450','MATH 301'])
def test_same_utterance_prerequisite_subject_anchors_it_without_history(code):
    from campusai.rag.context import resolve_query
    q=f'What is the direct prerequisite of {code} and how many credits does it have?'
    assert not resolve_query(q).needs_clarification
    assert resolve_query(q,requires_context=True).needs_clarification


def test_pronoun_only_or_two_subjects_do_not_gain_an_invented_anchor():
    from campusai.rag.context import resolve_query
    assert resolve_query('What is its prerequisite and how many credits does it have?').needs_clarification
    assert resolve_query('CS301 or the prerequisite of CS201 and how many credits does it have?').needs_clarification


def test_multi_fact_single_chunk_quote_retains_each_original_row_without_cross_row_splicing(tmp_path):
    from campusai.rag.grounding import validate_quote
    item=source(tmp_path,rows=[['CS101','Foundations','3',''],['CS999','Unrelated','7',''],
                             ['CS201','Systems','4','CS101'],['CS301','Advanced','2','CS201']])
    store=RelationIndex(tmp_path);store.rebuild(['alpha']);app=service(tmp_path,store=store)
    answer=app.ask('In alpha.pdf, follow two consecutive direct prerequisite links from CS301. State both links and the credit value of the last course.',doc_ids=['alpha'],language='en')
    assert not answer.abstained
    quoted=json.loads(answer.citations[0].quote)
    original=json.loads(item['content'])['rows']
    assert quoted==[original[0],original[2],original[3]] and validate_quote(answer.citations[0].quote,item['content'])
    for wrong in [quoted[:2]+[['CS101','Foundations','9','']],
                  [['CS101','Advanced','3','CS201'],quoted[1]],
                  {'rows':quoted},[quoted[0],'invented row']]:
        assert not validate_quote(json.dumps(wrong),item['content'])
    app.close()
