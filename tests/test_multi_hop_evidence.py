"""Synthetic safety/budget controls; not real-source model quality."""
from dataclasses import replace
import json

import pytest

from campusai.rag.claims import align_claims, extract_claims
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.multi_hop import MultiHopRequest, SourceRole
from campusai.rag.multi_hop_evidence import (find_premise, name_matches,
    prerequisite_claim_support, retrieve_composition, scoped_calculation_support,
    deterministic_direct_prerequisite_code)
from campusai.rag.multi_hop_evidence import name_code_claim_support
from campusai.retrieval.hybrid import RetrievalResult


HEADERS=['Course code','Course name','Credits','Prerequisite']


def row(doc, code, credits, prerequisite='', name='Example', cid=None):
    return RetrievalResult(cid or doc+'-'+code,doc,1,
        json.dumps(dict(headers=HEADERS,rows=[[code,name,str(credits),prerequisite]]),ensure_ascii=False),
        'table',1.0,'synthetic',dict(source_name=doc+'.pdf',source_hash=doc,table_id=cid or doc+'-'+code))


class Search:
    def __init__(self, returns):self.returns=iter(returns);self.calls=[]
    def __call__(self,*args,**kwargs):
        self.calls.append((args,kwargs));return next(self.returns)


class Model:
    model='synthetic-control'
    def __init__(self,payload=None):self.payload=payload;self.calls=0
    def generate_json(self,*args,**kwargs):
        self.calls+=1
        assert self.payload is not None, 'unnecessary model generation'
        return self.payload


def arithmetic(kind='sum', codes=('CS201','CS202')):
    return MultiHopRequest(kind,tuple(SourceRole(doc,doc+'.pdf',code) for doc,code in zip(('a','b'),codes)))


@pytest.mark.parametrize('kind,expected',[('sum','7.'),('difference','3 - 4 = -1 credits.')])
def test_source_qualified_arithmetic_is_local_and_preserves_negative_sign(kind,expected):
    plan=arithmetic(kind);search=Search([[row('a','CS201',3),row('b','CS202',4)]])
    results,trace=retrieve_composition(plan,search,filters=None,mode='hybrid',top_k=5)
    model=Model();answer=GroundedAnswerGenerator(model).answer('CS201 and CS202 credits?',results,'en',multi_hop_context=trace)
    assert not answer.abstained and answer.answer.endswith(expected) and model.calls==0
    assert {c.doc_id for c in answer.citations}=={'a','b'}
    assert trace['search_calls']==1 and trace['returned_candidates']==2
    assert all(c.status=='supported' for c in answer.claims)


def test_same_code_different_scopes_is_two_explicit_operands_not_a_global_conflict():
    plan=arithmetic(codes=('CS201','CS201'))
    results,trace=retrieve_composition(plan,Search([[row('a','CS201',3),row('b','CS201',4)]]),
        filters=None,mode='hybrid',top_k=5)
    answer=GroundedAnswerGenerator(Model()).answer('Total credits for CS201?',results,'en',multi_hop_context=trace)
    assert not answer.abstained and answer.answer.endswith('7.')
    records=EvidenceRegistry(results).values()
    assert scoped_calculation_support(answer.answer,records)[0]
    assert not scoped_calculation_support(answer.answer.replace('are 7.','are 6.'),records)[0]
    assert not scoped_calculation_support(answer.answer,records[:1])[0]


def test_missing_side_never_borrows_identical_code_or_fetches_a_third_source():
    plan=arithmetic(codes=('CS201','CS201'))
    search=Search([[row('a','CS201',3),row('outside','CS201',3)]])
    results,trace=retrieve_composition(plan,search,filters={'program':'X'},mode='hybrid',top_k=5)
    assert not results and trace['problem']=='missing_or_conflicting_operand'
    assert len(search.calls)==1 and search.calls[0][1]['doc_ids']==['a','b']


def test_parent_row_proves_bridge_before_one_dependent_source_scoped_search():
    plan=MultiHopRequest('prerequisite_lookup',(SourceRole('a','a.pdf'),),target_code='CS201')
    search=Search([[row('a','CS201',4,'CS101')],[row('a','CS101',3)]])
    results,trace=retrieve_composition(plan,search,filters=None,mode='hybrid',top_k=5)
    assert trace['problem'] is None and len(results)==2
    assert trace['edge']['bridge_code']=='CS101'
    assert search.calls[1][0]==('CS101',) and search.calls[1][1]['doc_ids']==['a']
    assert len(search.calls)==2 and all(call[1]['top_k']==20 for call in search.calls)


