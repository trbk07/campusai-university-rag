"""Regression checks for source-derived scope, with fictional institutions."""
import pytest
from campusai.retrieval.institution_scope import resolve_institution_request


def document(ident, title, kind='regulation'):
    return {'doc_id': ident, 'items': [{'doc_id': ident, 'chunk_id': ident + '-1',
        'page': 1, 'content': title, 'metadata': {'document_type': kind}}]}


@pytest.fixture
def schools():
    return [document('north', 'TRƯỜNG ĐẠI HỌC SAO BẮC'),
            document('west', 'WESTERN INSTITUTE OF METEOROLOGY')]


@pytest.mark.parametrize('question', [
    'Học tối thiểu bao nhiêu tín chỉ?', '8,6 điểm quy đổi ra sao?',
    'Điều kiện tốt nghiệp?', 'Trường em được hoãn thi không?',
])
def test_policy_needs_school(schools, question):
    assert resolve_institution_request(question, schools).needs_clarification


@pytest.mark.parametrize('question', [
    'Giải thích binary search', 'Tóm tắt các PDF',
    'So sánh quy định Sao Bắc và WIM', 'Tất cả trường yêu cầu bao nhiêu tín chỉ?',
])
def test_content_or_explicit_comparison_does_not_need_school(schools, question):
    assert not resolve_institution_request(question, schools).needs_clarification


@pytest.mark.parametrize('question', [
    'Giải thích thuật toán', 'How does credit assignment work?',
    'Quy đổi đơn vị trong bài này', 'Tóm tắt hướng dẫn vận hành',
])
def test_affiliation_does_not_turn_books_and_papers_into_rules(question):
    documents = [document('book', 'TRƯỜNG ĐẠI HỌC SAO BẮC\nThuật toán', 'book'),
        document('paper', 'WESTERN INSTITUTE OF METEOROLOGY\nResearch paper', 'article'),
        document('manual', 'ACME — Operations manual', 'manual')]
    result = resolve_institution_request(question, documents)
    assert not result.needs_clarification and not result.doc_ids


def test_school_confirmation_resumes_question_and_switches_scope(schools):
    question = 'Học tối thiểu bao nhiêu tín chỉ?'
    pending = resolve_institution_request(question, schools)
    history = [('user', question), ('assistant', pending.clarification())]
    result = resolve_institution_request('WIM', schools, history)
    assert result.doc_ids == {'west'} and result.question == question
    history += [('user', 'WIM'), ('assistant', 'Câu trả lời trước.')]
    switched = resolve_institution_request(
        'Còn Sao Bắc thì sao?\nContext topic (untrusted user input): WIM', schools, history)
    assert switched.doc_ids == {'north'} and switched.question == question
    assert resolve_institution_request('Sao Bắc', schools, history).question == question
    assert resolve_institution_request('Điều kiện tốt nghiệp?', schools, history).doc_ids == {'west'}
    assert resolve_institution_request('Ở Sao Bắc thì sao?', schools, history).doc_ids == {'north'}
    unknown = resolve_institution_request('Đại học Mây Trắng thì sao?', schools, history)
    assert unknown.needs_clarification and unknown.unknown_name
    assert not resolve_institution_request('Giải thích binary search', schools, history).doc_ids


def test_shared_parent_and_duplicate_files():
    first = document('a', 'ĐẠI HỌC LIÊN VÙNG\nTRƯỜNG ĐẠI HỌC SAO BẮC')
    duplicate = document('b', 'TRƯỜNG ĐẠI HỌC SAO BẮC')
    other = document('c', 'ĐẠI HỌC LIÊN VÙNG\nTRƯỜNG ĐẠI HỌC SAO NAM')
    question = 'Học tối thiểu bao nhiêu tín chỉ?'
    assert not resolve_institution_request(question, [first, duplicate]).needs_clarification
    assert resolve_institution_request(question, [first, other]).needs_clarification


