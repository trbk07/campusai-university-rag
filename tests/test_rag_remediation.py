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
