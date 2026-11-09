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


@pytest.mark.parametrize('question',[
    'HRO có quy định ngày nghỉ thế nào?',
    'ACME policy có áp dụng cho nhân viên thử việc không?',
    'Còn XTR thì quy chế cấp quyền thế nào?',
])
def test_nonacademic_policy_acronyms_are_not_school_choices(question):
    sources=[document('workplace','ACME — Employee policy','regulation'),
             document('technical','XTR — Operations handbook','handbook')]
    result=resolve_institution_request(question,sources)
    assert not result.needs_clarification and not result.unknown_name
    assert not result.unrecognized_reference and result.question==question


@pytest.mark.parametrize('question',[
    'Trường dữ liệu client_id có nghĩa gì?',
    'API có trường thông tin trạng thái nào?',
    'Mô tả trường nhập liệu địa chỉ.',
    'Trường bắt buộc nào cần điền?',
    'Điện trường và từ trường khác nhau thế nào?',
])
def test_technical_common_nouns_are_not_unknown_school_names(schools,question):
    sources=[*schools,document('technical','API fields and physical quantities','manual')]
    result=resolve_institution_request(question,sources)
    assert not result.needs_clarification and not result.unknown_name
    assert result.question==question


def test_common_noun_guard_preserves_explicit_and_capitalized_institution_names(schools):
    for question in ['Quy chế Trường Đại học Dữ liệu thế nào?',
                     'Trường Dữ Liệu có quy định tín chỉ gì?']:
        assert resolve_institution_request(question,schools).needs_clarification
    sources=[document('environment','Trường Đại học Môi trường'),*schools]
    result=resolve_institution_request('Quy chế đại học môi trường thế nào?',sources)
    assert result.doc_ids=={'environment'} and not result.needs_clarification


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


def test_role_title_is_not_an_unknown_school_name(schools):
    result = resolve_institution_request('Hiệu trưởng hiện tại của cả hai trường là ai?', schools)
    assert not result.needs_clarification and not result.unknown_name
    unknown = resolve_institution_request('Hiệu trưởng Trường Đại học Mây Trắng là ai?', schools)
    assert unknown.needs_clarification and unknown.unknown_name


@pytest.mark.parametrize('query',[
    'ZX987654 có bao nhiêu tín chỉ?',
    'HK7 ngành Điều khiển thông minh có mấy tín?',
    'hk7 nganh dieu khien thong minh co may tin?',
    'HK7 DKTM mấy tín chỉ?',
])
def test_unique_literal_source_locator_selects_document_without_guessing_school(schools,query):
    import copy
    docs=copy.deepcopy(schools)
    docs[0]['items'].append({'doc_id':'north','page':8,'content':
        '3. Ngành Điều khiển thông minh\nZX987654 Điều khiển robot 4 tín chỉ','metadata':{}})
    result=resolve_institution_request(query,docs)
    assert result.doc_ids=={'north'} and not result.needs_clarification


def test_duplicate_source_locator_cannot_pick_a_school_or_erase_unknown_name(schools):
    import copy
    docs=copy.deepcopy(schools)
    for doc in docs:doc['items'].append({'doc_id':doc['doc_id'],'page':8,
        'content':'3. Ngành Điều khiển thông minh\nZX987654 robot 4 tín chỉ','metadata':{}})
    assert resolve_institution_request('ZX987654 có mấy tín chỉ?',docs).needs_clarification
    assert resolve_institution_request('Ngành Điều khiển thông minh HK7 mấy tín chỉ?',docs).needs_clarification
    docs[1]['items'].pop()
    request=resolve_institution_request('Trường Đại học Mây Trắng môn ZX987654 mấy tín chỉ?',docs)
    assert request.needs_clarification and request.unknown_name and not request.doc_ids


def test_source_locator_needs_all_codes_and_literal_programme_heading(schools):
    import copy
    docs=copy.deepcopy(schools)
    docs[0]['items'].append({'doc_id':'north','page':8,'content':'ZX987654 robot 4 tín chỉ',
                            'metadata':{'program':'Điều khiển thông minh'}})
    assert resolve_institution_request('ZX987654 và ZX987655 có mấy tín chỉ?',docs).needs_clarification
    assert resolve_institution_request('Ngành Điều khiển thông minh HK7 mấy tín chỉ?',docs).needs_clarification
    assert resolve_institution_request('Học tối thiểu bao nhiêu tín chỉ?',docs).needs_clarification


@pytest.mark.parametrize('query',[
    'ABC và WIM có cùng giới hạn tín chỉ không?',
    'Kỳ hè ABC và WIM đều có giới hạn tín chỉ chứ?',
    'WIM và ABC có cùng mức tín chỉ không?',
])
def test_unresolved_comparison_arm_is_not_silently_discarded(schools,query):
    request=resolve_institution_request(query,schools)
    assert request.needs_clarification and request.unknown_name
    assert request.unrecognized_reference=='ABC' and not request.doc_ids