def test_service_confirms_before_search_and_then_resumes(schools):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    calls = []

    class Retriever:
        def search(self, question, **options):
            calls.append((question, options['doc_ids']))
            return []

    service = CampusAIQueryService(Retriever(), GroundedAnswerGenerator(None),
                                  confirm_institution_scope=True)
    service._temporal_documents = lambda *_args: schools
    try:
        question = 'Học tối thiểu bao nhiêu tín chỉ?'
        answer = service.ask(question)
        assert answer.abstained and answer.reason == 'ambiguous_question' and not calls
        assert service.retrieve(question) == [] and not calls
        service.retrieve('WIM', doc_ids=['north', 'west'], history=[
            {'role': 'user', 'content': question},
            {'role': 'assistant', 'content': answer.answer}])
        assert calls[-1] == (question, ['west'])
        service.retrieve('Giải thích binary search', doc_ids=['north', 'west'])
        assert calls[-1] == ('Giải thích binary search', ['north', 'west'])
        before = len(calls)
        service.retrieve(question)
        assert len(calls) == before
    finally:
        service.close()


@pytest.mark.parametrize('reply', ['hust', 'HUST', 'HuSt', 'h.u.s.t', 'OTHER'])
def test_unmatched_abbreviation_explains_missing_scope_and_keeps_question(schools, reply):
    question='Học tối thiểu bao nhiêu tín chỉ?'
    first=resolve_institution_request(question, schools)
    history=[('user', question), ('assistant', first.clarification())]
    unknown=resolve_institution_request(reply, schools, history)
    assert unknown.needs_clarification and unknown.unknown_name and not unknown.doc_ids
    message=unknown.clarification()
    assert reply in message and 'tên trường đầy đủ' in message
    assert 'TRƯỜNG ĐẠI HỌC SAO BẮC' in message
    assert 'WESTERN INSTITUTE OF METEOROLOGY' in message
    history += [('user', reply), ('assistant', message)]
    result=resolve_institution_request('Sao Bắc', schools, history)
    assert result.doc_ids == {'north'} and result.question == question


def test_fresh_content_question_after_clarification_is_not_a_school_reply(schools):
    first=resolve_institution_request('Điều kiện tốt nghiệp?', schools)
    history=[('user','Điều kiện tốt nghiệp?'),('assistant', first.clarification())]
    result=resolve_institution_request('Giải thích binary search', schools, history)
    assert not result.needs_clarification and not result.doc_ids


def test_unknown_reply_never_becomes_an_evidence_lookup(schools):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator

    class Retriever:
        def search(self, *_args, **_options):
            raise AssertionError('Unresolved school choice must not reach retrieval')

    service=CampusAIQueryService(Retriever(),GroundedAnswerGenerator(None),confirm_institution_scope=True)
    service._temporal_documents=lambda *_args:schools
    question='Học tối thiểu bao nhiêu tín chỉ?'
    history=[{'role':'user','content':question},
             {'role':'assistant','content':resolve_institution_request(question,schools).clarification()}]
    try:
        answer=service.ask('hust',history=history)
        assert answer.reason=='ambiguous_question' and 'hust' in answer.answer
        assert not answer.citations
        assert service.retrieve('hust',history=history)==[]
    finally:
        service.close()


@pytest.mark.parametrize('language', ['vi','en'])
def test_missing_information_messages_give_an_action_without_changing_reason(language):
    from campusai.rag.abstention import user_message,canonicalize_abstention_reason
    for reason in ['ambiguous_question','no_evidence_found','document_does_not_mention','unsupported_claim']:
        assert canonicalize_abstention_reason(reason)==reason
        message=user_message(reason,language)
        assert ('Bạn' in message or 'Hãy' in message) if language=='vi' else ('Please' in message or 'You can' in message)
    assert 'chương trình' not in user_message('ambiguous_question',language)
    assert 'PDF' not in user_message('provider_error',language)


def test_prompt_distinguishes_missing_user_scope_from_insufficient_evidence():
    from campusai.rag.grounding import GroundedAnswerGenerator
    prompt=GroundedAnswerGenerator(None).prompt('Explain the selected passage',[])
    assert 'MISSING USER SCOPE' in prompt
    assert 'do not guess it: abstain with ambiguous_question' in prompt
    assert 'rather than pretending the user omitted information' in prompt