def test_direct_prerequisite_code_lookup_uses_the_reviewable_source_row_without_model():
    evidence = row('a', 'PEC1008', 2, 'PHI1006')
    model = Model()
    answer = GroundedAnswerGenerator(model).answer(
        'Use only alpha.pdf. Which prerequisite code is listed for PEC1008?',
        [evidence], 'en')
    assert not answer.abstained
    assert answer.answer == 'Course PHI1006 is a direct prerequisite of PEC1008.'
    assert answer.citations[0].chunk_id == evidence.chunk_id
    assert json.loads(answer.citations[0].quote) == ['PEC1008', 'Example', '2', 'PHI1006']
    assert model.calls == 0


@pytest.mark.parametrize('question,results', [
    ('Which prerequisite code is listed for PEC1008 and PEC2008?', [row('a','PEC1008',2,'PHI1006')]),
    ('Which courses list PEC1008 as a prerequisite?', [row('a','PEC1008',2,'PHI1006')]),
    ('How many credits does the prerequisite of PEC1008 have?', [row('a','PEC1008',2,'PHI1006')]),
    ('Which prerequisite code is listed for PEC1008?', [row('a','PEC1008',2,'PHI1006'), row('b','PEC1008',2,'PHI2006')]),
])
def test_direct_prerequisite_code_lookup_fails_closed_for_scope_or_conflict(question, results):
    assert deterministic_direct_prerequisite_code(question, results, 'en') is None


@pytest.mark.parametrize('prereq',['','CS101 or CS102','CS101 CS102','unknown'])
def test_missing_or_non_unique_bridge_never_runs_second_search(prereq):
    plan=MultiHopRequest('prerequisite_lookup',(SourceRole('a','a.pdf'),),target_code='CS201')
    search=Search([[row('a','CS201',4,prereq)]])
    results,trace=retrieve_composition(plan,search,filters=None,mode='hybrid',top_k=5)
    assert not results and trace['problem']=='direct_edge_not_established' and len(search.calls)==1


def test_endpoint_cooccurrence_does_not_prove_a_prerequisite_edge():
    evidence=[row('a','CS101',3),row('a','CS201',4)]
    text='Course CS101 is a prerequisite of course CS201.'
    registry=EvidenceRegistry(evidence)
    claims=extract_claims(text,[dict(claim_id='edge',text=text,citation_ids=[r.chunk_id for r in evidence])])
    assert align_claims(claims,registry,{'edge':claims[0].citation_ids})[0].status=='unsupported'
    assert prerequisite_claim_support(text,[row('a','CS201',4,'CS101')])[0]
    assert not prerequisite_claim_support('Course CS201 is a prerequisite of course CS101.',
        [row('a','CS201',4,'CS101')])[0]


def test_exact_direct_source_statement_still_proves_edge():
    text='Course CS101 is a prerequisite of course CS201.'
    evidence=replace(row('a','CS201',4),content=text,content_type='text')
    assert prerequisite_claim_support(text,[evidence])[0]


@pytest.mark.parametrize('prefix',['It is not true that ', 'Rejected assertion: '])
def test_quoted_or_negated_endpoint_statement_does_not_certify_relation(prefix):
    text='Course CS101 is a prerequisite of course CS201.'
    evidence=replace(row('a','CS201',4),content=prefix+text,content_type='text')
    assert not prerequisite_claim_support(text,[evidence])[0]


def test_conflicting_duplicate_rows_fail_closed_but_exact_duplicates_dedup():
    original=row('a','CS201',3)
    assert find_premise([original,replace(original,chunk_id='duplicate')],'a',code='CS201')
    assert find_premise([original,row('a','CS201',4,cid='conflict')],'a',code='CS201') is None


def test_bilingual_name_and_footnote_are_explicit_segments_not_fuzzy_substrings():
    assert name_matches('Công nghệ chuỗi khối','Công nghệ chuỗi khối\nBlockchain Technology')
    assert name_matches('Luận văn','Luận văn*\nThesis')
    assert not name_matches('Điện tử','Điện tử y sinh\nBioelectronics')
    assert not name_matches('Công nghệ','Công nghệ\nchuỗi khối\nBlockchain Technology')


def test_second_source_lookup_cannot_reuse_first_source_credit():
    plan=MultiHopRequest('name_code_lookup',(SourceRole('a','a.pdf'),SourceRole('b','b.pdf')),lookup_name='Example')
    search=Search([[row('a','CS201',3)],[row('a','CS201',3)]])
    results,trace=retrieve_composition(plan,search,filters=None,mode='hybrid',top_k=5)
    assert not results and trace['problem']=='missing_or_conflicting_second_hop'
    assert search.calls[1][1]['doc_ids']==['b']


def test_context_truncation_blocks_generation_even_with_hidden_full_premises():
    huge=row('a','CS201',3,name='X'*2000)
    results,trace=retrieve_composition(arithmetic(),Search([[huge,row('b','CS202',4)]]),
        filters=None,mode='hybrid',top_k=5)
    model=Model()
    answer=GroundedAnswerGenerator(model,max_context_chars=1000).answer('CS201 and CS202 credits?',results,'en',multi_hop_context=trace)
    assert answer.abstained and answer.reason=='context_budget_exceeded' and model.calls==0


def test_supported_one_side_is_not_a_complete_comparison():
    plan=arithmetic('compare',('CS201','CS201'))
    results,trace=retrieve_composition(plan,Search([[row('a','CS201',3),row('b','CS201',4)]]),
        filters=None,mode='hybrid',top_k=5)
    cid=results[0].chunk_id
    payload=dict(answer='Course CS201 has 3 credits.',confidence='high',abstained=False,
        claims=[dict(claim_id='one',text='Course CS201 has 3 credits.',citation_ids=[cid])],
        citations=[dict(chunk_id=cid,page=1,quote=json.dumps(['CS201','Example','3','']))])
    model=Model(payload)
    answer=GroundedAnswerGenerator(model).answer('Compare CS201 credits?',results,'en',multi_hop_context=trace)
    assert answer.abstained and answer.reason=='unsupported_claim' and model.calls==1


def test_join_requires_edge_claim_and_child_credit_with_their_own_citations():
    plan=MultiHopRequest('prerequisite_lookup',(SourceRole('a','a.pdf'),),target_code='CS201')
    results,trace=retrieve_composition(plan,Search([[row('a','CS201',4,'CS101'),row('a','CS101',3)]]),
        filters=None,mode='hybrid',top_k=5)
    edge='Course CS101 is a prerequisite of course CS201.'
    credit='Course CS101 has 3 credits.'
    payload=dict(answer=edge+' '+credit,confidence='high',abstained=False,
        claims=[dict(claim_id='edge',text=edge,citation_ids=['a-CS201']),
                dict(claim_id='credit',text=credit,citation_ids=['a-CS101'])],
        citations=[dict(chunk_id=r.chunk_id,page=1,quote=json.dumps(json.loads(r.content)['rows'][0])) for r in results])
    answer=GroundedAnswerGenerator(Model(payload)).answer('CS201 prerequisite credits?',results,'en',multi_hop_context=trace)
    assert not answer.abstained and len(answer.citations)==2
    # Correct child credit without proving the requested edge is incomplete.
    payload['claims']=payload['claims'][1:];payload['answer']=credit
    answer=GroundedAnswerGenerator(Model(payload)).answer('CS201 prerequisite credits?',results,'en',multi_hop_context=trace)
    assert answer.abstained and answer.reason=='unsupported_claim'


def test_cross_source_name_code_lookup_proves_both_identifier_edge_and_child_credit():
    plan=MultiHopRequest('name_code_lookup',(SourceRole('a','a.pdf'),SourceRole('b','b.pdf')),lookup_name='Blockchain Technology')
    results,trace=retrieve_composition(plan,Search([[row('a','CS201',3,name='Blockchain Technology')],
        [row('b','CS201',4,name='Blockchain Technology')]]),filters=None,mode='hybrid',top_k=5)
    edge='Blockchain Technology has course code CS201.';credit='Course CS201 has 4 credits.'
    payload=dict(answer=edge+' '+credit,confidence='high',abstained=False,
        claims=[dict(claim_id='edge',text=edge,citation_ids=['a-CS201']),
                dict(claim_id='credit',text=credit,citation_ids=['b-CS201'])],
        citations=[dict(chunk_id=r.chunk_id,page=1,quote=json.dumps(json.loads(r.content)['rows'][0])) for r in results])
    answer=GroundedAnswerGenerator(Model(payload)).answer('Blockchain Technology code and credits in b.pdf?',
        results,'en',multi_hop_context=trace)
    assert not answer.abstained and {c.doc_id for c in answer.citations}=={'a','b'}


def test_faulty_retriever_cannot_hide_excess_candidates_in_trace():
    results,trace=retrieve_composition(arithmetic(),Search([[row('a','CS201',3)]*21]),filters=None,mode='hybrid',top_k=5)
    assert not results and trace['problem']=='retrieval_candidate_budget_exceeded'
    assert trace['returned_candidates']==21


def test_real_service_invalidates_both_caches_when_either_source_changes(tmp_path):
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    def save(doc,n):
        r=row(doc,'CS201',n)
        BM25Index([dict(chunk_id=r.chunk_id,doc_id=doc,page=1,content=r.content,
            content_type='table',metadata=r.metadata)],'en').save(tmp_path/doc/'bm25.json')
    save('a',3);save('b',4)
    model=Model()
    service=CampusAIQueryService(HybridRetriever(tmp_path),GroundedAnswerGenerator(model),default_mode='bm25')
    try:
        question='Total credits for CS201 in a.pdf and CS201 in b.pdf?'
        first=service.ask(question,doc_ids=['a','b'],language='en')
        assert not first.abstained and first.answer.endswith('7.') and not service.last_cache_hit
        assert service.ask(question,doc_ids=['a','b'],language='en').cache_hit
        save('b',5)
        changed=service.ask(question,doc_ids=['a','b'],language='en')
        assert not changed.abstained and changed.answer.endswith('8.') and not service.last_cache_hit
        difference=service.ask('Credits for CS201 in b.pdf minus CS201 in a.pdf?',doc_ids=['a','b'],language='en')
        assert not difference.abstained and '5 - 3 = 2' in difference.answer
        # Changing authorized scope cannot reuse the earlier two-source answer.
        with pytest.raises(ValueError,match='authorization'):
            service.ask(question,doc_ids=['a','b'],authorized_doc_ids=['a'],language='en')
        missing=service.ask(question,doc_ids=['a'],authorized_doc_ids=['a'],language='en')
        assert missing.abstained and service._request_local.multi_hop_trace['search_calls']==0
        assert model.calls==0
    finally:service.close()


def test_complete_native_comparison_preserves_actual_existing_model_prompt(tmp_path):
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    records=[row('a','CS201',3),row('b','CS201',4)]
    for r in records:
        BM25Index([dict(chunk_id=r.chunk_id,doc_id=r.doc_id,page=1,content=r.content,
            content_type='table',metadata=r.metadata)],'en').save(tmp_path/r.doc_id/'bm25.json')
    payload=dict(answer='a.pdf: Course CS201 has 3 credits. b.pdf: Course CS201 has 4 credits.',
        confidence='high',abstained=False,
        claims=[dict(claim_id=str(i),text=f'Course CS201 has {n} credits.',citation_ids=[r.chunk_id])
                for i,(r,n) in enumerate(zip(records,(3,4)))],
        citations=[dict(chunk_id=r.chunk_id,page=1,quote=json.dumps(json.loads(r.content)['rows'][0])) for r in records])
    model=Model(payload);generate=model.generate_json;prompts=[]
    def capture(prompt,**kwargs):prompts.append(prompt);return generate(prompt,**kwargs)
    model.generate_json=capture
    generator=GroundedAnswerGenerator(model)
    service=CampusAIQueryService(HybridRetriever(tmp_path),generator,default_mode='bm25')
    try:
        question='Compare CS201 credits in the selected documents.'
        answer=service.ask(question,doc_ids=['a','b'],language='en')
        assert not answer.abstained and model.calls==1
        assert prompts==[generator.prompt(question,service.last_retrieval,'en')]
        assert service._request_local.multi_hop_trace['preserve_existing_prompt']
    finally:service.close()


@pytest.mark.parametrize('text',[
    'Môn Công nghệ dữ liệu có mã CS201.',
    'Môn Công nghệ dữ liệu có mã CS 201.',
    'Course Công nghệ dữ liệu has course code CS201.',
])
def test_named_code_relation_uses_own_row_and_canonical_code_spacing(text):
    result=row('a','CS 201',3,name='Công nghệ dữ liệu\nData Technology')
    assert name_code_claim_support(text,[result])==(True,(result.chunk_id,))
    claims=extract_claims(text,[dict(claim_id='name',text=text,citation_ids=[result.chunk_id])])
    aligned=align_claims(claims,EvidenceRegistry([result]),{'name':claims[0].citation_ids})
    assert aligned[0].status=='supported' and aligned[0].support_score==1


def test_named_code_relation_preserves_footnote_and_rejects_wrong_or_ambiguous_identity():
    result=row('a','CS 201',3,'CS101',name='Luận văn*\nThesis')
    assert name_code_claim_support('Môn Luận văn có mã CS201.',[result])[0]
    assert not name_code_claim_support('Môn Luận văn có mã CS101.',[result])[0]
    assert not name_code_claim_support('Môn Luận có mã CS201.',[result])[0]
    other=row('a','CS202',3,name='Luận văn*\nThesis',cid='ambiguous')
    # Separate chunks with two identifiers for the same name remain conflicting.
    assert not name_code_claim_support('Môn Luận văn có mã CS201.',[result,other])[0]


def test_named_code_relation_does_not_take_number_from_hours_or_another_source():
    result=row('a','CS 201',3,name='Data Technology')
    assert not name_code_claim_support('Course Data Technology has code CS203.',[result])[0]
    assert name_code_claim_support('Course Other Name has code CS201.',[result])==(False,())
    assert name_code_claim_support('Course Data Technology has 3 credits.',[result]) is None
