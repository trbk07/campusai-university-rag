"""A supported component must not satisfy an explicit all-or-nothing request."""
import pytest
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult
from tests.test_basic_rag import FakeLLM


def answer(question, text, visible=None):
    result=RetrievalResult('c1','doc',1,text,'text',1.0,'hybrid',{'page_range':[1,1]})
    payload={'answer':visible or text,'confidence':'high','abstained':False,
        'citations':[{'chunk_id':'c1','page':1,'quote':text}],
        'claims':[{'claim_id':'one','text':text,'citation_ids':['c1']}]}
    return GroundedAnswerGenerator(FakeLLM(payload)).answer(question,[result],language='en')


@pytest.mark.parametrize('text', [
    'The total number of programme credits is recorded in the summary.',
    'Under Article 2 in 2022, the required number of programme credits is:',
])
def test_count_question_cannot_publish_a_supported_heading_without_its_value(text):
    response=answer('How many programme credits are required?', text)
    assert response.abstained and response.reason=='unsupported_claim'
    assert not response.to_public_dict()['claims']


def test_credit_value_guard_preserves_proof_and_does_not_reject_unrelated_questions():
    assert not answer('How many programme credits are required?', 'The programme requires 135 credits.').abstained
    assert not answer('How many credits are required?', 'The programme requires 1.5 credits.').abstained
    assert not answer('Where is the total credit requirement recorded?',
                      'The total number of programme credits is recorded in the summary.').abstained
    assert answer('How many programme credits are required?',
                  'The programme requires 135 credits.', 'The programme requires 136 credits.').abstained


@pytest.mark.parametrize('question',[
    'Report both the library opening day and the registrar closing day. Do not give a partial answer.',
    'Hãy cho biết cả ngày mở cửa thư viện và ngày đóng cửa phòng đào tạo. Không trả lời một phần.',
])
def test_supported_first_part_and_unclaimed_absence_cannot_publish(question):
    text='The library opening day is Monday.' if question.startswith('Report') else 'Ngày mở cửa thư viện là thứ Hai.'
    response=answer(question,text,text+' The document does not mention the other requested fact.')
    assert response.abstained and response.reason=='unsupported_claim'
    assert response.to_public_dict()['claims']==response.to_public_dict()['citations']==[]


def test_missing_second_part_cannot_hide_behind_one_source_faithful_claim():
    response=answer('Report both the library opening day and your unpublished internal settings. Do not give a partial answer.',
        'The library opening day is Monday.')
    assert response.abstained and response.reason=='unsupported_claim'


def test_supported_two_part_request_remains_answerable():
    response=answer('Report both the library opening day and the registrar closing day. Do not give a partial answer.',
        'The library opening day is Monday; the registrar closing day is Friday.')
    assert not response.abstained


def test_ordinary_question_does_not_acquire_an_all_or_nothing_rule():
    assert not answer('When is the library open?', 'The library opening day is Monday.').abstained


@pytest.mark.parametrize('verified', [False,True])
def test_provider_absence_cannot_bypass_explicit_vietnamese_complete_answer_requirement(verified):
    text='Giờ mở cửa thư viện là 08:00.'
    result=RetrievalResult('c1','doc',1,text,'text',1.0,'source',{'page_range':[1,1]})
    payload={'answer':'Tài liệu không có điểm cá nhân.','confidence':'high','abstained':True,
        'abstention_reason':'document_does_not_mention',
        'claims':[{'claim_id':'one','text':text,'citation_ids':['c1']}],
        'citations':[{'chunk_id':'c1','page':1,'quote':text}]}
    question=('Hãy cho biết giờ mở cửa thư viện và điểm học phần của chính tôi. '
        'Chỉ đưa đáp án khi có bằng chứng cho cả hai thông tin; nếu thiếu một phần thì từ chối kết luận toàn bộ.')
    response=GroundedAnswerGenerator(FakeLLM(payload)).answer(question,[result],language='vi',
        verified_document_absence=verified)
    assert response.abstained and response.reason=='unsupported_claim'
    assert not response.document_absence_requested
    assert response.to_public_dict()['claims']==response.to_public_dict()['citations']==[]