class AliasModel:
    def __init__(self, result):
        self.result=result
        self.calls=[]

    def generate_json(self, prompt, **options):
        self.calls.append((prompt,options))
        if isinstance(self.result,Exception):raise self.result
        return self.result


@pytest.fixture
def alias_service(schools):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    services=[]

    def make(result):
        model=AliasModel(result)
        service=CampusAIQueryService(object(),GroundedAnswerGenerator(model),confirm_institution_scope=True)
        services.append(service)
        question='Học tối thiểu bao nhiêu tín chỉ?'
        history=[('user',question),('assistant',resolve_institution_request(question,schools).clarification())]
        return service,model,question,history

    yield make
    for service in services:service.close()


def test_model_alias_match_routes_pending_question_and_remembers_choice(schools,alias_service):
    service,model,question,history=alias_service({
        'status':'confirmed','candidate_id':'c0','match_type':'established_alias'})
    result=service._institution_request('NorthStar',schools,history)
    assert result.doc_ids=={'north'} and result.question==question
    assert len(model.calls)==1
    prompt,options=model.calls[0]
    assert question not in prompt and 'doc_ids' not in prompt
    assert 'NorthStar' in prompt and 'TRƯỜNG ĐẠI HỌC SAO BẮC' in prompt
    assert options['generationConfig']['maxOutputTokens']==256
    history += [('user','NorthStar'),('assistant','Câu trả lời có nguồn.')]
    assert service._institution_request('Điều kiện tốt nghiệp?',schools,history).doc_ids=={'north'}
    assert service._institution_request('northstar',schools,history).doc_ids=={'north'}
    assert len(model.calls)==1


@pytest.mark.parametrize('result', [
    {'status':'ambiguous','candidate_id':'none','match_type':'none'},
    {'status':'unknown','candidate_id':'none','match_type':'none'},
    {'status':'confirmed','candidate_id':'not-authorized','match_type':'established_alias'},
    {'status':'confirmed','candidate_id':'c0','match_type':'nearest_name'},
    {'status':'confirmed','candidate_id':'c0','match_type':'established_alias','extra':'guess'},
    None,
])
def test_uncertain_or_invalid_alias_results_ask_user_without_selecting(schools,alias_service,result):
    service,model,_,history=alias_service(result)
    for _ in range(2):
        response=service._institution_request('northstar',schools,history)
        assert response.needs_clarification and not response.doc_ids
        assert 'tên trường đầy đủ' in response.clarification()
    assert len(model.calls)==1


def test_alias_api_error_explains_unavailability_without_retry(schools,alias_service):
    from campusai.llm.client import LLMProviderError
    service,model,_,history=alias_service(LLMProviderError('timeout'))
    for _ in range(2):
        response=service._institution_request('northstar',schools,history)
        assert response.needs_clarification and not response.doc_ids
        assert 'dịch vụ AI chưa thực hiện được' in response.clarification()
    assert len(model.calls)==1


def test_known_source_alias_needs_no_model_and_alias_cache_cannot_cross_scope(schools,alias_service):
    service,model,_,history=alias_service({'status':'confirmed','candidate_id':'c0','match_type':'name_variant'})
    assert service._institution_request('WIM',schools,history).doc_ids=={'west'}
    assert not model.calls
    assert service._institution_request('northstar',schools,history).doc_ids=={'north'}
    model.result={'status':'unknown','candidate_id':'none','match_type':'none'}
    response=service._institution_request('northstar',schools[1:],history)
    assert response.needs_clarification and not response.doc_ids
    assert len(model.calls)==2
    assert 'SAO BẮC' not in model.calls[-1][0]


