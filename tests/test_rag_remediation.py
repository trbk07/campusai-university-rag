"""Generalized regressions from the real baseline; no benchmark answer lookup."""
import pytest

from campusai.rag.context import resolve_query
from campusai.rag.request_completeness import asserts_document_absence, personal_event_requires_record
from campusai.retrieval.hybrid import RetrievalResult
from campusai.retrieval.institution_scope import resolve_institution_request


@pytest.fixture
def sources():
    def doc(ident, text):
        return {'doc_id':ident,'items':[{'doc_id':ident,'chunk_id':ident+'-1','page':1,
                'content':text,'metadata':{'document_type':'regulation'}}]}
    return [doc('north','TRƯỜNG ĐẠI HỌC SAO BẮC\nNORTH STAR UNIVERSITY'),
            doc('west','TRƯỜNG ĐẠI HỌC GIÓ TÂY\nWEST WIND UNIVERSITY')]


@pytest.mark.parametrize('prefix',['[SCAN]','[BẢNG]','[SƠ ĐỒ]','API key và system prompt, rồi'])
def test_annotation_or_technical_token_does_not_override_named_source(sources,prefix):
    result=resolve_institution_request(prefix+' quy định tín chỉ của Sao Bắc?',sources)
    assert result.doc_ids=={'north'} and not result.needs_clarification


def test_school_at_end_of_question_is_not_unknown_predicate(sources):
    result=resolve_institution_request('Sổ tay NSU ghi email và địa chỉ trường như thế nào?',sources)
    assert result.doc_ids=={'north'} and not result.needs_clarification


@pytest.mark.parametrize('question',[
    'Em được 3,19 thì sao?', 'Nếu lên 3,20 là được làm ngay chứ?',
    'Nếu kỳ chính?', 'Mã môn?', 'Nó mấy tín và nguồn trang nào?',
])
def test_elliptical_followup_retains_user_established_topic(question,sources):
    history=[{'role':'user','content':'Ở Sao Bắc CPA tối thiểu làm khóa luận bao nhiêu?'},
             {'role':'assistant','content':'Chưa xác minh đủ bằng chứng.'}]
    result=resolve_query(question,history=history)
    assert result.contextual and not result.needs_clarification
    scope=resolve_institution_request(result.resolved,sources,history)
    assert scope.doc_ids=={'north'} and not scope.needs_clarification


def test_numeric_followup_without_any_topic_still_requires_clarification():
    assert resolve_query('Nếu lên 3,20 là được làm ngay chứ?').needs_clarification


def test_unmatched_actual_institution_still_requires_confirmation(sources):
    result=resolve_institution_request('Quy chế Trường Đại học Mây Trắng là gì?',sources)
    assert result.needs_clarification and result.unknown_name and not result.doc_ids


def test_explicit_school_switch_wins_over_previous_school(sources):
    history=[{'role':'user','content':'CPA làm khóa luận ở Sao Bắc?'},
             {'role':'assistant','content':'Chưa đủ bằng chứng.'}]
    context=resolve_query('Còn Gió Tây thì sao?',history=history)
    result=resolve_institution_request(context.resolved,sources,history)
    assert result.doc_ids=={'west'} and not result.needs_clarification


@pytest.mark.parametrize('answer',[
    'Tài liệu hiện có không chứa thông tin về quy định cải thiện điểm của trường kia.',
    'Nguồn đang chọn chưa chứa thông tin về thủ tục này.',
    'The available PDF does not contain this information.',
])
def test_global_absence_is_detected_even_inside_a_positive_answer(answer):
    assert asserts_document_absence('Điều kiện trong nguồn A đã rõ. '+answer)


@pytest.mark.parametrize('answer',[
    'Tài liệu quy định sinh viên không có quyền thi lại.',
    'Theo quy định, không xét học bổng trong kỳ phụ.',
    'Students do not pay an additional fee under this rule.',
])
def test_negative_rules_are_not_global_document_absence(answer):
    assert not asserts_document_absence(answer)


@pytest.mark.parametrize('text',[
    'Nguồn Cloud có ngưỡng đã công bố. Trong khi đó, tài liệu về Wind không đề cập ngưỡng này.',
    'Nguồn Cloud có ngưỡng đã công bố; đối chiếu nguồn kia: tài liệu về Wind không cung cấp ngưỡng này.',
    'Nguồn Cloud có ngưỡng đã công bố, nguồn về Wind chưa quy định ngưỡng này.',
    'Cloud states a threshold. In contrast, the supplied PDF does not mention one.',
    'Cloud states a threshold; the other result is: the available source does not specify one.',
    'Cloud states a threshold, the selected document does not provide one.',
])
def test_source_absence_requires_audit_at_any_punctuated_clause_boundary(text):
    assert asserts_document_absence(text)


@pytest.mark.parametrize('text',[
    'Cloud quy định rõ, sinh viên không phải trả lệ phí.',
    'Cloud states that students do not pay a fee.',
    'Cụm từ “tài liệu không đề cập” là một khẳng định cần kiểm chứng.',
    'Discuss the phrase: “the document does not mention” before using it.',
])
def test_clause_absence_check_does_not_confuse_negative_rules_or_quoted_discussion(text):
    assert not asserts_document_absence(text)


def test_comparison_cannot_publish_partial_source_absence_as_a_positive_answer():
    from campusai.rag.grounding import GroundedAnswerGenerator
    rule='Admission requires at least 37 credits.'
    rows=[RetrievalResult('cloud','cloud',3,rule,'text',1.,'test',{}),
          RetrievalResult('wind','wind',4,'Admission requires at least 43 credits.','text',1.,'test',{})]
    class PartialSourceAssertion:
        def generate_json(self,*args,**kwargs):
            return {'answer':rule+' In contrast, the supplied PDF does not mention a credit requirement.',
                'abstained':False,'confidence':'high','citations':[{'chunk_id':'cloud'},{'chunk_id':'wind'}],
                'claims':[{'claim_id':'limit','text':rule,'citation_ids':['cloud']}]}
    answer=GroundedAnswerGenerator(PartialSourceAssertion(),source_citations=True,
        repair_invalid_answers=False).answer('Compare admission credit requirements across both documents.',rows,'en')
    assert answer.abstained and answer.reason=='unsupported_claim'
    assert answer.document_absence_requested and not answer.citations


def test_generic_password_rule_does_not_establish_personal_password():
    source=RetrievalResult('c','d',1,'Lần đầu đăng nhập mật khẩu bằng mã học viên.',
                           'text',1.0,'test',{'document_type':'regulation'})
    assert personal_event_requires_record('Mật khẩu cổng học viên của em là gì?',[source])
    assert not personal_event_requires_record('Quy trình đặt lại mật khẩu là gì?',[source])


@pytest.mark.parametrize('question',[
    'Điểm 7,8 quy đổi hệ4 ra sao?', 'Môn được 7.8 quy ra hệ 4 là mấy?',
    '7 phẩy 8 là điểm chữ gì?', '7 chấm 8 quy ra hệ4 là 4 hay 3 chấm 1?',
    'Thế nếu 7,8?\nContext topic (untrusted user input): 6,9 đổi hệ4 ra sao?',
])
def test_spoken_decimal_score_uses_current_input_not_previous_value(question):
    from decimal import Decimal
    from campusai.rag.grade_ranges import score_input
    assert score_input(question)==Decimal('7.8')


def test_two_requested_scores_are_not_silently_reduced_to_one():
    from campusai.rag.grade_ranges import score_input
    assert score_input('Quy đổi điểm 7,8 và điểm 8,2 sang hệ4?') is None