def test_deictic_school_pronoun_is_not_a_new_institution(schools):
    request=resolve_institution_request('So sánh quy chế Sao Bắc và WIM; hai trường kia có khác nhau không?',schools)
    assert request.doc_ids=={'north','west'} and not request.needs_clarification


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


@pytest.mark.parametrize('query',['Em đang hỏi về WIM nhé','Tôi chọn Sao Bắc','WIM','I am asking about WIM'])
def test_source_only_statement_acknowledges_without_retrieval_or_generated_facts(schools,query):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    class Retriever:
        def search(self,*args,**kwargs):
            raise AssertionError('A source selection without a question must not retrieve')
    service=CampusAIQueryService(Retriever(),GroundedAnswerGenerator(None),confirm_institution_scope=True)
    service._temporal_documents=lambda *_args:schools
    try:
        answer=service.ask(query)
        assert answer.abstained and not answer.citations
        assert service._request_local.conversation_kind=='source_choice'
        assert service._request_local.context_question
        assert 'Đã chọn nguồn:' in answer.answer
        # The next academic question retains only the user-confirmed owner.
        selected=resolve_institution_request('Điều kiện tốt nghiệp?',schools,
            [('user',service._request_local.context_question),('assistant',answer.answer)])
        assert selected.doc_ids==({'north'} if 'Sao' in query else {'west'})
    finally:service.close()


def test_scope_statement_resumes_pending_question_but_not_academic_field_as_choice(schools):
    from campusai.retrieval.institution_scope import _reference_only
    question='Điều kiện tốt nghiệp?'
    history=[('user',question),('assistant','Bạn muốn hỏi trường nào?')]
    selected=resolve_institution_request('Em đang hỏi về WIM nhé',schools,history)
    assert selected.question==question and selected.doc_ids=={'west'}
    for text in ['Điểm WIM','Tín chỉ Sao Bắc','Quy chế WIM','WIM ở đâu?',
                 'WIM có điểm C không?']:
        assert not _reference_only(text,schools)


def test_institution_acronyms_do_not_cross_generic_name_boundary(schools):
    from campusai.retrieval.institution_scope import requested_institution_documents
    for query in ['Xét HS như thế nào?','HB có phải giấy tờ không?']:
        assert not requested_institution_documents(query,schools)
    for alias in ['SB','DHSB','TDHSB','TSB','WIM']:
        assert requested_institution_documents(alias,schools)==({'west'} if alias=='WIM' else {'north'})


def test_split_complete_acronym_resolves_but_ambiguous_or_partial_prefix_does_not():
    docs=[document('north','TRƯỜNG ĐẠI HỌC SAO BẮC PHÍA NAM'),
          document('west','WESTERN INSTITUTE OF METEOROLOGY')]
    for query in ['dhsb pn cần bao nhiêu tín chỉ?','DHSB PN cần bao nhiêu tín chỉ?']:
        result=resolve_institution_request(query,docs)
        assert result.doc_ids=={'north'} and not result.needs_clarification
    assert not resolve_institution_request('HS cần bao nhiêu tín chỉ?',docs).doc_ids
    docs.append(document('duplicate','TRƯỜNG ĐẠI HỌC SAO BẮC PHÍA NAM'))
    assert resolve_institution_request('dhsb pn cần bao nhiêu tín chỉ?',docs).doc_ids=={'north','duplicate'}
    docs[-1]=document('other','TRƯỜNG ĐẠI HỌC SÔNG BẠC PHÍA NAM')
    assert resolve_institution_request('dhsb pn cần bao nhiêu tín chỉ?',docs).needs_clarification


@pytest.fixture
def literal_locator_sources(schools):
    import copy,json
    docs=copy.deepcopy(schools)
    docs[0]['items'] += [
        {'doc_id':'north','chunk_id':'article','page':8,'content':
         'Điều 27. Điều kiện bảo trì thiết bị\nCác yêu cầu được nêu ở đây.','metadata':{}},
        {'doc_id':'north','chunk_id':'subheading','page':9,'content':
         '2. Điều kiện, hình thức làm đồ án, khóa luận:\nĐiểm tích lũy là một điều kiện.','metadata':{}},
        {'doc_id':'north','chunk_id':'mapping','page':10,'content_type':'table',
         'content':json.dumps({'scope':'Controlled','headers':['Điểm chữ','Khoảng điểm'],
                              'rows':[['X','7,1–8,2']]},ensure_ascii=False),'metadata':{}}]
    docs[1]['items'] += [{'doc_id':'west','chunk_id':'other','page':8,'content':
        'Điều 27. Đăng ký môn học\nMột chủ đề khác.','metadata':{}}]
    return docs