def test_full_question_alias_and_school_switch_preserve_intent(schools,alias_service):
    from campusai.rag.context import resolve_query
    service,model,_,_=alias_service({'status':'confirmed','candidate_id':'c0','match_type':'established_alias'})
    original='Quy định của NorthStar là gì?'
    first=service._institution_request(original,schools,[])
    assert first.doc_ids=={'north'} and 'Quy định' in first.question
    assert 'SAO BẮC' in first.question and 'NorthStar' not in first.question
    history=[{'role':'user','content':original},{'role':'assistant','content':'Previous answer.'}]
    followup=resolve_query('Còn WIM thì sao?',history=history)
    second=service._institution_request(followup.resolved,schools,followup.history)
    assert second.doc_ids=={'west'}
    assert 'Quy định' in second.question and 'WESTERN INSTITUTE' in second.question
    assert 'NorthStar' not in second.question and 'SAO BẮC' not in second.question
    history=[{'role':'user','content':second.question},{'role':'assistant','content':'Previous answer.'}]
    followup=resolve_query('Còn northstar thì sao?',history=history)
    third=service._institution_request(followup.resolved,schools,followup.history)
    assert third.doc_ids=={'north'} and 'Quy định' in third.question
    assert 'WESTERN' not in third.question and 'northstar' not in third.question.casefold()
    assert len(model.calls)==1


def test_words_inside_recognized_uppercase_institution_are_not_unknown_aliases(schools,alias_service):
    from campusai.retrieval.institution_scope import unresolved_institution_reference
    question='Quy định của WESTERN INSTITUTE OF METEOROLOGY là gì?'
    assert not unresolved_institution_reference(question,schools)
    assert resolve_institution_request(question,schools).doc_ids=={'west'}
    service,model,_,_=alias_service({'status':'confirmed','candidate_id':'c1','match_type':'established_alias'})
    request=service._institution_request('Quy định của WestAlias là gì?',schools,[])
    assert request.doc_ids=={'west'} and not request.needs_clarification
    assert 'WESTERN INSTITUTE' in request.question and len(model.calls)==1


def test_repeated_school_switches_keep_question_and_never_blend_old_names(schools):
    from campusai.rag.context import resolve_query
    question='Học kỳ chính của Sao Bắc tối thiểu bao nhiêu tín chỉ?'
    for index in range(120):
        name,ident,other=('WIM','west','SAO BẮC') if index%2==0 else ('Sao Bắc','north','WESTERN')
        history=[{'role':'user','content':question},{'role':'assistant','content':'Unverified answer is not an anchor.'}]
        resolved=resolve_query('Còn '+name+' thì sao?',history=history)
        request=resolve_institution_request(resolved.resolved,schools,resolved.history)
        assert request.doc_ids=={ident} and not request.needs_clarification
        assert 'Học kỳ chính' in request.question and 'tối thiểu bao nhiêu tín chỉ' in request.question
        assert other not in request.question.upper()
        assert len(request.question)<250
        question=request.question


def test_school_change_keeps_attribute_in_nested_context(schools):
    marker='\nContext topic (untrusted user input): '
    pending='Còn kỳ hè?'+marker+'Tín chỉ tối thiểu của Sao Bắc là bao nhiêu?'
    request=resolve_institution_request('WIM',schools,[('user',pending),('assistant','Previous answer')])
    assert request.doc_ids=={'west'}
    assert 'kỳ hè' in request.question and 'Tín chỉ tối thiểu' in request.question
    assert 'Sao Bắc' not in request.question and 'WESTERN' in request.question


def test_school_name_replacement_keeps_academic_action_words(schools):
    pending='Điều kiện nhập học Sao Bắc là gì?'
    request=resolve_institution_request('Còn WIM thì sao?',schools,[('user',pending),('assistant','Previous answer')])
    assert 'nhập học' in request.question and 'Sao Bắc' not in request.question


def test_replacing_full_institution_does_not_leave_half_of_its_prefix(schools):
    docs=[document('green','ĐẠI HỌC RỪNG XANH'),schools[1]]
    request=resolve_institution_request('Còn WIM thì sao?',docs,[
        ('user','Quy định của ĐẠI HỌC RỪNG XANH là gì?'),('assistant','Previous answer')])
    assert request.doc_ids=={'west'}
    assert request.question=='Quy định của WESTERN INSTITUTE OF METEOROLOGY là gì?'