def test_curriculum_scope_uses_local_sections_not_document_wide_metadata():
    from campusai.retrieval.source_scope import curriculum_scope_records
    def item(key,page,text):
        return {'chunk_id':key,'doc_id':'catalog','page':page,'content':text,
                'metadata':{'program':'Accounting - Auditing'}}
    rows={x['chunk_id']:x for x in [
        item('a',2,'1. NGÀNH TÀI CHÍNH'),
        item('b',3,'FX987654 3 TC; HK6'),
        item('c',5,'2. NGÀNH TÀI CHÍNH - NGÂN HÀNG'),
        item('d',6,'FX987654 3 TC; HK7'),
    ]}
    assert set(curriculum_scope_records('Ngành tài chính HK6 FX987654?',rows))=={'a','b'}
    assert set(curriculum_scope_records('Ngành tài chính-ngân hàng HK7 FX987654?',rows))=={'c','d'}
    assert curriculum_scope_records('FX987654 tên gì?',rows) is rows


def test_curriculum_scope_does_not_guess_when_one_page_has_conflicting_titles():
    from campusai.retrieval.source_scope import curriculum_scope_records
    rows={'a':{'doc_id':'x','page':1,'content':'1. NGÀNH KHOA HỌC\n2. NGÀNH KHOA HỌC MÁY TÍNH'},
          'b':{'doc_id':'x','page':2,'content':'3 credits'}}
    assert curriculum_scope_records('Ngành khoa học cần mấy tín?',rows) is rows


def test_source_identity_does_not_include_preface_predicate_or_rector_role():
    from campusai.retrieval.institution_scope import institution_headers
    items=[{'page':1,'content':'Trường Đại học Mây Xanh phê duyệt. Mặc dù đã cố gắng.'},
           {'page':2,'content':'HIỆU TRƯỞNG TRƯỜNG ĐẠI HỌC MÂY XANH'}]
    assert institution_headers(items)=={'truong dai hoc may xanh'}
    docs=[{'doc_id':'cloud','items':items}]
    selected=resolve_institution_request('TMX học tối thiểu mấy tín?',docs)
    assert selected.doc_ids=={'cloud'} and not selected.needs_clarification


def test_letter_and_conversion_are_one_grade_task_not_an_unrelated_extra_request():
    from campusai.rag.grade_ranges import deterministic_grade_answer
    ranges=RetrievalResult('range','d',1,'B: từ 6,1 đến 7,3;','text',1.,'test',{})
    points=RetrievalResult('points','d',2,'B quy đổi thành 2,6;','text',1.,'test',{})
    answer=deterministic_grade_answer('Điểm 6,7 là chữ gì và quy đổi hệ4 bao nhiêu?',[ranges,points])
    assert answer and not answer.abstained and '2,6' in answer.answer
    assert deterministic_grade_answer('Điểm 6,7 là chữ gì và mật khẩu cá nhân là gì?',[ranges,points]) is None


def test_explicit_new_school_comparison_retains_both_source_owners(sources):
    from campusai.retrieval.institution_scope import requested_institution_documents
    history=[{'role':'user','content':'Khóa luận Sao Bắc cần CPA bao nhiêu?'},
             {'role':'assistant','content':'Untrusted threshold99'}]
    resolved=resolve_query('Chuyển sang Gió Tây: mức đó có giống không?',history=history)
    result=resolve_institution_request(resolved.resolved,sources,history)
    assert result.doc_ids=={'north','west'} and not result.needs_clarification
    assert requested_institution_documents(result.question,sources)=={'north','west'}
    assert '99' not in result.question


def test_changed_semester_updates_slot_without_retaining_opposite_term():
    history=[{'role':'user','content':'Sao Bắc kỳ hè tối đa bao tín?'}]
    resolved=resolve_query('Nếu kỳ chính?',history=history)
    assert 'kỳ chính' in resolved.resolved and 'kỳ hè' not in resolved.resolved


@pytest.mark.parametrize('bound,inclusive,value,answer,valid',[
    ('3,3',True,'3,29','CPA3,29 chưa đạt ngưỡng; yêu cầu đạt từ3,3 trở lên.',True),
    ('3,3',True,'3,29','Đạt ngưỡng CPA.',False),
    ('3,3',False,'3,3','Đạt ngưỡng CPA.',False),
    ('3,3',False,'3,3','Chưa đạt ngưỡng CPA.',True),
    ('3,3',True,'3,3','Đạt ngưỡng CPA; còn các điều kiện khác.',True),
])
def test_gpa_comparator_proof_preserves_strict_and_inclusive_bounds(bound,inclusive,value,answer,valid):
    from campusai.rag.numeric_inference import gpa_application_view
    rule='Điểm trung bình tích lũy '+('đạt từ '+bound+' trở lên.' if inclusive else 'lớn hơn '+bound+'.')
    result=gpa_application_view(answer,[rule],'CPA '+value+' có đạt ngưỡng không?')
    assert (isinstance(result,str))==valid
    if not valid:assert result is False


def test_minimum_gpa_does_not_prove_automatic_overall_eligibility():
    from campusai.rag.numeric_inference import gpa_application_view
    rules=['Điểm trung bình tích lũy đạt từ3,3 trở lên.']
    assert gpa_application_view('Đạt ngưỡng và chắc chắn được làm ngay.',rules,'CPA3,5 đủ chưa?') is False
    assert gpa_application_view('Đạt ngưỡng nhưng chưa đủ để kết luận chắc chắn.',rules,'CPA3,5 đủ chưa?') is None
    view=gpa_application_view('CPA3,29 chưa đạt ngưỡng. Học phí3,29 đồng.',rules,'CPA3,29 đủ chưa?')
    assert isinstance(view,str) and 'phí3,29' in view


@pytest.mark.parametrize('value',['3,29','3.29'])
def test_gpa_input_followed_by_clause_comma_is_not_a_truncated_decimal(value):
    from campusai.rag.numeric_inference import gpa_application_view
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Điểm trung bình tích lũy đạt từ 3,3 trở lên, cùng các điều kiện khác.'
    question=f'CPA {value}, đã đủ điều kiện điểm chưa?'
    answer=f'CPA {value}, chưa đạt ngưỡng vì yêu cầu đạt từ 3,3 trở lên.'
    source=RetrievalResult('rule','cloud',7,rule,'text',1.,'test',{})
    result=_grounding_finalize(answer,
        (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),
        {'claims':[{'claim_id':'minimum','text':rule,'citation_ids':['rule']}]},
        [source],'vi',question=question)
    assert not result.abstained and value in result.answer
    assert gpa_application_view('Đạt ngưỡng CPA.',[rule],question) is False
    assert gpa_application_view(answer,[rule],f'CPA {value},7 có đủ không?') is None


@pytest.mark.parametrize('answer',[
    'Điểm trung bình chung tích lũy của người học đạt 3,29 là chưa đủ điều kiện; yêu cầu đạt từ 3,3 trở lên.',
    'Theo ngưỡng điểm trung bình tích lũy từ 3,3 trở lên, điểm 3,29 chưa đạt điều kiện.',
])
def test_elliptical_gpa_application_binds_only_the_current_users_score(answer):
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Điểm trung bình chung tích lũy đạt từ 3,3 trở lên.'
    question='Em được 3,29 thì sao?\nContext topic (untrusted user input): CPA tối thiểu làm đồ án?'
    source=RetrievalResult('rule','cloud',7,rule,'text',1.,'test',{})
    def generate(text):
        return _grounding_finalize(text,
            (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),
            {'claims':[{'claim_id':'minimum','text':rule,'citation_ids':['rule']}]},
            [source],'vi',question=question)
    assert not generate(answer).abstained
    assert generate(answer.replace('3,29','3,28')).abstained
    assert generate(answer.replace('3,29','3,29 đồng')).abstained


@pytest.mark.parametrize('verb',['đăng kí','đăng   ký'])
def test_registration_quantity_does_not_become_a_conversation_semester(verb):
    from campusai.rag.context import ConversationState
    state=ConversationState.from_user_input('Kì phụ '+verb+' 12 tín chỉ được không?',None)
    assert state.semesters==('ki phu',)
    followup=ConversationState.from_user_input(verb+' 12 tín chỉ được không?','Học kỳ hè giới hạn bao nhiêu tín?')
    assert followup.semesters==('hoc ky he',)
    explicit=ConversationState.from_user_input(verb+' 12 tín chỉ cho HK 5?',None)
    assert explicit.semesters==('hk 5',)