def test_named_prose_mapping_requires_printed_lead_in_and_keeps_duplicate_owners(schools):
    import copy
    from campusai.retrieval.source_scope import explicit_source_documents
    docs=copy.deepcopy(schools)
    text=('3. Thiết bị được phân nhóm\n'
          'theo trạng thái an toàn trong danh sách sau.\n'
          'a) Phân loại có nhãn, bao gồm:\n'
          'X+: Đạt mức kiểm định nâng cao;\n'
          'X: Đạt mức kiểm định cơ bản;\n')
    item={'doc_id':'north','page':12,'content':text,'metadata':{}}
    docs[0]['items'].append(item)
    question='Theo bảng trạng thái an toàn trang 12, ký hiệu X+ nghĩa là gì?'
    assert explicit_source_documents(question,docs)=={'north'}
    # Neither a value, an inferred heading nor a generic word can identify
    # an owner when the actual printed field is absent.
    for other in [question.replace('trạng thái an toàn','số hiệu thiết bị'),
                  question.replace('trang 12','trang 11'),
                  question.replace('trang 12',''),
                  'Bảng trạng thái an toàn trang 12 có mức kiểm định cơ bản không?']:
        result=explicit_source_documents(other,docs)
        assert result==({'north'} if other.startswith('Bảng trạng thái') else set())
    for replacement in [text.replace('trạng thái an toàn','đặc điểm vận hành'),
                        text.replace('X: Đạt mức kiểm định cơ bản;',''),
                        text.replace('a) Phân loại có nhãn, bao gồm:','a) Đây là ví dụ.'),
                        text.replace('X: Đạt mức','4. Mục khác\nX: Đạt mức')]:
        item['content']=replacement
        item['metadata']['heading_path']='trạng thái an toàn'
        assert not explicit_source_documents(question,docs)
    item['content']=text
    docs[1]['items'].append({**item,'doc_id':'west'})
    assert explicit_source_documents(question,docs)=={'north','west'}
    assert not resolve_institution_request(question,docs).doc_ids


@pytest.mark.parametrize('question',[
    'Điều 27 quy định thế nào về bảo trì thiết bị?',
    'Trang 8 Điều 27 quy định thế nào về bảo trì thiết bị?',
    'Từ điều kiện đồ án trang 9, yêu cầu điểm là gì?',
    'Trang 10 trong bảng điểm chữ, mức X là gì?',
])
def test_explicit_page_article_and_literal_title_identify_source(literal_locator_sources,question):
    request=resolve_institution_request(question,literal_locator_sources)
    assert request.doc_ids=={'north'} and not request.needs_clarification


def test_locator_requires_every_explicit_coordinate_and_a_meaningful_printed_title(literal_locator_sources):
    from campusai.retrieval.source_scope import explicit_source_documents
    for question in ['Điều 27 có quy định gì?','Trang 8 có gì?',
                     'Trang 10 Điều 27 nói gì về bảo trì thiết bị?',
                     'Trang 9 có bảng điểm chữ không?',
                     'Trang 1-999999999 bảng điểm chữ thế nào?',
                     'Trang 0 bảng điểm chữ là gì?']:
        assert not explicit_source_documents(question,literal_locator_sources)


def test_locator_does_not_trust_metadata_or_resolve_unread_competing_sources(literal_locator_sources):
    from campusai.retrieval.source_scope import explicit_source_documents
    docs=literal_locator_sources
    docs[0]['items'][1]['content']='Ordinary unrelated body.'
    docs[0]['items'][1]['metadata']={'heading_path':['Điều 27. Điều kiện bảo trì thiết bị']}
    assert not explicit_source_documents('Điều 27 nói gì về bảo trì thiết bị?',docs)
    docs[1]['items'][0]['metadata']['coverage_complete']=False
    assert not explicit_source_documents('Trang 10 trong bảng điểm chữ, mức X là gì?',docs)


def test_locator_preserves_ambiguous_owners_and_explicit_school_priority(literal_locator_sources):
    import copy
    docs=literal_locator_sources
    query='Trang 10 trong bảng điểm chữ, mức X là gì?'
    duplicate=copy.deepcopy(docs[0]['items'][-1]);duplicate['doc_id']='west'
    docs[1]['items'].append(duplicate)
    assert resolve_institution_request(query,docs).needs_clarification
    unknown=resolve_institution_request('Trường Đại học Mây Trắng '+query,docs)
    assert unknown.unknown_name and not unknown.doc_ids
    selected=resolve_institution_request('WIM: Điều 27 quy định bảo trì thiết bị ra sao?',docs)
    assert selected.doc_ids=={'west'}  # A locator never overrides a named owner.


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


