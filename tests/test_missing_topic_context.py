import pytest
from datetime import date

from campusai.rag.context import resolve_query


@pytest.mark.parametrize('question',[
    'What minimum latest process score is necessary?',
    'Which most recent assessment result does the rule use?',
    'Use only the uploaded rules.pdf. What is the required latest exam score?',
])
def test_assessment_recency_does_not_select_a_new_document_version(question):
    from campusai.rag.temporal import parse_temporal_intent
    assert parse_temporal_intent(question,reference_date=date(2032,1,1)).kind=='none'


def test_a_real_latest_document_request_still_selects_its_version():
    from campusai.rag.temporal import parse_temporal_intent
    for question in ['Use the latest regulation to check the process score.',
                     'What does the latest GPA policy require?']:
        assert parse_temporal_intent(question,reference_date=date(2032,1,1)).kind=='latest'


def test_named_regulation_is_the_local_subject_of_its_replacement_question():
    question = 'Use only the uploaded rules.pdf. When does the 2031 academic regulation take effect, and which earlier regulation does it replace?'
    assert not resolve_query(question).needs_clarification
    assert resolve_query('When does it take effect, and which earlier regulation does it replace?').needs_clarification


@pytest.mark.parametrize("question", [
    "bao nhiêu tín thì được", "bn tc là đủ vậy", "mấy tín nhỉ", "credits cần bao nhiêu",
    "thế tổng là mấy", "ủa ít nhất bao nhiêu tín mới ok", "thế sinh viên năm 2 thì sao",
    "năm hai có khác ko", "còn sv năm 2", "vậy n2 áp dụng kiểu gì", "em năm hai thì có được không",
    "mình có đủ điều kiện ko", "vậy em được chứ", "case t thì sao", "am I eligible vậy",
    "như của mình thì ok không bạn", "tính vậy em có bị gì không", "bằng này có dùng được không",
    "ielts này đủ chưa", "What about it?",
    "chưa có giấy chứng minh thì nộp sau được không",
    "không có giấy tờ thì bổ sung sau được chứ",
    "chứng chỉ này nộp sau được không",
])
def test_unanchored_reference_requests_clarification(question):
    resolved = resolve_query(question)
    assert resolved.needs_clarification
    assert resolved.resolved == question


@pytest.mark.parametrize("question", [
    "Use only the uploaded handbook.pdf. What is the code of that course?",
    "Using the selected document, does this rule apply to the current academic year?",
    "In the document, how many credits does this subject carry?",
])
def test_document_selection_does_not_resolve_a_missing_course_or_rule(question):
    assert resolve_query(question).needs_clarification
    assert not resolve_query(question, selected_text="Course CS210 has 4 credits.").needs_clarification
    assert not resolve_query(question, history=[{"role": "user", "content": "Explain course CS210."}]).needs_clarification


def test_deictic_course_with_an_explicit_local_identifier_is_self_contained():
    assert not resolve_query('Use only handbook.pdf. How many credits does this course (CS210) have?').needs_clarification


@pytest.mark.parametrize("question", [
    "Môn MAT1042 có bao nhiêu tín chỉ vậy?",
    "Mỗi học kỳ cần đăng ký ít nhất bao nhiêu tín chỉ?",
    "Bao nhiêu tín chỉ cần để tốt nghiệp ngành máy tính?",
    "Sinh viên năm 2 ngành máy tính học những môn nào?",
    "Am I eligible for admission with an IELTS score of 6.5?",
    "IELTS 6.5 có đáp ứng yêu cầu tuyển sinh thạc sĩ không?",
    "Credits required for graduating from the mathematics program?",
    "Chưa có chứng chỉ IELTS thì nộp hồ sơ thạc sĩ sau được không?",
    "Giấy chứng minh nhân dân cần nộp khi đăng ký thạc sĩ không?",
])
def test_self_contained_reference_keeps_its_subject(question):
    resolved = resolve_query(question)
    assert not resolved.needs_clarification
    assert resolved.resolved == question


def test_history_anchors_a_reference_but_cannot_replace_source_evidence():
    history = [{"role": "user", "content": "Điều kiện tốt nghiệp ngành máy tính"}]
    resolved = resolve_query("mấy tín nhỉ", history=history)
    assert not resolved.needs_clarification
    assert "untrusted user input" in resolved.resolved
    assert history[0]["content"] in resolved.resolved


def test_longer_discourse_followup_retains_its_user_topic():
    history = [{"role": "user", "content": "Điều kiện danh hiệu sinh viên giỏi"}]
    question = "còn phần rèn luyện thì cần tới loại nào"
    resolved = resolve_query(question, history=history)
    assert not resolved.needs_clarification
    assert history[0]["content"] in resolved.resolved