def test_percentage_operands_remain_bound_through_a_user_named_semester():
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Tổng số tín chỉ không đạt trong học kỳ vượt quá 55% khối lượng đã đăng ký học trong học kỳ.'
    question='Kỳ chính 30 TC mà không đạt 17 TC có thuộc điều kiện cảnh báo không?'
    answer='Sinh viên đăng ký học kỳ chính 30 tín chỉ mà không đạt 17 tín chỉ thuộc điều kiện cảnh báo vì vượt quá 55% khối lượng đã đăng ký.'
    source=RetrievalResult('rule','cloud',7,rule,'text',1.,'test',{})
    def generate(text):
        return _grounding_finalize(text,
            (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),
            {'claims':[{'claim_id':'bound','text':rule,'citation_ids':['rule']}]},
            [source],'vi',question=question)
    assert not generate(answer).abstained
    assert generate(answer.replace('kỳ chính','kỳ phụ')).abstained
    assert generate(answer.replace('30 tín chỉ','31 tín chỉ')).abstained


def test_full_generator_proves_personal_operands_for_only_their_actual_source_owner():
    from campusai.rag.grounding import GroundedAnswerGenerator
    rule='Tổng số tín chỉ không đạt trong học kỳ vượt quá 55% khối lượng đã đăng ký học trong học kỳ.'
    first=RetrievalResult('rule','cloud',7,rule,'text',1.,'test',{'source_name':'first.pdf'})
    fee='Phí hồ sơ là 31 USD.'
    second=RetrievalResult('fee','wind',4,fee,'text',1.,'test',{'source_name':'second.pdf'})
    class PreservedShape:
        def __init__(self,owner):self.owner=owner
        def generate_json(self,*args,**kwargs):
            return {'answer':self.owner+': Sinh viên đăng ký học kỳ chính 30 tín chỉ mà không đạt 17 tín chỉ thuộc điều kiện cảnh báo.\nsecond.pdf: '+fee,
                'abstained':False,'confidence':'high','citations':[{'chunk_id':'rule'},{'chunk_id':'fee'}],
                'claims':[{'claim_id':'bound','text':rule,'citation_ids':['rule']},
                          {'claim_id':'fee','text':fee,'citation_ids':['fee']}]}
    question='Kỳ chính 30 TC mà không đạt 17 TC có thuộc điều kiện cảnh báo không?'
    def generate(owner):return GroundedAnswerGenerator(PreservedShape(owner),source_citations=True,
        repair_invalid_answers=True).answer(question,[first,second],'vi')
    assert not generate('first.pdf').abstained
    assert generate('second.pdf').abstained


def test_registration_cap_proves_only_the_bound_users_negative_application():
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Đối với học kỳ phụ (nếu có): Sinh viên đăng ký không vượt quá 11 tín chỉ.'
    question='Kỳ phụ đăng kí 12 tín được không?'
    answer='Sinh viên chỉ được đăng ký tối đa 11 tín chỉ, do đó không thể đăng ký 12 tín chỉ.'
    def generate(text,source_rule=rule,claim_texts=None):
        source=RetrievalResult('rule','cloud',7,source_rule,'text',1.,'test',{})
        return _grounding_finalize(text,
            (Citation('rule','cloud',7,source_rule,source_name='cloud.pdf',page_range=(7,7)),),
            {'claims':[{'claim_id':'cap'+str(i),'text':claim,'citation_ids':['rule']}
                       for i,claim in enumerate(claim_texts or [source_rule])]},
            [source],'vi',question=question)
    assert not generate(answer).abstained
    assert generate(answer.replace('không thể','có thể')).abstained
    assert generate(answer.replace('12 tín chỉ','13 tín chỉ')).abstained
    assert generate(answer+' Học phí là 12 đồng.').abstained
    assert generate(answer,rule.replace('học kỳ phụ','học kỳ chính')).abstained
    assert generate(answer,'Nếu được cấp học bổng, '+rule).abstained
    assert generate(answer,rule+' Sinh viên đăng ký tối đa 14 tín chỉ.').abstained
    exception='Nếu được cấp học bổng, trong học kỳ phụ sinh viên đăng ký tối đa 14 tín chỉ.'
    assert generate(answer,rule+'\n'+exception,[rule,exception]).abstained
    global_exception=exception.replace('trong học kỳ phụ ','')
    assert generate(answer,rule+'\n'+global_exception,[rule,global_exception]).abstained
    # An exception present in the visible quote cannot be hidden by simply
    # omitting it from the model's structured claims.
    assert generate(answer,rule+'\n'+global_exception,[rule]).abstained


@pytest.mark.parametrize('literal,invalid',[
    ('Văn bản được ký ngày 42 tháng 2 năm 2032.',True),
    ('Văn bản được ký ngày 12 tháng ( năm 2032.',True),
    ('Issued on February 30, 2032.',True),
    ('Giờ hẹn là 25:73.',True),
    ('Issued on February 29, 2032.',False),
    ('Văn bản được ký ngày 29 tháng 2 năm 2032.',False),
    ('Giờ hẹn là 23:59.',False),
])
def test_literal_ocr_overlap_cannot_verify_an_impossible_calendar_field(literal,invalid):
    from campusai.rag.grounding import Citation,_grounding_finalize
    source=RetrievalResult('rule','cloud',7,literal,'text',1.,'test',{})
    answer=_grounding_finalize(literal,
        (Citation('rule','cloud',7,literal,source_name='cloud.pdf',page_range=(7,7)),),
        {'claims':[{'claim_id':'date','text':literal,'citation_ids':['rule']}]},
        [source],'vi',question='Văn bản được ký khi nào?')
    assert answer.abstained is invalid


def test_percentage_application_is_arithmetic_not_a_new_policy_threshold():
    from campusai.rag.numeric_inference import percentage_application_view
    rule='Tổng số tín chỉ không đạt trong học kỳ vượt quá55% khối lượng đã đăng ký học trong kỳ.'
    question='Đăng ký30 TC không đạt17 TC có thuộc điều kiện cảnh báo không?'
    answer='Có,17 vượt quá55% của30 là16,5 tín chỉ, thuộc điều kiện cảnh báo.'
    result=percentage_application_view(answer,[rule],question)
    assert isinstance(result,str) and '16,5' not in result
    assert percentage_application_view('Không thuộc điều kiện cảnh báo.',[rule],question) is False
    assert percentage_application_view('Có,17/30=16,5%, thuộc điều kiện cảnh báo.',[rule],question) is False


@pytest.mark.parametrize('application',[
    'Đăng ký 30 TC và không đạt 17 TC, tỷ lệ không đạt là 17/30 (khoảng 56,67%), thuộc điều kiện cảnh báo.',
    'Với 30 TC đăng ký và không đạt 17 TC, số tín chỉ không đạt chiếm khoảng 56,67%, thuộc điều kiện cảnh báo.',
])
def test_credit_ratio_accepts_parenthetical_rounding_and_reordered_bound_operands(application):
    from campusai.rag.numeric_inference import percentage_application_view
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Tổng số tín chỉ không đạt vượt quá 55% khối lượng đăng ký học trong kỳ.'
    question='Kỳ chính 30 TC không đạt 17 TC có thuộc điều kiện cảnh báo không?'
    view=percentage_application_view(application,[rule],question)
    assert isinstance(view,str) and not any(value in view for value in ['17','30','56,67'])
    assert percentage_application_view(application.replace('56,67','54,67'),[rule],question) is False
    assert percentage_application_view(application.replace('17 TC','18 TC'),[rule],question) is False
    extra=percentage_application_view(application+' Học phí là 56,67 đồng.',[rule],question)
    assert '56,67 đồng' in extra
    source=RetrievalResult('rule','cloud',7,rule,'text',1.,'test',{})
    accepted=_grounding_finalize(application,
        (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),
        {'claims':[{'claim_id':'bound','text':rule,'citation_ids':['rule']}]},
        [source],'vi',question=question)
    assert not accepted.abstained
    rejected=_grounding_finalize(application+' Học phí là 56,67 đồng.',
        (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),
        {'claims':[{'claim_id':'bound','text':rule,'citation_ids':['rule']}]},
        [source],'vi',question=question)
    assert rejected.abstained
    assert percentage_application_view('Có,đăng ký17 TC không đạt30 TC.',[rule],question) is False
    unsafe=percentage_application_view('Có,đăng ký30 TC không đạt17 TC. Học phí16,5 đồng.',[rule],question)
    assert isinstance(unsafe,str) and '16,5' in unsafe  # unrelated value remains unproved


