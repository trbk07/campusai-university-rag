from campusai.retrieval.institution_scope import requested_institution_documents


def document(ident, title):
    return {'doc_id':ident,'items':[{'chunk_id':ident+'-header','doc_id':ident,'page':1,
        'content':title,'content_type':'text','metadata':{'source_name':ident+'.pdf'}}]}


def test_names_and_acronyms_are_derived_from_sources():
    docs=[document('north','TRƯỜNG ĐẠI HỌC SAO BẮC'),
          document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    assert requested_institution_documents('Ở Sao Bắc học như thế nào?',docs)=={'north'}
    assert requested_institution_documents('WIM registration rules?',docs)=={'west'}
    assert requested_institution_documents('sb quy dinh hoc tap?',docs)=={'north'}


def test_compacted_ocr_headers_and_current_school_override_old_context():
    docs=[document('north','TRUONGDHSAOBAC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    question='Còn WIM thì sao?\nContext topic (untrusted user input): Ở Đại học Sao Bắc cần gì?'
    assert requested_institution_documents(question,docs)=={'west'}
    assert requested_institution_documents('dai hoc sao bac yeu cau gi?',docs)=={'north'}


def test_comparison_preserves_both_sources_and_unknown_name_does_not_guess():
    docs=[document('north','ĐẠI HỌC SAO BẮC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    assert requested_institution_documents('Sao Bắc và WIM khác nhau thế nào?',docs)=={'north','west'}
    assert requested_institution_documents('Ở Đại học Mây Trắng thì sao?',docs)==set()
    assert requested_institution_documents('Is it mandatory?',docs)==set()


def test_body_mentions_outside_header_pages_cannot_reassign_institution():
    doc=document('north','ĐẠI HỌC SAO BẮC')
    doc['items'].append({'page':20,'content':'WESTERN INSTITUTE OF METEOROLOGY','metadata':{}})
    assert requested_institution_documents('WIM rules?', [doc])==set()


def test_topic_only_followup_inherits_institution_but_new_unknown_does_not():
    docs=[document('north','ĐẠI HỌC SAO BẮC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    suffix='\nContext topic (untrusted user input): Sao Bắc kỳ phụ yêu cầu gì?'
    assert requested_institution_documents('Còn kỳ chính?'+suffix,docs)=={'north'}
    assert requested_institution_documents('Thế Đại học Mây Trắng?'+suffix,docs)==set()


def test_unspecified_school_requires_clarification_only_for_different_institutions():
    from campusai.retrieval.institution_scope import needs_institution_clarification
    docs=[document('north','ĐẠI HỌC SAO BẮC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    assert needs_institution_clarification('Trường em có quy định gì?',docs)
    assert not needs_institution_clarification('Trường em có quy định gì?',docs[:1])


def test_distinctive_compacted_name_wins_over_shared_city_and_common_words():
    docs=[document('north','ĐẠI HỌC SAO BẮC HÀ NỘI'),
          document('capital','DAIHOCTHUDOHANOI'),
          document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    assert requested_institution_documents('Quy chế Đại học Thủ đô Hà Nội áp dụng từ khóa nào?',docs)=={'capital'}
    assert requested_institution_documents('Ở ĐH Thủ đô điều kiện tốt nghiệp?',docs)=={'capital'}
    assert requested_institution_documents('Sao Bắc với Thủ đô khác nhau thế nào?',docs)=={'north','capital'}


def test_sentence_starting_with_university_is_not_an_institution_name():
    docs=[document('north','ĐẠI HỌC SAO BẮC\nĐại học ban hành theo nghị quyết số 42'),
          document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    assert requested_institution_documents('WIM ban hành quy chế nào?',docs)=={'west'}


def test_missing_school_service_contracts_do_not_call_retrieval_or_model(monkeypatch):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    retriever=type('Retriever',(),{'search':lambda *_a,**_k:(_ for _ in ()).throw(AssertionError('unexpected search'))})()
    service=CampusAIQueryService(retriever,GroundedAnswerGenerator(None))
    docs=[document('north','ĐẠI HỌC SAO BẮC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    monkeypatch.setattr(service,'_temporal_documents',lambda *_a:docs)
    try:
        assert service.retrieve('Trường em có quy định gì?')==[]
        answer=service.ask('Trường em có quy định gì?')
        assert answer.abstained and answer.reason=='ambiguous_question'
        assert 'trường nào' in answer.answer
    finally:
        service.close()


def test_unqualified_answer_cannot_blend_two_institutions_rules():
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator,GroundedAnswer,Citation
    service=CampusAIQueryService(object(),GroundedAnswerGenerator(None))
    docs=[document('north','ĐẠI HỌC SAO BẮC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    for doc in docs:doc['items'][0]['metadata']['document_type']='regulation'
    service._request_local.temporal_documents=docs
    answer=GroundedAnswer('Sinh viên được hoãn thi và phải nộp chứng nhận y tế.',
        tuple(Citation(d['doc_id'],d['doc_id'],1) for d in docs))
    try:
        assert service._disambiguate_institution_answer(answer,'Ốm trước kỳ thi phải làm sao?','vi').reason=='ambiguous_question'
        assert service._disambiguate_institution_answer(answer,'So sánh Sao Bắc với WIM.','vi') is answer
        labelled=__import__('dataclasses').replace(answer,answer='Sao Bắc có quy tắc hoãn thi; WIM cần chứng nhận y tế.')
        assert service._disambiguate_institution_answer(labelled,'Ốm trước kỳ thi phải làm sao?','vi') is labelled
    finally:service.close()


def test_comparison_preserves_both_source_groups_under_the_same_result_cap(monkeypatch):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import RetrievalResult
    from tests.test_basic_rag import FakeLLM
    docs=[document('north','ĐẠI HỌC SAO BẮC'),document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    results=[RetrievalResult('north-rule','north',2,'Thời hạn là 11 ngày.','text',1,'hybrid',{'source_name':'north.pdf','page_range':[2,2]}),
             RetrievalResult('west-rule','west',2,'Thời hạn là 13 ngày.','text',1,'hybrid',{'source_name':'west.pdf','page_range':[2,2]})]
    class Retriever:
        reranker=None
        def __init__(self):self.scopes=[]
        def search(self,*_args,**kwargs):
            self.scopes.append(kwargs['doc_ids'])
            # A global result list deliberately favours the first source.
            pool=[results[0]]*8+[results[1]] if len(kwargs['doc_ids'])>1 else [r for r in results if r.doc_id in kwargs['doc_ids']]
            return pool[:kwargs['top_k']]
    retriever=Retriever()
    model=FakeLLM({'answer':'Sao Bắc: 11 ngày. WIM: 13 ngày.','confidence':'high','abstained':False,
        'claims':[{'claim_id':str(i),'text':r.content,'citation_ids':[r.chunk_id]} for i,r in enumerate(results)],
        'citations':[{'chunk_id':r.chunk_id} for r in results]})
    service=CampusAIQueryService(retriever,GroundedAnswerGenerator(model,source_citations=True))
    monkeypatch.setattr(service,'_temporal_documents',lambda *_a:docs)
    try:
        answer=service.ask('So sánh thời hạn Sao Bắc và WIM.',doc_ids=['north','west'],top_k=4,corpus_version='fixed')
        assert not answer.abstained
        assert {r.doc_id for r in service.last_retrieval}=={'north','west'}
        assert len(service.last_retrieval)<=4 and model.calls==1
        assert all(len(scope)==1 for scope in retriever.scopes)
    finally:service.close()