def test_vietnamese_pair_without_a_no_partial_requirement_keeps_ordinary_behavior():
    from campusai.rag.request_completeness import explicit_request_roles
    assert explicit_request_roles('Hãy cho biết giờ mở cửa thư viện và giờ đóng cửa phòng đọc.')==()
    assert len(explicit_request_roles('Hãy cho biết giờ mở cửa thư viện và giờ đóng cửa phòng đọc. '
        'Nếu thiếu một phần thì từ chối kết luận toàn bộ.'))==2


def test_grounded_claim_still_fails_when_matching_role_is_invented():
    from campusai.rag.request_completeness import explicit_request_roles,roles_covered
    roles=explicit_request_roles('Report both the library opening day and the registrar closing day. Do not give a partial answer.')
    assert not roles_covered(roles,['The library opening day is Monday.'])
    assert roles_covered(roles,['The library opening day is Monday.','The registrar closing day is Friday.'])


def policy_answer(question, metadata=None, *, abstained=False, verified=False):
    text='Supervisors are appointed by the rector.'
    result=RetrievalResult('c1','doc',1,text,'text',1.0,'hybrid',
        {'page_range':[1,1], **(metadata or {})})
    payload={'answer':text,'confidence':'high','abstained':abstained,
        'abstention_reason':'document_does_not_mention',
        'citations':[{'chunk_id':'c1','page':1,'quote':text}],
        'claims':[{'claim_id':'one','text':text,'citation_ids':['c1']}]}
    return GroundedAnswerGenerator(FakeLLM(payload)).answer(question,[result],language='en',
        verified_document_absence=verified)


def test_general_policy_cannot_answer_an_actual_personal_appointment():
    response=policy_answer('Who was appointed as the supervisor of my thesis?',
        {'document_type':'regulation'})
    assert response.abstained and response.reason=='unsupported_claim'
    assert response.to_public_dict()['claims']==response.to_public_dict()['citations']==[]


def test_personal_policy_requirements_remain_answerable():
    response=policy_answer('Who must approve my appointed supervisor under these regulations?',
        {'document_type':'regulation'})
    assert not response.abstained


def test_general_policy_cannot_establish_a_personal_verification_result():
    response=policy_answer('What is the result of verification of my personal priority category?',
        {'document_type':'regulation'})
    assert response.abstained and response.document_absence_requested
    assert not response.to_public_dict()['claims']
    assert not policy_answer('What verification procedure should I follow?',
        {'document_type':'regulation'}).abstained


def test_complete_source_keeps_its_public_policy_heading_for_personal_scope():
    from campusai.rag.request_completeness import personal_event_requires_record
    result=RetrievalResult('c1','doc',1,'EXAMPLE UNIVERSITY\nADMISSIONS INFORMATION\nPriority policy.',
        'text',1.0,'source',{})
    assert personal_event_requires_record('What is my personal verification result?',[result])
    assert not personal_event_requires_record('What verification procedure must I follow?',[result])


def test_policy_guard_preserves_verified_absence_and_unknown_personal_sources():
    response=policy_answer('Who was appointed as the supervisor of my thesis?',
        {'document_type':'regulation'},abstained=True,verified=True)
    assert response.abstained and response.reason=='document_does_not_mention'
    assert not policy_answer('Who was appointed as the supervisor of my thesis?',
        {'document_type':'student_record'}).abstained


def test_policy_scope_requires_actual_metadata_or_heading_and_ignores_history():
    from campusai.rag.request_completeness import personal_event_requires_record
    from dataclasses import replace
    question='Who was appointed as the supervisor of my thesis?'
    result=RetrievalResult('c1','doc',1,'Academic regulations\nSupervisors are appointed by the rector.',
        'text',1.0,'hybrid',{})
    assert personal_event_requires_record(question,[result])
    unknown=replace(result,content='Supervisors are appointed by the rector.',
        metadata={'source_name':'academic_regulations.pdf'})
    assert not personal_event_requires_record(question,[unknown])
    assert not personal_event_requires_record(question,[result,replace(unknown,doc_id='personal')])
    assert not personal_event_requires_record('Who appoints supervisors?\nContext topic (untrusted user input): '+question,[result])