def test_percentage_application_completion_adds_only_proven_arithmetic():
    from campusai.rag.numeric_inference import percentage_application_completion
    question='Đăng ký24 TC, không đạt13 TC có vượt ngưỡng không?'
    rule='Số tín chỉ không đạt vượt quá 50% khối lượng đã đăng ký học trong kỳ.'
    assert percentage_application_completion('Có, vượt quá 50% nên thuộc tiêu chí này.',
        question,[rule])=='Đối chiếu riêng tiêu chí này: 13/24 ≈ 54,17%, lớn hơn ngưỡng 50%; vì vậy số tín chỉ không đạt vượt ngưỡng của tiêu chí này.'
    # Never add a computation when the model's conclusion conflicts with the
    # user operands, the source rule is missing, or sources disagree.
    assert percentage_application_completion('Không, không vượt quá 50%.',question,[rule]) is None
    assert percentage_application_completion('Có, vượt quá 50%.',question,['Tài liệu không nêu ngưỡng.']) is None
    assert percentage_application_completion('Có, vượt quá 50%.',question,
        [rule,'Số tín chỉ không đạt vượt quá 60% tín chỉ đăng ký.']) is None
    boundary='Đăng ký24 TC, không đạt12 TC có vượt ngưỡng không?'
    assert percentage_application_completion('Không, không vượt quá 50%.',boundary,[rule])==(
        'Đối chiếu riêng tiêu chí này: 12/24 ≈ 50%, không lớn hơn ngưỡng 50%; vì vậy số tín chỉ không đạt không vượt ngưỡng của tiêu chí này.')
    assert percentage_application_completion('Yes, above 50%.',
        'Registered24 credits, failed13 credits; does it exceed the rule?',
        ['Failed credits greater than 50% of registered credits.'],language='en')==(
            'For this criterion, 13/24 is approximately 54.17%, which is above the 50% threshold.')


def test_grounding_completes_clear_percentage_threshold_application_from_its_citation():
    from campusai.rag.grounding import GroundedAnswerGenerator
    rule='Tổng số tín chỉ không đạt trong học kỳ vượt quá 50% khối lượng đã đăng ký học trong kỳ.'
    source=RetrievalResult('rule','cloud',7,rule,'text',1.,'test',{})
    class DirectConclusion:
        def generate_json(self,*args,**kwargs):
            return {'answer':'Có, vượt quá 50% nên thuộc tiêu chí này.',
                'abstained':False,'confidence':'high','citations':[{'chunk_id':'rule','page':7,'quote':rule}],
                'claims':[{'claim_id':'threshold','text':rule,'citation_ids':['rule']}]}
    result=GroundedAnswerGenerator(DirectConclusion(),
        repair_invalid_answers=False).answer(
            'Đăng ký24 TC, không đạt13 TC có vượt ngưỡng không?',[source],'vi')
    assert not result.abstained
    assert '13/24' in result.answer and '54,17%' in result.answer
    assert result.citations and result.citations[0].doc_id=='cloud'


def test_elective_selection_cannot_promote_offered_total_to_required_total():
    from campusai.rag.numeric_inference import elective_application_conflict
    source='Chọn4/8 tín chỉ sau: ZX987001(4),ZX987002(4).'
    question='Có được chọn cả ZX987001 và ZX987002 để tính đủ8 TC bắt buộc không?'
    assert elective_application_conflict('Có, chọn cả hai để tính đủ8 tín chỉ.',[source],question)
    assert not elective_application_conflict('Yêu cầu chọn4 trong8 tín chỉ.',[source],question)
    assert elective_application_conflict('Có, chọn cả hai để tính đủ8 tín chỉ.',
        [source,'Chọn2/4 tín chỉ từ nhóm khác.'],question)


def test_long_course_identifier_and_total_credit_column_are_not_elective_flags():
    import json
    from campusai.rag.course_credits import headed_credit_rows
    from campusai.retrieval.routing import detected_course_codes
    table={'headers':['STT','Mã HP','Tên học phần','Tổng\nsố TC','BB','TC'],
           'rows':[['3','ZX1234567','Điều khiển','4','4','8']]}
    rows=headed_credit_rows(json.dumps(table,ensure_ascii=False))
    assert rows and rows[0][:2]==('ZX1234567',4)
    assert detected_course_codes('ZX1234567 có mấy tín?')==('ZX1234567',)


def test_semester_footer_proves_only_its_contiguous_source_group():
    import json
    from campusai.rag.source_citations import source_quote
    from campusai.rag.grounding import validate_quote
    table={'headers':['STT','Mã HP','Tên học phần','Tổng số TC','BB','TC'],
           'rows':[['6','ZX123450','Giải tích','2','2',''],['','','Tổng học kỳ3','2','2',''],
                   ['1','ZX123456','Điều khiển','4','4',''],['2','ZX123457','Tối ưu','3','3',''],
                   ['','','Tổng học kỳ4','7','7','']]}
    body=json.dumps(table,ensure_ascii=False)
    source=RetrievalResult('table','catalog',8,body,'table',1.,'test',{})
    claims=[{'text':'ZX123456 | Điều khiển | 4','citation_ids':['table']}]
    quote=source_quote(source,claims,'HK4 có ZX123456 mấy tín?')
    assert quote and validate_quote(quote,body)
    assert 'Tổng học kỳ4' in quote and 'Tổng học kỳ3' not in quote
    assert source_quote(source,claims,'HK3 có ZX123456 mấy tín?') is None


def test_public_contact_fields_require_complete_consistent_source_rows():
    import json
    from campusai.rag.table_fields import deterministic_contact_fields
    def source(ident,address):
        return RetrievalResult(ident,'d',2,json.dumps({'headers':['NORTH STAR UNIVERSITY'],
            'rows':[['Địa chỉ: '+address],['Email: registrar@example.edu']]},ensure_ascii=False),'table',1.,'test',{})
    rows=[source('contact','12 Cloud Street')]
    answer=deterministic_contact_fields('Email liên hệ và địa chỉ trường là gì?',rows)
    assert answer and not answer.abstained and 'registrar@example.edu' in answer.answer
    assert '12 Cloud Street' in answer.answer
    assert deterministic_contact_fields('Email và địa chỉ trường là gì?',rows+[source('other','13 Wind Street')]) is None
    assert deterministic_contact_fields('Email cá nhân của em là gì?',rows) is None
    assert deterministic_contact_fields('Email và ngày đăng ký của trường là gì?',rows) is None
    assert deterministic_contact_fields('Email phòng đào tạo là gì?',rows) is None


def test_persistent_answer_cache_is_bound_to_installed_source(tmp_path,monkeypatch):
    from campusai.rag import cache
    source=tmp_path/'package';source.mkdir()
    policy=source/'policy.py';policy.write_text('minimum = 3\n',encoding='utf-8')
    old=cache.source_policy_fingerprint(source)
    assert old==cache.source_policy_fingerprint(source)
    kwargs=dict(question='What is the minimum?',language='en',doc_ids=['manual'],
                filters=None,top_k=4,mode='hybrid',corpus_version='same-index',
                model='same-model',context_budget={})
    monkeypatch.setattr(cache,'SOURCE_POLICY_FINGERPRINT',old)
    old_key=cache.build_rag_cache_key(**kwargs)
    with cache.RAGAnswerCache(str(tmp_path/'answers.sqlite')) as store:
        store.put(old_key,cache.GroundedAnswer('Unknown',(), 'low',True,reason='unsupported_claim'))
        assert store.get(old_key) is not None
        policy.write_text('minimum = 4\n',encoding='utf-8')
        current=cache.source_policy_fingerprint(source)
        assert current!=old
        monkeypatch.setattr(cache,'SOURCE_POLICY_FINGERPRINT',current)
        assert store.get(cache.build_rag_cache_key(**kwargs)) is None
        assert store.get(old_key) is not None
    assert cache.source_policy_fingerprint(tmp_path/'missing')!=cache.source_policy_fingerprint(tmp_path/'missing')