def test_unspecified_proof_document_retains_topic_and_versions_the_cache():
    topic = 'Điều kiện ngoại ngữ dự tuyển thạc sĩ trong thông báo.'
    request = 'Chưa có giấy chứng minh thì nộp sau được không?'
    resolved = resolve_query(request, history=[{'role': 'user', 'content': topic}])
    assert resolved.contextual and not resolved.needs_clarification
    assert topic in resolved.resolved and 'untrusted user input' in resolved.resolved
    assert resolved.cache_context()['version'] == 'request-context-v12'
    assistant_only = resolve_query(request, history=[{'role': 'assistant', 'content': topic}])
    assert assistant_only.needs_clarification


@pytest.mark.parametrize('course', ['Applied physics', 'Chemistry', 'Algebra', 'Computing', 'Linear systems'])
def test_explicit_subject_before_same_utterance_it_needs_no_history(course):
    question = f'The joint study plan lists {course}; what term and number of credits does it show?'
    resolved = resolve_query(question)
    assert not resolved.needs_clarification and not resolved.contextual
    assert resolved.resolved == question
    other = resolve_query(question, history=[{'role': 'user', 'content': 'Unrelated previous topic'}])
    assert other.resolved == question
    assert resolve_query(question, requires_context=True).needs_clarification


@pytest.mark.parametrize('question', ['What credits does it show?', 'What about that course?',
    'The plan lists it; what credits does it show?',
    'The plan lists that course; what credits does it show?',
    'The plan lists some course; what credits does it show?'])
def test_pronoun_or_unspecified_object_is_not_an_invented_local_topic(question):
    assert resolve_query(question).needs_clarification


@pytest.mark.parametrize('prefix', ['Use only the uploaded admissions.pdf. ',
                                   'Chỉ dùng tài liệu đã tải lên admissions.pdf. '])
def test_selecting_a_pdf_does_not_resolve_an_unnamed_programme(prefix):
    question = prefix + 'I want to choose it. What is its admission quota?'
    assert resolve_query(question).needs_clarification
    assert not resolve_query(prefix + 'What is the admission quota for programme AZ8?').needs_clarification
    resolved = resolve_query(question, history=[{'role': 'user', 'content': 'Programme AZ8'}])
    assert not resolved.needs_clarification
    assert 'Programme AZ8' in resolved.resolved


@pytest.mark.parametrize('question', [
    'phải đóng mấy tiền vậy', 'phai dong may tien vay?',
    'chuyển khoản được chứ hay phải tới nộp',
    'chuyen khoan duoc chu hay phai toi nop?',
    'được nhận những gì thế', 'duoc nhan nhung gi the?',
    'thưởng học phí của năm nào vậy', 'thuong hoc phi cua nam nao vay?',
    'tiếng Anh lúc ra trường cần bậc nào', 'tieng Anh luc ra truong can bac nao?',
    'cần học gì trước và mấy tín vậy', 'can hoc gi truoc va may tin vay?',
    'cần học trước những môn nào nhỉ', 'can hoc truoc nhung mon nao nhi?',
    'kỳ 5 thì bên nào phụ trách', 'ky 7 thi ben nao phu trach?',
])
def test_implicit_followup_uses_only_a_user_topic_and_clarifies_without_it(question):
    topic = 'Mình đang tìm hiểu chương trình Toán ứng dụng.'
    history = [{'role': 'user', 'content': topic},
               {'role': 'assistant', 'content': 'UNVERIFIED_FEE_987654321'}]
    resolved = resolve_query(question, history=history)
    assert resolved.contextual and not resolved.needs_clarification
    assert topic in resolved.resolved
    assert 'untrusted user input' in resolved.resolved
    assert 'UNVERIFIED_FEE_987654321' not in resolved.resolved
    assert resolve_query(question).needs_clarification
    assert resolve_query(question, history=history[1:]).needs_clarification
    selected = resolve_query(question, selected_text='Chương trình Khoa học vật liệu')
    assert not selected.needs_clarification
    assert 'Khoa học vật liệu' in selected.resolved


@pytest.mark.parametrize('question', [
    'Phải đóng mấy tiền lệ phí tuyển thạc sĩ vậy?',
    'Chuyển khoản lệ phí tuyển sinh thạc sĩ được không?',
    'Sinh viên Giỏi được nhận những gì thế?',
    'Thưởng học phí của năm nào cho sinh viên trúng tuyển xuất sắc?',
    'Tiếng Anh lúc ra trường ngành Toán cần bậc nào?',
    'Cần học gì trước môn Đại số tuyến tính và mấy tín vậy?',
    'Cần học trước những môn nào để đăng ký CS210?',
    'Kỳ 5 của chương trình Khoa học máy tính thì bên nào phụ trách?',
])
def test_explicit_subject_does_not_inherit_an_earlier_unrelated_topic(question):
    history = [{'role': 'user', 'content': 'Quy định học phí ngành Lịch sử.'}]
    resolved = resolve_query(question, history=history)
    assert not resolved.contextual and not resolved.needs_clarification
    assert resolved.resolved == question