@pytest.mark.parametrize('question', [
    'Theo quy chế QRSU, nghiên cứu sinh báo cáo tiến độ ở đâu?',
    'QRSU yêu cầu tối thiểu bao nhiêu tín chỉ?',
    'qrsu yêu cầu tối thiểu bao nhiêu tín chỉ?',
    'Trong sổ tay qrsu, lớp học phần được mở lúc nào?',
    'Tại QRSU, nghiên cứu sinh phải báo cáo ra sao?',
    'tại qrsu, nghiên cứu sinh phải báo cáo ra sao?',
    'Trên trang PDF 12 QRSU: hội đồng cấp Đại học gồm bao nhiêu thành viên?',
    'ở trang 12 qrsu: quy định học tập thế nào?',
])
def test_embedded_or_leading_unfamiliar_school_alias_reaches_existing_verifier(schools,alias_service,question):
    from campusai.retrieval.institution_scope import unresolved_institution_reference
    assert unresolved_institution_reference(question,schools).casefold()=='qrsu'
    service,model,_,_=alias_service({'status':'confirmed','candidate_id':'c0','match_type':'established_alias'})
    result=service._institution_request(question,schools,[])
    assert result.doc_ids=={'north'} and not result.needs_clarification
    assert 'qrsu' not in result.question.casefold() and 'SAO BẮC' in result.question
    assert len(model.calls)==1
    # Alias verification gets the reference and authorized candidate names,
    # never an opportunity to answer the policy question from outside sources.
    assert question not in model.calls[0][0]


@pytest.mark.parametrize('word',['hai','three','both','all','mot','muoi','one'])
def test_quantity_in_known_school_question_is_not_an_unknown_institution(schools,alias_service,word):
    from campusai.retrieval.institution_scope import unresolved_institution_reference
    question=f'Sao Bắc quy định tổng số tuần của {word} học kỳ chính là bao nhiêu?'
    assert not unresolved_institution_reference(question,schools)
    service,model,_,_=alias_service({'status':'unknown','candidate_id':'none','match_type':'none'})
    result=service._institution_request(question,schools,[])
    assert result.doc_ids=={'north'} and not result.needs_clarification
    assert not model.calls


@pytest.mark.parametrize('term',['NCS','NCKH','CTDT','JSON','CPU'])
def test_academic_role_or_technical_term_does_not_become_school_alias(schools,term):
    from campusai.retrieval.institution_scope import unresolved_institution_reference
    assert not unresolved_institution_reference(f'{term} yêu cầu những điều kiện gì ở Sao Bắc?',schools)


def test_degree_level_is_not_a_school_name_but_a_real_capitalized_name_is(schools):
    question='Hội đồng cấp Đại học gồm bao nhiêu thành viên ở Sao Bắc?'
    result=resolve_institution_request(question,schools)
    assert result.doc_ids=={'north'} and not result.needs_clarification
    unknown=resolve_institution_request('Hội đồng cấp Đại học Mây Trắng gồm mấy người?',schools)
    assert unknown.needs_clarification and unknown.unknown_name