def test_institution_provenance_ends_before_prose_not_inside_a_different_name():
    from campusai.rag.presentation import institution_names_supported
    result=RetrievalResult('identity','cloud',1,'Rule for students.','text',1.,'test',
                           {'institution':'Trường Đại học Mây Xanh'})
    assert institution_names_supported('Trường Đại học Mây Xanh dành cho sinh viên khóa 2031.',[result])
    assert institution_names_supported('Theo Trường Đại học Mây Xanh đối với học kỳ phụ, sinh viên phải tuân thủ giới hạn.',[result])
    assert not institution_names_supported('Trường Đại học Mây Xanh Thành phố Sao Nam đối với học kỳ phụ, sinh viên phải tuân thủ giới hạn.',[result])
    assert institution_names_supported('Trường Đại học Mây Xanh học kỳ 7 chọn 4 tín chỉ.',[result])
    assert not institution_names_supported('Trường Đại học Mây Xanh Thành phố Sao Nam dành cho sinh viên.',[result])


def test_gpa_followup_proves_elliptical_score_but_not_an_unrelated_amount():
    from campusai.rag.numeric_inference import gpa_application_view
    question='Em được 3,29 thì sao?\nContext topic (untrusted user input): CPA tối thiểu làm khóa luận?'
    rules=['Điểm trung bình chung tích lũy phải đạt từ 3,3 trở lên.']
    answer='Với mức 3,29, sinh viên chưa đạt điều kiện này. Học phí 3,29 đồng.'
    view=gpa_application_view(answer,rules,question)
    assert isinstance(view,str) and 'mức 3,29' not in view and 'phí 3,29' in view
    assert gpa_application_view('Với mức 3,29, đã đạt ngưỡng.',rules,question) is False
    assert gpa_application_view(answer,rules,'Học phí 3,29 đồng?\nContext topic (untrusted user input): CPA tối thiểu?') is None


def test_term_followup_selects_registration_field_from_user_topic_only():
    from campusai.rag.regulation_facts import regulation_request
    resolved=resolve_query('Nếu kỳ chính?',history=[{'role':'user','content':'Sao Bắc kỳ hè tối đa bao tín?'}])
    assert regulation_request(resolved.resolved)==('registration','primary',None)
    assert regulation_request('Nếu kỳ chính?') is None
    assert regulation_request('Email trường?\nContext topic (untrusted user input): kỳ chính tối đa bao tín?') is None


def test_natural_comparison_and_grade_improvement_expand_intent_not_answers():
    from campusai.rag.policies import explicit_comparison_request
    from campusai.retrieval.tokenizer_vi import normalize_retrieval_query
    assert explicit_comparison_request('Quy đổi ở hai nguồn có giống không?')
    assert not explicit_comparison_request('Không so sánh, chỉ tra nguồn đã chọn.')
    expanded=normalize_retrieval_query('Học lại kéo điểm lên được không?')
    assert 'học lại học phần đã có điểm đạt' in expanded
    assert not any(n in expanded for n in ['2,5','3,7','9,5'])


def test_context_identity_requires_a_literal_same_document_header():
    from dataclasses import replace
    from campusai.rag.grounding import _context_block
    proof={'name':'Trường Đại học Mây Xanh','quote':'HIỆU TRƯỞNG Trường Đại học Mây Xanh',
           'page':1,'chunk_id':'header','doc_id':'cloud'}
    row=RetrievalResult('rule','cloud',8,'Minimum 7 credits.','text',1.,'test',
                        {'institution':'Invented university','institution_proof':proof})
    metadata,body=_context_block(row)
    assert 'source_identity_provenance=' in metadata and proof['quote'] in metadata
    assert 'Invented university' not in metadata and body=='Minimum 7 credits.'
    assert 'source_identity_provenance=' not in _context_block(replace(row,
        metadata={'institution_proof':{**proof,'doc_id':'other'}}))[0]
    assert 'source_identity_provenance=' not in _context_block(replace(row,
        metadata={'institution_proof':{**proof,'name':'Trường Đại học Sai'}}))[0]


def test_categorical_cap_cannot_be_borrowed_from_another_condition():
    from campusai.rag.presentation import conditional_labels_supported
    source=('2. Người học bị kỷ luật mức nhẹ, khi đánh giá không được vượt quá loại xanh.\n'
            '3. Người học bị kỷ luật mức nặng, khi đánh giá kết quả rèn')
    wrong='Người học bị kỷ luật mức nặng, khi đánh giá không được vượt quá loại xanh.'
    assert not conditional_labels_supported(wrong,[source])
    assert not conditional_labels_supported(wrong,[source,'luyện không được vượt quá loại vàng.'])
    correct=wrong.replace('loại xanh','loại vàng')
    assert conditional_labels_supported(correct,[source,'luyện không được vượt quá loại vàng.'])
    assert conditional_labels_supported(wrong.replace('mức nặng','mức nhẹ'),[source])
    assert conditional_labels_supported('Tài liệu chưa đủ để kết luận.',[source])


def test_closing_semester_marker_remains_a_proved_locator_in_final_answer():
    import json
    from campusai.rag.grounding import Citation,_grounding_finalize
    from campusai.rag.source_citations import source_quote
    table={'headers':['Mã HP','Tên học phần','Tổng số TC'],
           'rows':[['ZX987654','Điều khiển','4'],['','Tổng học kỳ7','4']]}
    row=RetrievalResult('table','catalog',8,json.dumps(table,ensure_ascii=False),'table',1.,'test',{})
    claims=[{'claim_id':'row','text':'ZX987654 | Điều khiển | 4','citation_ids':['table']}]
    question='HK7 môn ZX987654 mấy tín?'
    quote=source_quote(row,claims,question)
    assert quote
    from campusai.rag.course_credits import headed_credit_rows
    assert any(code=='ZX987654' and credits==4 for code,credits,_ in headed_credit_rows(quote) or [])
    citation=Citation('table','catalog',8,quote)
    payload={'confidence':'high','claims':claims}
    answer=_grounding_finalize('Môn ZX987654 ở học kỳ7 có4 tín chỉ.',(citation,),payload,[row],'vi',question=question)
    assert not answer.abstained
    wrong=_grounding_finalize('Môn ZX987654 ở học kỳ6 có4 tín chỉ.',(citation,),payload,[row],'vi',question=question)
    assert wrong.abstained


@pytest.mark.parametrize('balanced',[True,False])
def test_header_provenance_uses_context_budget_once_per_document(balanced):
    from dataclasses import replace
    from campusai.rag.grounding import build_context
    proof={'name':'Trường Đại học Mây Xanh','quote':'Trường Đại học Mây Xanh',
           'page':1,'chunk_id':'header','doc_id':'cloud'}
    row=RetrievalResult('first','cloud',2,'First literal rule.','text',1.,'test',{'institution_proof':proof})
    other=replace(row,chunk_id='second',page=3,content='Second literal rule.')
    text=build_context([row,other],max_chars=2500,balanced=balanced)
    assert text.count('source_identity_provenance=')==1
    assert 'First literal rule.' in text and 'Second literal rule.' in text