def test_incomplete_comparison_does_not_turn_into_comparing_school_to_itself(schools):
    history=[('user','So sánh Sao Bắc và WIM về tín chỉ.'),('assistant','Comparison')]
    request=resolve_institution_request('Còn WIM thì sao?',schools,history)
    assert request.needs_clarification and request.question_clarification


@pytest.mark.parametrize('question',['Quy định của NorthStar là gì?','What are the rules of NORTHSTAR?'])
def test_explicit_unknown_school_is_not_silently_answered_from_only_selected_school(schools,question):
    request=resolve_institution_request(question,schools[1:])
    assert request.needs_clarification and request.unknown_name
    assert not request.doc_ids


def test_resolved_intent_is_not_expanded_again_from_old_history():
    from campusai.rag.context import resolve_query
    marker='\nContext topic (untrusted user input): '
    prior='Give an example'+marker+'Explain binary search'
    history=[{'role':'user','content':'Explain binary search'},
        {'role':'assistant','content':'Unverified fact 999'},
        {'role':'user','content':prior},{'role':'assistant','content':'Another answer'}]
    result=resolve_query('Explain more',history=history)
    assert result.resolved.count('Explain binary search')==1
    assert 'Unverified fact 999' not in result.resolved


def test_api_returns_user_intent_separately_from_answer():
    from types import SimpleNamespace
    from campusai.api import CampusAIApplication
    from campusai.observability import MetricsRegistry
    from campusai.rag.grounding import GroundedAnswer
    query='Rules of the selected institution?'
    service=SimpleNamespace(ask=lambda *_a,**_k:GroundedAnswer('Insufficient evidence',(),'low',True,reason='unsupported_claim'),
        last_cache_hit=False,metrics=MetricsRegistry(),_request_local=SimpleNamespace(context_question=query))
    response=CampusAIApplication(service).query(query)
    assert response['context_question']==query
    assert 'Insufficient evidence' not in response['context_question']


@pytest.fixture
def cached_service(schools):
    from types import SimpleNamespace
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator,GroundedAnswer,Citation
    from campusai.rag.claims import Claim
    service=CampusAIQueryService(SimpleNamespace(reranker=None),GroundedAnswerGenerator(None),confirm_institution_scope=True)
    service._temporal_documents=lambda *_a:schools
    calls=[]

    def generate(question,doc_ids,filters,top_k,mode,language,version,key):
        calls.append((question,tuple(doc_ids),version))
        ident=doc_ids[0];text='Quy định chung của tài liệu.'
        citation=Citation(ident+'-rule',ident,2,quote=text,source_name=ident+'.pdf',page_range=(2,2))
        claim=Claim('rule',text,citation_ids=(citation.chunk_id,),status='supported',support_score=1)
        answer=GroundedAnswer(text,(citation,),'high',False,claims=(claim,))
        service.cache.put(key,answer)
        return answer

    service._ask_uncached_or_cached=generate
    yield service,calls
    service.close()


def test_returning_to_same_complete_rule_reuses_verified_answer_only_for_its_source(cached_service):
    service,calls=cached_service
    question='Quy định của Sao Bắc là gì?'
    first=service.ask(question,corpus_version='v1')
    history=[{'role':'user','content':service._request_local.context_question},
             {'role':'assistant','content':first.answer}]
    second=service.ask('Còn WIM thì sao?',history=history,corpus_version='v1')
    assert {c.doc_id for c in second.citations}=={'west'}
    history=[{'role':'user','content':service._request_local.context_question},
             {'role':'assistant','content':second.answer}]
    third=service.ask('Còn Sao Bắc thì sao?',history=history,corpus_version='v1')
    assert service.last_cache_hit and {c.doc_id for c in third.citations}=={'north'}
    assert len(calls)==2
    service.ask(question,corpus_version='v2')
    assert not service.last_cache_hit and len(calls)==3


def test_personal_questions_do_not_share_answers_across_different_histories(cached_service):
    service,calls=cached_service
    question='Tôi phải đáp ứng quy định của Sao Bắc thế nào?'
    for background in ['I have supplied one record.','I have supplied another record.']:
        service.ask(question,history=[{'role':'user','content':background}],corpus_version='v1')
    assert len(calls)==2 and not service.last_cache_hit


