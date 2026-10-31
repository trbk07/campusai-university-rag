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