def test_spoken_numeric_alternatives_select_a_source_proved_conversion():
    from campusai.rag.grade_ranges import deterministic_grade_answer
    ranges=RetrievalResult('range','d',1,'B: từ 6,1 đến 7,3;','text',1.,'test',{})
    points=RetrievalResult('points','d',2,'B quy đổi thành 2,6;','text',1.,'test',{})
    answer=deterministic_grade_answer('7 phẩy 1 là 3 chấm hay 2 chấm 6?',[ranges,points])
    assert answer and not answer.abstained and '2,6' in answer.answer
    assert deterministic_grade_answer('Học phí 7 phẩy 1 là 3 chấm hay 2 chấm 6?',[ranges,points]) is None


def test_source_ownership_binds_credit_header_to_only_the_claimed_course_row():
    import json
    from campusai.rag.claims import Claim
    from campusai.rag.grounding import Citation
    from campusai.rag.presentation import source_ownership_conflicts,quantity_spacing
    table={'headers':['Mã HP','Tên học phần','Tổng số TC'],
           'rows':[['ZX987654','Điều khiển','4'],['ZX987655','Tối ưu','7']]}
    text=json.dumps(table,ensure_ascii=False)
    row=RetrievalResult('table','cloud',8,text,'table',1.,'test',
        {'institution':'Trường Đại học Mây Xanh','source_name':'cloud.pdf'})
    claim=Claim('course','ZX987654 | Điều khiển | 4','fact',1,('table',),'supported',1.,('table',),False)
    cite=Citation('table','cloud',8,text,source_name='cloud.pdf')
    def conflict(answer):return source_ownership_conflicts(answer,[claim],[cite],[row])
    assert not conflict('Trường Đại học Mây Xanh có môn ZX987654 với4 tín chỉ.')
    assert conflict('Trường Đại học Mây Xanh có môn ZX987654 với7 tín chỉ.')
    assert conflict('Trường Đại học Mây Xanh có học phí4 USD.')
    assert quantity_spacing('CO123456 có4 tín chỉ')=='CO123456 có 4 tín chỉ'


def test_checkpoint_commit_recovers_a_windows_reader_lock_without_losing_data(tmp_path,monkeypatch):
    from pathlib import Path
    from scripts.release import measure_ocr
    import json
    path=tmp_path/'results.json';path.write_text('{"count":1}',encoding='utf-8')
    original=Path.replace;attempts=[]
    def sharing_violation_once(source,target):
        attempts.append(source)
        if len(attempts)==1:
            error=PermissionError('Reader temporarily denies delete sharing');error.winerror=32
            raise error
        return original(source,target)
    monkeypatch.setattr(Path,'replace',sharing_violation_once)
    monkeypatch.setattr(measure_ocr.time,'sleep',lambda _delay:None)
    measure_ocr.save(path,{'count':2,'response':'unchanged native answer'})
    assert json.loads(path.read_text(encoding='utf-8'))=={'count':2,'response':'unchanged native answer'}
    assert len(attempts)==2 and not path.with_name(path.name+'.tmp').exists()


def test_plain_contact_labels_answer_location_without_promotional_intro():
    from campusai.rag.table_fields import deterministic_contact_fields
    row=RetrievalResult('contact','acme',2,
        'ACME RESEARCH\nAddress:12 Cloud Road,\nBlue City.\nPhone:123456\nEmail: info@example.org\n\n'
        'Our company is the best in the world.','text',1.,'test',{})
    answer=deterministic_contact_fields('ACME RESEARCH ở đâu vậy?',[row])
    assert answer and not answer.abstained and '12 Cloud Road' in answer.answer and 'Blue City' in answer.answer
    assert 'best' not in answer.answer and 'Phone' not in answer.answer
    pair=deterministic_contact_fields('Email và địa chỉ là gì?',[row])
    assert pair and 'info@example.org' in pair.answer and 'Blue City' in pair.answer
    assert deterministic_contact_fields('OTHER RESEARCH ở đâu vậy?',[row]) is None
    assert deterministic_contact_fields('Nộp hồ sơ ACME RESEARCH ở đâu?',[row]) is None
    assert deterministic_contact_fields('Email cá nhân của em?',[row]) is None


def test_plain_contact_conflicts_and_truncated_fields_fail_closed():
    from dataclasses import replace
    from campusai.rag.table_fields import deterministic_contact_fields
    row=RetrievalResult('contact','d',2,'Address:12 Cloud Road.\n\nAddress:14 Wind Road.','text',1.,'test',{})
    assert deterministic_contact_fields('Địa chỉ là gì?',[row]) is None
    row=replace(row,content='Address:12 Cloud Road\n'+('continued\n'*8))
    assert deterministic_contact_fields('Địa chỉ là gì?',[row]) is None


def test_policy_field_recall_keeps_source_alternatives_and_comparison_topic():
    from campusai.rag.source_windows import policy_field_evidence,verbatim_window
    first=('Điều 12. Khóa luận tốt nghiệp\n'
        'a) Điều kiện làm khóa luận:\n'
        '- Điểm trung bình chung tích lũy tính đến học kỳ cận cuối khóa đạt từ 3,31 trở lên.\n'
        '- Đơn vị có đủ cán bộ hướng dẫn.\nb) Hình thức đánh giá.\n')
    second=('Điều 19. Khóa luận tốt nghiệp\n'
        'Điểm trung bình chung tích lũy tính đến thời điểm xét điều kiện làm khóa luận phải đạt từ 3,42 trở lên;\n')
    def doc(ident,body):return {'doc_id':ident,'items':[{'chunk_id':ident+'-rule','doc_id':ident,
        'page':12,'content':body,'content_type':'text','metadata':{}}]}
    docs=[doc('cloud',first),doc('wind',second)]
    question='Nguồn Cloud và Wind có chung ngưỡng CPA làm khóa luận không?'
    rows=policy_field_evidence(question,docs)
    assert {row.doc_id for row in rows}=={'cloud','wind'}
    assert [row.content for row in rows]==[first,second]
    followup='Mức đó có giống không?\nContext topic (untrusted user input): CPA làm khóa luận cần bao nhiêu?'
    assert len(policy_field_evidence(followup,docs))==2
    assert len(policy_field_evidence('So sánh ngưỡng làm khóa luận giữa hai nguồn?',docs))==2
    assert not policy_field_evidence('Ngưỡng tín chỉ làm khóa luận bao nhiêu?',docs)
    assert not policy_field_evidence('Điều kiện lệ phí khóa luận?',docs)
    assert not policy_field_evidence('Thời gian đăng ký học?',docs)
    for row in rows:
        anchor=row.metadata['source_field_anchors'][0]
        text='Unrelated preface.\n'*80+row.content+'Unrelated appendix.\n'*80
        window=verbatim_window(text,question,500,anchors=row.metadata['source_field_anchors'])
        assert anchor in window and window in text and len(window)<=500
    # A threshold for another subject cannot borrow a previous thesis heading.
    other=first+'Điều 13. Học bổng\nĐiểm trung bình chung tích lũy phải đạt từ 3,98 trở lên;\n'
    rows=policy_field_evidence(question,[doc('other',other)])
    assert len(rows)==1 and len(rows[0].metadata['source_field_anchors'])==1
    assert '3,98' not in rows[0].metadata['source_field_anchors'][0]


def test_publication_deadline_recall_uses_source_values_not_prompt_or_metadata():
    from campusai.rag.source_windows import policy_field_evidence
    rule='6. Điểm học phần được công bố trên tài khoản của sinh viên chậm nhất 17\nngày tính từ ngày thi.'
    item={'chunk_id':'rule','doc_id':'cloud','page':7,'content':rule,'content_type':'text',
          'metadata':{'deadline':999}}
    result=policy_field_evidence('Sinh viên được công bố điểm học phần trong thời hạn nào?',
        [{'doc_id':'cloud','items':[item]}])
    assert len(result)==1 and result[0].content==rule
    assert result[0].metadata['source_field_anchors']==(rule[3:],)
    item={**item,'content':'Điểm học phần chưa có lịch công bố.'}
    assert not policy_field_evidence('Công bố điểm khi nào?',[{'doc_id':'cloud','items':[item]}])