@pytest.mark.parametrize('question,expected',[
    ('Tại TRƯỜNG ĐẠI HỌC SAO BẮC, nghiên cứu sinh phải báo cáo ra sao?','north'),
    ('Ở WESTERN INSTITUTE OF METEOROLOGY, quy định học tập thế nào?','west'),
])
def test_words_of_recognized_uppercase_name_stay_recognized_after_location_prefix(schools,question,expected):
    request=resolve_institution_request(question,schools)
    assert request.doc_ids=={expected} and not request.needs_clarification


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
const pendingUser={role:'user',text:'Eligibility at North Star',scopeKey:key,failed:true};
messages.push(pendingUser,{role:'assistant',scopeKey:key,failed:true,answer:{answer:'Unverified threshold999'}});
rememberQuestion(key,pendingUser,{context_question:'Eligibility at North Star',partial:true});
assert(conversationHistory(key).some(turn=>turn.role==='user'&&turn.content==='Eligibility at North Star'));
assert(!conversationHistory(key).some(turn=>turn.content.includes('Unverified threshold999')));
const fresh={role:'user',text:'Explain transactions',scopeKey:key};
rememberQuestion(key,fresh,{context_question:'Explain transactions'});
assert.equal(topicMemory.get(key),'Explain transactions');
renderConversation=()=>{};renderSources=()=>{};updateComposer=()=>{};
resetChat();assert.equal(topicMemory.size,0);assert.equal(messages.length,0);
`,context);
'''
    result=subprocess.run(['node','-e',script],text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr


@pytest.fixture
def named_pdf_web(tmp_path):
    """Routing-only WSGI fixture: valid local PDFs/indexes, no model inference."""
    import hashlib,io,json
    import pymupdf as fitz
    from types import SimpleNamespace
    from campusai.schemas import Document,Chunk
    from campusai.documents.registry import DocumentRegistry
    from campusai.retrieval.index_builder import build_document_indexes
    from campusai.observability import MetricsRegistry
    from campusai.rag.grounding import GroundedAnswer
    from campusai.api import CampusAIApplication
    from campusai.web import make_wsgi_app
    store=tmp_path/'store';index=tmp_path/'index';registry=DocumentRegistry(store/'registry.json')
    ids={};calls=[]
    for number,name in enumerate(['Alpha.pdf','Beta.pdf','Gamma.pdf'],1):
        text=f'Controlled source {number}: deadline {number+10} August 2025.'
        with fitz.open() as pdf:
            pdf.new_page().insert_text((40,50),text);raw=pdf.tobytes()
        ident=hashlib.sha256(raw).hexdigest();ids[name]=ident
        path=store/'uploads'/ident/name;path.parent.mkdir(parents=True);path.write_bytes(raw)
        document=Document(ident,str(path),1,language='en',metadata={'text_coverage_version':4,
            'coverage_complete':True,'unread_pages':[],'readable_pages':[1]},
            chunks=[Chunk(ident+'_one',ident,1,text)])
        registry.add(document);build_document_indexes(document,index)
    def ask(question,**options):
        calls.append((question,options))
        return GroundedAnswer('Routing-only fixture; no generated answer.',(), 'low',True,
                              reason='insufficient_evidence',evidence_status='not_found')
    service=SimpleNamespace(ask=ask,metrics=MetricsRegistry(),last_cache_hit=False,
        reset_request_state=lambda:None,retriever=SimpleNamespace(index_root=index))
    application=CampusAIApplication(service,ingestion_defaults={'store_dir':store,'index_dir':index})
    def request(question,*,streaming=False,selected=None,authorized=None,history=None):
        web=make_wsgi_app(application,enable_query_streaming=streaming)
        payload={'question':question,'doc_ids':[ids[name] for name in selected or ids],'language':'en'}
        if history is not None:payload['history']=history
        body=json.dumps(payload).encode();response={}
        environ={'REQUEST_METHOD':'POST','PATH_INFO':'/api/query','CONTENT_TYPE':'application/json',
            'CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body),
            'HTTP_ACCEPT':'application/x-ndjson' if streaming else 'application/json'}
        if authorized is not None:environ['campusai.authorized_doc_ids']=[ids[name] for name in authorized]
        output=b''.join(web(environ,lambda status,headers:response.update(status=status,headers=headers)))
        assert response['status'].startswith('200'),output
        return json.loads(output)
    request.application=application
    return request,ids,calls


@pytest.mark.parametrize('streaming',[False,True])
@pytest.mark.parametrize('question,expected',[
    ('What is the deadline in Alpha.pdf?',{'Alpha.pdf'}),
    ('Theo file Alpha.pdf, hạn nộp là khi nào?',{'Alpha.pdf'}),
    ('According to Beta.pdf, what deadline applies?',{'Beta.pdf'}),
    ('Trong Alpha.pdf và Beta.pdf có mốc nào?',{'Alpha.pdf','Beta.pdf'}),
    ('Compare Alpha.pdf and Beta.pdf',{'Alpha.pdf','Beta.pdf'}),
    ('Does the manual mention Beta.pdf?',{'Alpha.pdf','Beta.pdf','Gamma.pdf'}),
])
def test_web_content_questions_use_only_explicit_named_pdf_scope(named_pdf_web,streaming,question,expected):
    request,ids,calls=named_pdf_web
    request(question,streaming=streaming)
    assert len(calls)==1
    assert set(calls[0][1]['doc_ids'])=={ids[name] for name in expected}


@pytest.mark.parametrize('question',[
    'What is the deadline in Missing.pdf?', 'Do not use Alpha.pdf', "Don't use Alpha.pdf", 'Don’t use Alpha.pdf',
    'Compare Alpha.pdf and Missing.pdf',
])
def test_unknown_or_negative_pdf_scope_clarifies_before_retrieval(named_pdf_web,question):
    request,ids,calls=named_pdf_web
    result=request(question)
    assert not calls and result['answer']['abstained']
    assert result['answer']['abstention_reason']=='ambiguous_question'


def test_pdf_scope_cannot_expand_authorized_sources_or_lose_current_followup_name(named_pdf_web):
    request,ids,calls=named_pdf_web
    result=request('What is the deadline in Gamma.pdf?',selected=['Alpha.pdf','Beta.pdf'],authorized=['Alpha.pdf','Beta.pdf'])
    assert result['answer']['abstained'] and not calls
    history=[{'role':'user','content':'What is the deadline in Alpha.pdf?'},
             {'role':'assistant','content':'Previous verified answer.'}]
    request('Còn file Beta.pdf thì sao?',history=history)
    assert calls[-1][1]['doc_ids']==[ids['Beta.pdf']]


@pytest.mark.parametrize('target',['Alpha.pdf','Beta.pdf'])
@pytest.mark.parametrize('streaming',[False,True])
def test_grounded_web_answer_cannot_use_another_selected_pdf_for_a_named_source(named_pdf_web,target,streaming):
    """Scripted unit model: provenance check, not native-model quality evidence."""
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.retrieval.hybrid import HybridRetriever
    request,ids,calls=named_pdf_web
    number=1 if target=='Alpha.pdf' else 2
    class Model:
        model='scripted-provenance-unit'
        def __init__(self):self.calls=0
        def generate_json(self,*a,**k):
            self.calls+=1
            return {'answer':f'The deadline is {number+10} August 2025.','confidence':'high','abstained':False,
                'citations':[{'chunk_id':ids[target]+'_one','doc_id':ids[target],'page':1,'page_range':[1,1],
                              'quote':f'Controlled source {number}: deadline {number+10} August 2025.'}]}
    model=Model();application=request.application
    service=CampusAIQueryService(HybridRetriever(application.ingestion_defaults['index_dir']),GroundedAnswerGenerator(model))
    application.query_service=service
    try:
        response=request('What deadline is stated in Alpha.pdf?',streaming=streaming)
        assert model.calls==1
        if target=='Alpha.pdf':
            assert not response['answer']['abstained']
            assert {citation['doc_id'] for citation in response['answer']['citations']}=={ids['Alpha.pdf']}
        else:
            assert response['answer']['abstained'] and not response['answer']['citations']
    finally:service.close()


def test_chat_clarification_editing_restores_exact_scope_without_sending_and_renders_correct_notices():
    import shutil,subprocess
    if not shutil.which('node'):pytest.skip('Node required for frontend behavior checks')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();let sends=0,notifications=0;
const $=key=>{if(!nodes.has(key))nodes.set(key,{value:'',textContent:'',style:{},focus(){this.focused=true},dispatchEvent(){},setAttribute(){}});return nodes.get(key)};
const state={busy:false,aiConfigured:true,documents:[{doc_id:'a',ready:true},{doc_id:'b',ready:true}],selected:new Set(['b']),replyLanguage:'vi'};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const context=vm.createContext({assert,$,state,esc,icon:()=>'',hasPendingAttachments:()=>false,readySelected:()=>state.documents.filter(doc=>doc.ready&&state.selected.has(doc.doc_id)),Event:class{constructor(type){this.type=type}},notify:()=>notifications++,post:()=>{sends++;throw Error('must not submit')},postQuery:()=>{sends++;throw Error('must not submit')}});
vm.runInContext(fs.readFileSync('src/campusai/ui/features/chat.js','utf8').replace(/^import .*;\r?$/gm,'').replace(/^export /gm,''),context);
vm.runInContext(`
messages.push({role:'assistant',error:'Failure',question:'Original user question',docIds:['a'],language:'en'});
editQuestion(0);
assert.equal($('#question').value,'Original user question');assert.equal(state.replyLanguage,'en');
assert.deepEqual([...state.selected],['a']);assert.equal($('#question').focused,true);
state.documents=[{doc_id:'b',ready:true}];editQuestion(0);
assert.equal(state.selected.size,0);assert($('#query-status').textContent.includes('Nguồn cũ'));
state.busy=true;$('#question').value='Keep draft';editQuestion(0);assert.equal($('#question').value,'Keep draft');state.busy=false;
const ambiguous={role:'assistant',answer:{answer:'Choose a PDF',abstained:true,documentInfo:{kind:'page_count'}},question:'Original',docIds:['b'],time:'12:00'};
const html=renderMessage(ambiguous,1);assert(!html.includes('<div class="answer-note"></div>'));
assert(html.includes('data-edit-question="1"')&&html.includes('data-clarify-scope'));
const partial=renderMessage({role:'assistant',answer:{answer:'Checked answer',abstained:false,citations:[]},coverage:{complete:false,documents:[{unread_pages:[5,6]}]}},2);
assert(partial.includes('Còn 2 trang đang xử lý'));assert(!partial.includes('trang ảnh'));
assert(note({abstained:true,abstention_reason:'conflicting_evidence'}).includes('mâu thuẫn'));
assert(!safeMarkdown('<img src=x onerror=alert(1)>').includes('<img'));
`,context);
assert.equal(sends,0);assert.equal(notifications,2);
'''
    result=subprocess.run(['node','-e',script],text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr


def test_library_heartbeat_does_not_replace_controls_when_only_job_progress_changes():
    import shutil,subprocess
    if not shutil.which('node'):pytest.skip('Node required for frontend behavior checks')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const state={documents:[{doc_id:'a',ready:true}],jobs:[],limits:{max_mb:50,max_pages:218},uploadAvailable:true,loading:false,error:'',selected:new Set(['a'])};
const next={documents:state.documents,jobs:[{state:'running',progress:.5}],limits:state.limits,upload_available:true,runtime:{ai_configured:true}};
const context=vm.createContext({assert,state,icon:()=>'',request:async()=>next,$:()=>({textContent:''}),notify:()=>{}});
vm.runInContext(fs.readFileSync('src/campusai/ui/features/documents.js','utf8').replace(/^import .*;\r?$/gm,'').replace(/^export /gm,''),context);
vm.runInContext('globalThis.full=0;globalThis.jobsOnly=0;renderAll=()=>full++;renderJobs=()=>jobsOnly++;schedulePoll=()=>{};',context);
(async()=>{
 await vm.runInContext('refreshDocuments()',context);
 assert.equal(context.full,0);assert.equal(context.jobsOnly,1);assert(state.selected.has('a'));
 next.documents=[{doc_id:'a',ready:false}];await vm.runInContext('refreshDocuments()',context);
 assert.equal(context.full,1);assert.equal(state.selected.size,0);
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script],text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr


def test_pdf_thumbnail_is_small_cached_authorized_and_invalidated_on_source_change(named_pdf_web,monkeypatch):
    from campusai.web_documents import WebDocuments,WebError
    import pymupdf
    request,ids,_calls=named_pdf_web
    api=WebDocuments(request.application)
    reads=[];original=api.source_bytes
    def read(*args):
        reads.append(args[0]);return original(*args)
    monkeypatch.setattr(api,'source_bytes',read)
    image=api.thumbnail(ids['Alpha.pdf'],{})
    pix=pymupdf.Pixmap(image)
    assert image.startswith(b'\x89PNG') and 0<pix.width<=321 and 0<pix.height<=211
    assert api.thumbnail(ids['Alpha.pdf'],{})==image and len(reads)==1
    with pytest.raises(WebError) as denied:
        api.thumbnail(ids['Alpha.pdf'],{'campusai.authorized_doc_ids':[ids['Beta.pdf']]})
    assert denied.value.status==404 and len(reads)==1
    path=api.source(ids['Alpha.pdf'],{});data=path.read_bytes()
    path.write_bytes(data+b'changed source')
    with pytest.raises(WebError):api.thumbnail(ids['Alpha.pdf'],{})
    assert ids['Alpha.pdf'] not in api._thumbnail_cache
    path.write_bytes(data)
    assert api.thumbnail(ids['Alpha.pdf'],{}).startswith(b'\x89PNG')
    path.unlink()
    with pytest.raises(WebError):api.thumbnail(ids['Alpha.pdf'],{})


def test_thumbnail_route_uses_the_same_source_authorization(named_pdf_web):
    import json
    from campusai.web import make_wsgi_app
    request,ids,calls=named_pdf_web;web=make_wsgi_app(request.application)
    for allowed,status in [([ids['Alpha.pdf']],200),([ids['Beta.pdf']],404)]:
        response={}
        body=b''.join(web({'REQUEST_METHOD':'GET','PATH_INFO':f"/api/documents/{ids['Alpha.pdf']}/thumbnail",
                          'campusai.authorized_doc_ids':allowed},
                         lambda result,headers:response.update(status=result,headers=dict(headers))))
        assert response['status'].startswith(str(status))
        if status==200:
            assert response['headers']['Content-Type']=='image/png' and body.startswith(b'\x89PNG')
        else:assert not json.loads(body)['ok']
    assert not calls


def test_composer_tracks_uploads_two_batches_removal_errors_and_partial_readiness():
    import shutil,subprocess
    if not shutil.which('node'):pytest.skip('Node required for frontend upload behavior checks')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();let writes=0,routes=[],sent=0,queue=[];
const $=key=>{if(!nodes.has(key))nodes.set(key,{dataset:{},value:'',textContent:'',style:{},classList:{add(){},remove(){}},scrollLeft:0,
  get innerHTML(){return this.html||''},set innerHTML(value){this.html=value;if(key==='#composer-attachments')writes++},
  querySelectorAll:()=>[],focus(){},setAttribute(){}});return nodes.get(key)};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state={documents:[],jobs:[],selected:new Set(),limits:{max_mb:50,max_pages:218},uploadAvailable:true,loading:false,error:'',busy:false,aiConfigured:true};
let library={documents:[],jobs:[],limits:state.limits,upload_available:true,runtime:{ai_configured:true}};
const context=vm.createContext({assert,$,state,esc,icon:()=>'<svg></svg>',pdfIcon:()=>'<i>PDF</i>',bytes:()=>'',document:{activeElement:null},
  notify:()=>{},closeDialog:()=>{},route:tab=>routes.push(tab),toast:()=>{},errorText:()=> 'Upload failed',
  request:async()=>library,upload:()=>new Promise((resolve,reject)=>queue.push({resolve,reject})),post:()=>{sent++;throw Error('unexpected send')}});
vm.runInContext(fs.readFileSync('src/campusai/ui/features/documents.js','utf8').replace(/^import .*;\r?$/gm,'').replace(/^export /gm,''),context);
vm.runInContext('renderAll=()=>renderComposerAttachments();schedulePoll=()=>{};',context);
vm.runInContext(fs.readFileSync('src/campusai/ui/features/chat.js','utf8').replace(/^import .*;\r?$/gm,'').replace(/^export /gm,''),context);
$('#question').value='Keep my draft';
const execute=code=>vm.runInContext(code,context);
const cards=()=>($('#composer-attachments').innerHTML.match(/role="listitem"/g)||[]).length;
async function batch(start){
 const before=queue.length;
 execute(`chooseFiles(Array.from({length:5},(_,i)=>({name:'file-${start}-'+i+'.pdf',size:100})))`);
 const running=execute('submitUpload()');assert.equal(queue.length,before+5);
 assert(execute('hasPendingAttachments()'));execute('updateComposer()');assert($('#send').disabled);
 await execute("send('Must wait for attached PDFs')");assert.equal(sent,0);
 assert($('#composer-attachments').innerHTML.includes('spinner'));assert.equal($('#question').value,'Keep my draft');
 for(let i=0;i<5;i++){
  const id='d'+(start+i),job={job_id:'j'+id,document_id:id,name:'file-'+id+'.pdf',state:'queued',stage:'queued',created_at:start+i};
  library.jobs.push(job);queue[before+i].resolve({job});
 }
 await running;assert.equal(routes.at(-1),'assistant');
 library.documents=library.jobs.map(job=>({doc_id:job.document_id,name:job.name,ready:true,file_available:true,page_count:3,coverage_complete:true}));
 library.jobs=library.jobs.map(job=>({...job,state:'succeeded',stage:'done'}));
 await execute('refreshDocuments()');assert(!execute('hasPendingAttachments()'));
 execute('updateComposer()');assert(!$('#send').disabled);
}
(async()=>{
 await batch(0);assert.equal(cards(),5);await batch(5);assert.equal(cards(),10);assert.equal(state.selected.size,10);
 const stable=writes;execute('renderComposerAttachments()');assert.equal(writes,stable);
 execute("removeComposerAttachment('doc-d0')");assert.equal(cards(),9);assert.equal(state.documents.length,10);
 const before=queue.length;execute("chooseFiles([{name:'new.pdf',size:100}])");const running=execute('submitUpload()');
 const key=$('#composer-attachments').innerHTML.match(/data-attachment-remove="(upload-[^"]+)"/)[1];
 execute(`removeComposerAttachment('${key}')`);
 const job={job_id:'late',document_id:'late',name:'new.pdf',state:'running',stage:'ocr',created_at:100};library.jobs.push(job);
 queue[before].resolve({job});await running;await execute('refreshDocuments()');
 assert(!$('#composer-attachments').innerHTML.includes('new.pdf'));assert(!execute('hasPendingAttachments()'));
 library.documents.push({doc_id:'late',name:'new.pdf',ready:true,file_available:true,page_count:1});job.state='succeeded';
 await execute('refreshDocuments()');assert(!state.selected.has('late'));
 execute("chooseFiles([{name:'<bad>.pdf',size:100}])");const failed=execute('submitUpload()');queue.at(-1).reject(Error('network'));await failed;
 const html=$('#composer-attachments').innerHTML;assert(html.includes('is-error')&&html.includes('&lt;bad&gt;.pdf'));
 assert(!html.includes('spinner'));assert(!html.includes('<bad>'));assert(execute('hasPendingAttachments()'));
 const badKey=html.match(/data-attachment-remove="(upload-[^"]+)"/)[1];execute(`removeComposerAttachment('${badKey}')`);
 assert(!execute('hasPendingAttachments()'));
 library.documents[1]={...library.documents[1],coverage_complete:false};
 library.jobs.push({job_id:'partial',document_id:'d1',name:'partial.pdf',state:'running',stage:'ocr',created_at:200});
 await execute('refreshDocuments()');assert($('#composer-attachments').innerHTML.includes('Hỏi được phần đã đọc'));
 assert($('#composer-attachments').innerHTML.includes('spinner'));assert(!execute('hasPendingAttachments()'));
 library.jobs.at(-1).state='review_required';await execute('refreshDocuments()');
 assert(!$('#composer-attachments').innerHTML.includes('spinner'));
 const broken={job_id:'broken',document_id:'broken',name:'broken.pdf',state:'running',stage:'parsing',created_at:300,retryable:true};
 library.jobs.push(broken);await execute('refreshDocuments()');assert(execute('hasPendingAttachments()'));
 broken.state='failed';broken.stage='failed';await execute('refreshDocuments()');
 assert(!$('#composer-attachments').innerHTML.includes('spinner'));
 assert($('#composer-attachments').innerHTML.includes('data-job-retry="broken"'));
 execute("removeComposerAttachment('job-broken')");assert(!execute('hasPendingAttachments()'));
 assert.equal(sent,0);assert.equal($('#question').value,'Keep my draft');
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script],text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr
