"""Compact references preserve source identity, text, validation and isolation."""
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest

from campusai.rag.citation_handles import evidence_handles, reference_context, restore_citations
from campusai.rag.grounding import GroundedAnswerGenerator, build_context
from campusai.rag.service import CampusAIQueryService
from tests.test_basic_rag import FakeLLM, FakeRetriever, evidence
from tests.test_source_citations import payload


def generator(model, **kwargs):
    return GroundedAnswerGenerator(model, source_citations=True, compact_citation_ids=True, **kwargs)


@pytest.mark.parametrize('balanced', [False, True])
def test_only_typed_evidence_ids_change_not_source_or_question_text(balanced):
    identifier='a'*64+'_p3_s1_c1'
    text=f'MATH101 is required. The source checksum is {identifier}.'
    row=evidence(identifier,content=text)
    model=generator(None,balanced_context=balanced)
    prompt=model.prompt(f'Explain checksum {identifier}.',[row],'en')
    assert 'chunk_id=ev1\n' in prompt
    assert text in prompt and f'QUESTION:\nExplain checksum {identifier}.' in prompt
    assert 'doc_id=doc-1\npage=3' in prompt
    assert row.chunk_id==identifier and row.content==text
    assert len(build_context([row],evidence_ids=evidence_handles([row]))) < len(build_context([row]))


def test_auxiliary_reference_mapping_does_not_rewrite_source_values():
    original={'chunk_ids':['real'], 'text':'real','cells':['real'], 'doc_id':'real',
              'nested':{'parent_chunk_id':'real','note':'real'}}
    before=copy.deepcopy(original)
    mapped=reference_context(original,{'real':'ev1'})
    assert mapped=={**before,'chunk_ids':['ev1'],'nested':{'parent_chunk_id':'ev1','note':'real'}}
    assert original==before


def test_alias_schema_is_scoped_to_all_actual_retrieval_not_expected_labels():
    rows=[evidence('actual-source'),evidence('unrelated-source'),evidence('actual-source')]
    schema=generator(None).response_schema(rows)
    assert schema['properties']['citations']['items']['properties']['chunk_id']['enum']==['ev1','ev2']
    assert schema['properties']['claims']['items']['properties']['citation_ids']['items']['enum']==['ev1','ev2']
    assert evidence_handles(rows)=={'actual-source':'ev1','unrelated-source':'ev2'}
    plain=GroundedAnswerGenerator(None,source_citations=True).response_schema(rows)
    assert list(schema['properties'])==list(plain['properties'])


def test_complete_pdf_locators_use_handles_but_keep_actual_document_and_page():
    model=generator(None);row=evidence('physical-source')
    scope={'coverage':'complete_pdf_bytes_with_extracted_text_index',
           'documents':[{'doc_id':row.doc_id,'page_count':3}]}
    prompt=model.prompt('State the requirement.',[row],'en',document_scope_context=scope)
    assert '[PDF PAGE LOCATORS]' in prompt
    assert '{"chunk_id":"ev1","doc_id":"doc-1","page":3}' in prompt
    assert scope['documents'][0]['doc_id']=='doc-1'


def test_temporal_system_references_use_the_same_handles_without_mutating_context():
    context={'selected_doc_ids':['doc-1'],'evidence_chunk_ids':['actual'],'description':'actual'}
    before=copy.deepcopy(context)
    prompt=generator(None).prompt('State the requirement.',[evidence('actual')],'en',temporal_context=context)
    assert '"evidence_chunk_ids": ["ev1"]' in prompt
    assert '"description": "actual"' in prompt and context==before


def test_real_ids_restored_before_source_quote_and_claim_verification_without_mutating_response():
    wire=payload(chunk='ev1');before=copy.deepcopy(wire)
    llm=FakeLLM(wire);row=evidence('a'*64+'_p3_s1_c1')
    answer=generator(llm).answer('Which course is required?',[row],'en')
    assert not answer.abstained and llm.calls==1
    assert answer.citations[0].chunk_id==row.chunk_id and answer.citations[0].page==3
    assert answer.citations[0].quote=='MATH101 is required.'
    assert answer.claims[0].citation_ids==(row.chunk_id,)
    assert answer.to_public_dict()['citations'][0]['chunk_id']==row.chunk_id
    assert wire==before


@pytest.mark.parametrize('identifier',['ev2','ev999','c1',None,True,{},['ev1']])
def test_foreign_or_malformed_handles_cannot_bypass_current_source_scope(identifier):
    wire=payload(chunk=identifier)
    answer=generator(FakeLLM(wire)).answer('Which course is required?',[evidence()],'en')
    assert answer.abstained and answer.reason=='invalid_citation'
    assert not answer.to_public_dict()['citations']


def test_claims_cannot_smuggle_a_different_source_from_valid_top_level_citation():
    wire=payload(chunk='ev1');wire['claims'][0]['citation_ids']=['ev2']
    answer=generator(FakeLLM(wire)).answer('Which course is required?',[evidence()],'en')
    assert answer.abstained and answer.reason=='invalid_citation'


@pytest.mark.parametrize('text',['MATH101 has 99 credits.','MATH101 is not required.','SCI999 is required.'])
def test_short_handles_do_not_make_unsupported_facts_valid(text):
    answer=generator(FakeLLM(payload(text,chunk='ev1'))).answer('Which course is required?',[evidence()],'en')
    assert answer.abstained and not answer.to_public_dict()['citations']


def test_restoration_preserves_bad_extra_fields_for_existing_contract_to_reject():
    wire=payload(chunk='ev1');wire['citations'][0]['page']=999
    answer=generator(FakeLLM(wire)).answer('Which course is required?',[evidence()],'en')
    assert answer.abstained


@pytest.mark.parametrize('reason,verified', [('document_does_not_mention',True),('unsupported_claim',False)])
def test_valid_abstention_reason_remains_distinct(reason,verified):
    wire={'answer':'The source does not establish the fact.','confidence':'low','abstained':True,
          'abstention_reason':reason,'citations':[],'claims':[]}
    answer=generator(FakeLLM(wire)).answer('Which fact is established?',[evidence()],'en',
                                        verified_document_absence=verified)
    assert answer.abstained and answer.reason==reason


def test_reference_translation_never_changes_answer_or_claim_source_text():
    wire=payload(text='Literal ev1 is preserved.',chunk='ev1')
    restored=restore_citations(wire,{'actual':'ev1'})
    assert restored['answer']==restored['claims'][0]['text']=='Literal ev1 is preserved.'
    assert restored['claims'][0]['citation_ids']==['actual']


def test_concurrent_answers_never_share_handle_maps():
    barrier=Barrier(2)
    class Model:
        def generate_json(self,*args,**kwargs):
            barrier.wait(timeout=5)
            return payload(chunk='ev1')
    model=generator(Model())
    rows=[replace(evidence('source-a'),doc_id='doc-a'),replace(evidence('source-b'),doc_id='doc-b')]
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers=list(pool.map(lambda row:model.answer('Which course is required?',[row],'en'),rows))
    assert all(not answer.abstained for answer in answers)
    assert [(a.citations[0].chunk_id,a.citations[0].doc_id) for a in answers]==[('source-a','doc-a'),('source-b','doc-b')]


@pytest.mark.parametrize('source_pages',[False,True])
def test_both_answer_cache_routes_bind_the_optional_policy_and_keep_default_identity(source_pages):
    llm=FakeLLM(payload());model=GroundedAnswerGenerator(llm,source_citations=True)
    service=CampusAIQueryService(FakeRetriever([evidence()]),model)
    def ask():
        return (service.ask_source_pages('Which course is required?',[evidence()],language='en') if source_pages
                else service.ask('Which course is required?',language='en',corpus_version='fixed'))
    try:
        assert not ask().abstained;calls=llm.calls
        model.compact_citation_ids=False;ask()
        assert service.last_cache_hit and llm.calls==calls
        model.compact_citation_ids=True;llm.payload=payload(chunk='ev1')
        assert not ask().abstained and not service.last_cache_hit and llm.calls==calls+1
        ask();assert service.last_cache_hit
        model.compact_citation_ids=False;ask()
        assert service.last_cache_hit and llm.calls==calls+1
    finally:service.close()


@pytest.mark.parametrize('value',[True,'yes',1,None])
def test_unsupported_configuration_cannot_silently_enable_handles(value):
    with pytest.raises(ValueError):GroundedAnswerGenerator(None,compact_citation_ids=value)


@pytest.mark.parametrize('flag,source,accepted', [(True,True,True),(True,False,False),(1,True,False),(False,False,True)])
def test_app_profile_validates_and_passes_the_optional_wire_policy(tmp_path,monkeypatch,flag,source,accepted):
    import json
    from scripts.operations import serve
    path=tmp_path/'profile.json'
    path.write_text(json.dumps({'llm':{'provider':'gemini'},'rag':{
        'source_citations':source,'compact_citation_ids':flag}}))
    for name in ['CAMPUSAI_STATE_ROOT','CAMPUSAI_ANSWER_CALIBRATION','CAMPUSAI_ANSWER_CALIBRATION_SHA256','CAMPUSAI_RETRIEVAL_CALIBRATION']:
        monkeypatch.delenv(name,raising=False)
    for name,value in {'CAMPUSAI_LLM_CONFIG':path,'CAMPUSAI_INDEX_DIR':tmp_path/'index',
            'CAMPUSAI_STORE_DIR':tmp_path/'store','CAMPUSAI_JOB_DB':tmp_path/'jobs.sqlite3',
            'CAMPUSAI_RAG_CACHE_PATH':tmp_path/'answers.sqlite3'}.items():
        monkeypatch.setenv(name,str(value))
    monkeypatch.setattr(serve,'create_llm',lambda *args,**kwargs:FakeLLM({}))
    if not accepted:
        with pytest.raises(ValueError,match='RAG context profile'):serve.build_application()
    else:
        app=serve.build_application()
        try:assert app.query_service.answer_generator.compact_citation_ids is flag
        finally:app.close()