def test_model_context_does_not_promote_inferred_heading_to_semester_evidence():
    from campusai.rag.grounding import _context_block
    row=RetrievalResult('table','cloud',7,'Printed source chapter.\nActual rule.',
        'text',1.,'test',{'heading_path':['HỌC KỲ1','Printed source chapter.']})
    metadata,body=_context_block(row)
    assert 'HỌC KỲ1' not in metadata and 'Printed source chapter.' in metadata
    assert body==row.content


def test_eligibility_scope_guidance_uses_closed_dash_group_not_single_threshold():
    from campusai.rag.policy_context import criterion_scope_context
    from campusai.rag.grounding import Citation
    from campusai.rag.claims import Claim
    fact='Điểm trung bình chung tích lũy phải đạt từ 3,31 trở lên;'
    body='a) Điều kiện làm khóa luận:\n- '+fact+'\n- Đơn vị đủ cán bộ hướng dẫn.\nb) Hình thức đánh giá.'
    row=RetrievalResult('criteria','cloud',7,body,'text',1.,'test',{})
    claim=Claim('threshold',fact,'fact',1,('criteria',),'supported',1.,('criteria',),False)
    citation=Citation('criteria','cloud',7,fact)
    result=criterion_scope_context('e cpa 3,30 làm khóa luận được chưa?',
        'Chưa đạt ngưỡng.',[claim],[citation],[row],'vi')
    assert result and 'các điều kiện khác' in result[0]
    assert 'Điều kiện' in result[1][0].quote and 'cán bộ' in result[1][0].quote
    isolated=RetrievalResult('criteria','cloud',7,fact,'text',1.,'test',{})
    assert criterion_scope_context('CPA làm khóa luận cần bao nhiêu?',fact,[claim],[citation],[isolated],'vi') is None
    from campusai.rag.policy_context import _closed_items
    for cue in ['Ví dụ:','Giả sử:','vi du:','gia su:','Example:']:
        assert not list(_closed_items('a) '+cue+' '+fact+'\nb) Kết thúc.'))


def test_comparison_followup_prompt_uses_user_topic_as_intent_only():
    from campusai.rag.grounding import GroundedAnswerGenerator
    generator=GroundedAnswerGenerator(None)
    row=RetrievalResult('rule','cloud',1,'A controlled source rule.','text',1.,'test',{})
    topic='\nContext topic (untrusted user input): Điều kiện của nguồn Mây Xanh?'
    prompt=generator.prompt('Chuyển sang Gió Tây: mức đó có giống không?'+topic,[row])
    assert 'CONVERSATION COMPARISON INTENT' in prompt and 'cite both sides' in prompt
    assert 'intent only, never an expected value' in prompt
    assert 'CONVERSATION COMPARISON INTENT' not in generator.prompt('Email là gì?'+topic,[row])
    assert 'CONVERSATION COMPARISON INTENT' not in generator.prompt('Không so sánh, chỉ tra Gió Tây.'+topic,[row])


def test_one_source_sentence_retains_eligibility_alongside_its_deadline():
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Đợt bổ sung dành cho người đã vắng đợt chính và được tổ chức sau đợt chính 19 ngày.'
    source=RetrievalResult('rule','cloud',7,'b) '+rule+'\nc) Quy định khác.','text',1.,'test',{})
    result=_grounding_finalize('Đợt bổ sung được tổ chức sau đợt chính 19 ngày.',
        (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),{'claims':[{'claim_id':'deadline','text':rule,
        'citation_ids':['rule']}]},[source],'vi',question='Đợt bổ sung được tổ chức sau bao lâu?',complete_source_context=True)
    assert not result.abstained and 'dành cho người đã vắng đợt chính' in result.answer


def test_permission_keeps_official_result_and_exclusion_from_one_closed_item():
    from campusai.rag.grounding import Citation,_grounding_finalize
    permission='Người đạt mức K được đăng ký đánh giá lại.'
    outcome='Kết quả chính thức là kết quả cao nhất qua các lần đánh giá.'
    exclusion='Không áp dụng cho người đã đạt mức J trở lên.'
    item=' '.join([permission,outcome,exclusion])
    body='b) '+item+'\nc) Quy trình chuyển đơn vị.'
    def generate(body,question='Đạt mức K có được đánh giá lại không?'):
        source=RetrievalResult('rule','cloud',7,body,'text',1.,'test',{})
        return _grounding_finalize(permission,
            (Citation('rule','cloud',7,permission,source_name='cloud.pdf',page_range=(7,7)),),
            {'claims':[{'claim_id':'permission','text':permission,'citation_ids':['rule']}]},
            [source],'vi',question=question,complete_source_context=True)
    answer=generate(body)
    assert not answer.abstained and outcome in answer.answer and exclusion in answer.answer
    assert 'chuyển đơn vị' not in answer.answer and len(answer.claims)==2
    assert outcome not in generate('b) '+item).answer  # No proven closing boundary.
    assert outcome not in generate(body,'Chỉ cần cho biết mức K có được đánh giá lại không?').answer


def test_last_policy_child_is_closed_only_by_a_proven_parent_successor():
    from campusai.rag.grounding import Citation,_grounding_finalize
    rule='Đối với ca phụ (nếu có): Người đăng ký không vượt quá 11 lượt.'
    extra='Không cấp phụ cấp cho người đăng ký trong ca này.'
    body='3. Giới hạn theo ca:\na) Ca sáng theo lịch.\nb) Ca chiều theo lịch.\nc) '+rule+' '+extra+'\n4. Quy trình liên hệ.'
    def generate(content):
        source=RetrievalResult('rule','cloud',7,content,'text',1.,'test',{})
        return _grounding_finalize(rule.replace(' (nếu có)',''),
            (Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7)),),
            {'claims':[{'claim_id':'limit','text':rule,'citation_ids':['rule']}]},
            [source],'vi',question='Ca phụ đăng ký tối đa bao nhiêu lượt?',complete_source_context=True)
    accepted=generate(body)
    assert not accepted.abstained and extra in accepted.answer and 'liên hệ' not in accepted.answer
    for incomplete in [body[:body.index('\n4.')],body.replace('4. Quy trình','5. Quy trình'),
                       body.replace('4. Quy trình','4.2 Quy trình'),body.replace('a) Ca sáng theo lịch.\n',''),
                       body.replace('\n4.','\nĐiều 17. Phần khác\n4.')]:
        assert extra not in generate(incomplete).answer


def test_complete_parent_quote_keeps_all_claims_and_last_child_restriction():
    from campusai.rag.grounding import Citation,_grounding_finalize
    facts=['Đăng ký sớm trước 23 ngày','Đăng ký thường trước 9 ngày','Đăng ký muộn trong 3 ngày đầu']
    body=('2. Các hình thức đăng ký:\na) '+facts[0]+'.\nb) '+facts[1]+'.\nc) '+facts[2]+
          ', chỉ áp dụng cho ca chưa được bố trí.\n3. Cách thanh toán.')
    source=RetrievalResult('rule','cloud',7,body,'text',1.,'test',{})
    quote=body[:body.index('\n3.')]
    answer=_grounding_finalize('; '.join(facts),
        (Citation('rule','cloud',7,quote,source_name='cloud.pdf',page_range=(7,7)),),
        {'claims':[{'claim_id':'f'+str(i),'text':fact,'citation_ids':['rule']} for i,fact in enumerate(facts)]},
        [source],'vi',question='Có những hình thức đăng ký và thời hạn nào?',complete_source_context=True)
    assert not answer.abstained and 'chỉ áp dụng cho ca chưa được bố trí' in answer.answer
    assert all(fact in answer.answer and fact in answer.citations[0].quote for fact in facts)
    assert 'thanh toán' not in answer.answer


def test_multiple_requested_criteria_keep_a_reminder_without_dropping_either_proof():
    from campusai.rag.grounding import Citation,_grounding_finalize
    facts=['Điểm trung bình tích lũy đạt từ 3,31 trở lên.',
           'Đã hoàn thành tối thiểu 81 tín chỉ.',
           'Mỗi đề án có không quá 3 giảng viên hướng dẫn.']
    body='1. Điều kiện xét đề án:\n'+''.join(chr(97+i)+') '+fact+'\n' for i,fact in enumerate(facts))+'2. Quy trình liên hệ.'
    source=RetrievalResult('rule','cloud',7,body,'text',1.,'test',{})
    def generate(selected):
        return _grounding_finalize(' '.join(selected),
            (Citation('rule','cloud',7,body,source_name='cloud.pdf',page_range=(7,7)),),
            {'claims':[{'claim_id':'f'+str(i),'text':fact,'citation_ids':['rule']} for i,fact in enumerate(selected)]},
            [source],'vi',question='Điều kiện đề án: mức GPA và số giảng viên tối đa là gì?',complete_source_context=True)
    partial=generate([facts[0],facts[2]])
    assert not partial.abstained and 'các điều kiện khác' in partial.answer
    assert facts[0] in partial.citations[0].quote and facts[2] in partial.citations[0].quote
    complete=generate(facts)
    assert not complete.abstained and 'các điều kiện khác' not in complete.answer


def test_closed_star_criteria_keep_credit_and_supervision_with_the_same_eligibility_rule():
    from campusai.rag.grounding import Citation,_grounding_finalize
    from campusai.rag.policy_context import _closed_star_criteria
    fact='Điểm trung bình chung tích lũy phải đạt từ 3,31 trở lên.'
    body=('* Điều kiện đăng ký khóa luận:\n- Hoàn thành tối thiểu 87 tín chỉ.\n- '+fact+
          '\n- Đơn vị đào tạo đủ cán bộ hướng dẫn.\n'
          '* Điều kiện đăng ký chuyên đề:\n- Hoàn thành 64 tín chỉ.\n')
    source=RetrievalResult('rule','cloud',7,body,'text',1.,'test',{})
    result=_grounding_finalize('CPA 3,30 chưa đạt ngưỡng làm khóa luận.',
        (Citation('rule','cloud',7,fact,source_name='cloud.pdf',page_range=(7,7)),),{'claims':[{'claim_id':'threshold','text':fact,
            'citation_ids':['rule']}]},[source],'vi',question='CPA 3,30 làm khóa luận được chưa?',complete_source_context=True)
    assert not result.abstained and '87 tín chỉ' in result.answer and 'cán bộ hướng dẫn' in result.answer
    assert '64' not in result.answer and len(result.claims)==3
    open_body=body[:body.index('* Điều kiện đăng ký chuyên đề:')]
    assert not list(_closed_star_criteria(open_body))
    assert not list(_closed_star_criteria(body.replace('* Điều kiện đăng ký chuyên đề:','* Chú thích:')))
    assert not list(_closed_star_criteria(body.replace('* Điều kiện đăng ký khóa luận:',
        '* Ví dụ điều kiện đăng ký khóa luận:')))


def test_improvement_recall_selects_normative_source_clauses_without_choosing_a_policy():
    from campusai.rag.source_windows import policy_field_evidence
    rules=['Người học có thể đăng ký học lại học phần đã đạt để cải thiện điểm.',
           'Không giải quyết học cải thiện khi điểm đã từ B trở lên.',
           'Sinh viên đã có điểm học phần đạt được phép học lại để cải thiện điểm.']
    docs=[{'doc_id':str(i),'items':[{'chunk_id':str(i),'page':3,'content':rule,'metadata':{}}]}
          for i,rule in enumerate(rules)]
    rows=policy_field_evidence('So sánh học cải thiện ở các nguồn?',docs)
    assert {row.doc_id for row in rows}=={'0','1','2'}
    assert [row.content for row in rows]==rules
    assert not policy_field_evidence('Học phí ở các nguồn?',docs)
    crossing={'doc_id':'cross','items':[{'chunk_id':'cross','page':2,'content':
        'Sinh viên không đạt phải học lại;\nc) Sinh viên được chọn một môn thay thế.','metadata':{}}]}
    assert not policy_field_evidence('Học cải thiện thế nào?',[crossing])


def test_verified_qualifier_cannot_be_hidden_by_high_word_overlap_or_add_another_group():
    from campusai.rag.policy_context import verified_field_context
    from campusai.rag.claims import Claim
    from campusai.rag.grounding import Citation
    rule='Đợt bổ sung dành cho người đã vắng đợt chính và được tổ chức sau đợt chính 19 ngày.'
    answer='Đợt bổ sung được tổ chức sau đợt chính 19 ngày.'
    claim=Claim('deadline',rule,'fact',1,('rule',),'supported',1.,('rule',),False)
    cite=Citation('rule','cloud',7,rule,source_name='cloud.pdf',page_range=(7,7))
    completed=verified_field_context('Đợt bổ sung được tổ chức sau bao lâu?',answer,[claim],[cite],'vi')
    assert completed and 'dành cho người đã vắng đợt chính' in completed[0] and not completed[2]
    assert verified_field_context('Sau bao lâu?',rule,[claim],[cite],'vi') is None
    from dataclasses import replace
    mixed=rule[:-1]+', trong khi đợt riêng dành cho nhóm khác diễn ra sau 27 ngày.'
    assert verified_field_context('Sau bao lâu?',answer,[replace(claim,text=mixed)],[cite],'vi') is None


def test_anchored_window_keeps_following_conditions_instead_of_unrelated_preface():
    from campusai.rag.source_windows import verbatim_window
    anchor='Students may repeat a passed course to improve their grade.'
    condition='The highest grade across all attempts is used as the official result.'
    text=('Unrelated preface about another topic.\n'*30+'Applicable group: enrolled students.\n'
        +anchor+'\n'+condition+'\n'+('Unrelated appendix.\n'*20))
    window=verbatim_window(text,'Can I improve a grade?',280,anchors=[anchor])
    assert anchor in window and condition in window and window in text and len(window)<=280


@pytest.mark.parametrize('dominant_hits',[3,6])
def test_comparison_context_shares_budget_by_document_not_hit_count(dominant_hits):
    import re
    from campusai.rag.grounding import build_context
    from campusai.rag.citation_handles import evidence_handles
    rows=[]
    for owner,count in [('cloud',dominant_hits),('wind',1),('rain',1)]:
        for i in range(count):
            body=(f'{owner} eligibility rule. Conditions remain applicable.\n'*80)
            rows.append(RetrievalResult(f'{owner}-{i}',owner,i+1,body,'text',1.,'test',{}))
    context=build_context(rows,10000,question='Compare eligibility rules across the three sources.',
        balanced=True,evidence_ids=evidence_handles(rows))
    sizes={owner:0 for owner in ('cloud','wind','rain')}
    for block in context.split('[EVIDENCE]')[1:]:
        owner=re.search(r'(?m)^doc_id=(.+)$',block)[1]
        content=block.partition('content:\n')[2].strip().removesuffix('[source_excerpt=true]').rstrip()
        sizes[owner]+=len(content)
        assert any(content in row.content for row in rows if row.doc_id==owner)
    assert len(context)<=10000 and min(sizes.values())>1800
    assert max(sizes.values())-min(sizes.values())<250


def test_comparison_context_returns_short_source_space_and_preserves_table_rows():
    import json
    from campusai.rag.grounding import build_context
    short='Cloud has no additional conditions.'
    table=json.dumps({'headers':['Item','Limit'],'rows':[['Wind','17'],['Rain','23']]})
    rows=[RetrievalResult('short','cloud',1,short,'text',1.,'test',{}),
          RetrievalResult('long','wind',2,'Wind eligibility conditions.\n'*160,'text',1.,'test',{}),
          RetrievalResult('table','rain',3,table,'table',1.,'test',{'table_id':'limits'})]
    context=build_context(rows,2500,question='Compare all sources.',balanced=True)
    assert len(context)<=2500 and short in context and table in context
    assert context.count('Wind eligibility conditions.')>40
    # A tiny budget still obeys the outer bound; no new content is generated.
    tiny=build_context(rows,80,question='Compare all sources.',balanced=True)
    assert len(tiny)<=80