def test_selected_passages_keep_history_specific_cache(cached_service):
    service,calls=cached_service
    for background in ['First context.','Second context.']:
        service.ask('Quy định của Sao Bắc là gì?',selected_text='The highlighted passage',
            history=[{'role':'user','content':background}],corpus_version='v1')
    assert len(calls)==2 and not service.last_cache_hit


def test_unverified_answers_are_never_promoted_to_intent_cache(cached_service):
    from campusai.rag.grounding import GroundedAnswer
    service,calls=cached_service

    def reject(question,doc_ids,filters,top_k,mode,language,version,key):
        calls.append(question)
        answer=GroundedAnswer('Not verified',(),'low',True,reason='unsupported_claim')
        service.cache.put(key,answer)
        return answer

    service._ask_uncached_or_cached=reject
    for background in ['First context.','Second context.']:
        answer=service.ask('Quy định của Sao Bắc là gì?',
            history=[{'role':'user','content':background}],corpus_version='v1')
        assert answer.abstained
    assert len(calls)==2


def test_other_phases_keep_original_history_cache_policy(cached_service):
    service,calls=cached_service
    service.confirm_institution_scope=False
    for background in ['First context.','Second context.']:
        service.ask('Quy định của Sao Bắc là gì?',
            history=[{'role':'user','content':background}],corpus_version='v1')
    assert len(calls)==2 and not service.last_cache_hit


def test_implicit_school_survives_many_fresh_questions_without_repeating_name(cached_service):
    service,calls=cached_service
    history=[{'role':'user','content':'Quy định của Sao Bắc là gì?'},
             {'role':'assistant','content':'Previous answer.'}]
    for _ in range(15):
        answer=service.ask('Điều kiện đăng ký học kỳ chính là gì?',history=history[-6:],corpus_version='v1')
        assert not answer.abstained and {c.doc_id for c in answer.citations}=={'north'}
        remembered=service._request_local.context_question
        assert 'SAO BẮC' in remembered
        history += [{'role':'user','content':remembered},{'role':'assistant','content':answer.answer}]


def test_browser_memory_keeps_topic_after_many_turns_and_resets_between_chats():
    import shutil,subprocess
    if not shutil.which('node'):pytest.skip('Node required for frontend memory check')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({assert,$:()=>({textContent:''})});
const code=fs.readFileSync('src/campusai/ui/features/chat.js','utf8').replace(/^import .*;\r?$/gm,'').replace(/^export /gm,'');
vm.runInContext(code,context);
vm.runInContext(`
const key='vi:a,b';
const user={role:'user',text:'Explain binary search',scopeKey:key};
messages.push(user,{role:'assistant',scopeKey:key,answer:{answer:'Unverified assistant detail'}});
rememberQuestion(key,user,{context_question:'Explain binary search'});
for(let i=0;i<250;i++) {
  messages.push({role:'user',text:'thanks',scopeKey:key},{role:'assistant',scopeKey:key,answer:{answer:'ack'}});
  const history=conversationHistory(key);
  assert(history.length<=7);
  assert(history.some(turn=>turn.role==='user'&&turn.content==='Explain binary search'));
  assert(!history.some(turn=>turn.role==='user'&&turn.content.includes('Unverified assistant')));
}
assert.deepEqual(conversationHistory('vi:different-docs'),[]);
const failed={};rememberQuestion(key,failed,{context_question:'Do not retain',partial:true});
assert.equal(topicMemory.get(key),'Explain binary search');
const fresh={role:'user',text:'Explain transactions',scopeKey:key};
rememberQuestion(key,fresh,{context_question:'Explain transactions'});
assert.equal(topicMemory.get(key),'Explain transactions');
renderConversation=()=>{};renderSources=()=>{};updateComposer=()=>{};
resetChat();assert.equal(topicMemory.size,0);assert.equal(messages.length,0);
`,context);
'''
    result=subprocess.run(['node','-'],input=script,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
