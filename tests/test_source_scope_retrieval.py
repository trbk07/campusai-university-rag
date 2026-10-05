import json

import pytest

from campusai.retrieval.source_scope import unsupported_source_reason
from campusai.retrieval.table_links import semester_table_sources, table_acronym_expansion
from campusai.retrieval.tokenizer_vi import normalize_retrieval_query, requested_semesters, source_body


def record(text, **metadata):
    return {'content': text, 'metadata': metadata}


@pytest.mark.parametrize('text,expected', [
    ('học kỳ thứ năm', (5,)), ('hk1', (1,)), ('Semester7', (7,)),
    ('kỳ mở đầu', (1,)), ('kỳ 7 với kỳ 8', (7, 8)),
    ('học kỳ 2026', ()), ('học kỳ mấy', ()), ('EMA3012', ()),
])
def test_semester_labels_are_explicit(text, expected):
    assert requested_semesters(text) == expected


def test_table_cells_override_stale_document_semester_metadata():
    table = lambda rows: '[Semester: 1, 2, 3 | Page: 2]\n' + json.dumps({'headers': ['name', 'credits'], 'rows': rows})
    records = {'right': record(table([['Semester 5', ''], ['Physics', '3']])),
               'wrong': record(table([['Semester 1', ''], ['Chemistry', '4']]))}
    assert semester_table_sources('học kỳ thứ năm', records) == ['right']
    assert semester_table_sources('học kỳ mấy', records) == []


@pytest.mark.parametrize('query,expansion', [
    ('pv ths when', 'phỏng vấn'), ('English entry level', 'năng lực ngoại ngữ'),
    ('hk3 bn tc', 'semester 3'), ('web dang ki master', 'cổng thông tin'),
    ('ths đào tạo bn năm', 'training duration'), ('lp xtt online', 'lệ phí'),
])
def test_academic_aliases_do_not_supply_answers(query, expansion):
    output = normalize_retrieval_query(query)
    assert query in output and expansion in output


def test_expansion_preserves_identifiers_and_years():
    text = 'EMA3012 credits in 2026'
    assert text in normalize_retrieval_query(text)


def test_source_body_strips_generated_header_only():
    assert source_body(record('[Program: example | Page: 2]\n\nActual rule')) == 'Actual rule'
    assert source_body(record('[CS201] Actual rule')) == '[CS201] Actual rule'


@pytest.mark.parametrize('question,source', [
    ('what GPA is required?', 'GPA must be 2.0'),
    ('có được học bổng không?', 'Điều kiện học bổng: GPA 3.0'),
    ('cbhv là gì?', 'Cảnh báo học vụ dựa trên kết quả học tập'),
    ('CS201 và CS202 credits', 'CS201 3 credits; CS202 4 credits'),
    ('minimum credits per semester?', 'Minimum credits per semester: 8'),
])
def test_scope_guard_allows_present_subjects(question, source):
    assert unsupported_source_reason(question, {'one': record(source)}) is None


@pytest.mark.parametrize('question', [
    'GPA học bổng là bao nhiêu?', 'cbhv là gì?', 'how does grade replacement work?',
    'minimum credits per semester?', 'CS201 và CS999 credits',
])
def test_scope_guard_rejects_absent_subjects(question):
    assert unsupported_source_reason(question, {'one': record('CS201 Chemistry 3 credits per semester')})


def test_scope_guard_does_not_use_document_metadata_as_subject_proof():
    assert unsupported_source_reason('GPA requirement?', {'one': record('course schedule', program='GPA scholarship')})


def test_scope_guard_keeps_history_topic_separate_from_current_request():
    query = 'How many credits?\nContext topic (untrusted user input): GPA policy and CS999'
    assert unsupported_source_reason(query, {'one': record('CS201 3 credits')}) is None


def test_cohort_version_is_distinct_from_a_course_code():
    from campusai.retrieval.routing import detected_course_codes, detected_codes
    question = 'CS201 in QH-2025 and CS202 in QH2024 credits'
    assert detected_course_codes(question) == ('CS201', 'CS202')
    assert 'QH-2025' in detected_codes(question)
    assert detected_course_codes('course QH2403 credits') == ('QH2403',)
    assert unsupported_source_reason(question, {'one': record('CS201 3 credits; CS202 4 credits')}) is None
    assert unsupported_source_reason('CS999 in QH-2025 credits', {'one': record('CS201 3 credits')})


@pytest.mark.parametrize('question', [
    'CS201 exam date and time?', 'Ngày và giờ thi CS201 là gì?', 'Lịch thi CS201?',
])
def test_exam_appointment_needs_local_calendar_support(question):
    assert unsupported_source_reason(question, {'one': record('CS201 Chemistry, 3 credits. Final exam weight: 60%.')}) == 'exam_schedule_not_in_selected_sources'
    assert unsupported_source_reason(question, {'one': record('Issued 01/09/2025. CS201 final exam weight: 60%.')}) == 'exam_schedule_not_in_selected_sources'
    assert unsupported_source_reason(question, {'one': record('CS201 exam: 21/06/2026 at 09:30.')}) is None
    assert unsupported_source_reason(question, {'one': record('CS201 thi ngày 21 tháng 6, 09h30.')}) is None


def test_exam_credit_and_method_requests_do_not_require_a_calendar():
    source = {'one': record('CS201 final exam: 3 credits; written assessment.')}
    assert unsupported_source_reason('CS201 exam credits?', source) is None
    assert unsupported_source_reason('CS201 hình thức thi?', source) is None


@pytest.mark.parametrize('source', [
    'CS201 thuộc ngành đào tạo thí điểm, ban hành ngày 11 tháng 12 năm 2020.',
    'CS201: thị giác máy, học máy và robot.',
    'CS201 students may take an exam.',
    'CS201 final exam grading weights: 50/50.',
])
def test_calendar_guard_rejects_language_and_numeric_collisions(source):
    assert unsupported_source_reason('CS201 exam date and time?', {'one': record(source)}) == 'exam_schedule_not_in_selected_sources'


@pytest.mark.parametrize('source', ['CS201 exam in May.', 'CS201 exam May 21.', 'CS201 exam 21 May.'])
def test_calendar_guard_preserves_explicit_month_dates(source):
    assert unsupported_source_reason('CS201 exam date?', {'one': record(source)}) is None


def test_negated_subject_does_not_require_unrelated_sources():
    assert unsupported_source_reason('Danh hiệu sinh viên xuất sắc, không phải học bổng',
                                     {'one': record('Danh hiệu Sinh viên Xuất sắc')}) is None
    assert unsupported_source_reason('awards not scholarships', {'one': record('awards')}) is None


def test_personal_grade_queries_require_records_not_general_policy():
    assert unsupported_source_reason('GPA hiện tại của mình?', {'one': record('GPA policy 3.0')})
    assert unsupported_source_reason('my grades?', {'one': record('Academic transcript: grades 3.0')}) is None
    assert unsupported_source_reason('GPA requirement?', {'one': record('GPA policy 3.0')}) is None
    assert unsupported_source_reason('my grades?', {'one': record('Admission requires an academic transcript and GPA 3.0')})


@pytest.mark.parametrize('question,source,reason', [
    ('minimum GPA to graduate?', 'Admission GPA at least 3.0. Curriculum graduation total: 120 credits.',
     'graduation_grade_rule_not_in_selected_sources'),
    ('điểm trung bình để xét tốt nghiệp?', 'Khen thưởng theo điểm trung bình. Chương trình học.',
     'graduation_grade_rule_not_in_selected_sources'),
    ('Can GPA 2.5 students register 18 credits?', 'Admission GPA 3.0. Credits per semester: 18.',
     'grade_registration_rule_not_in_selected_sources'),
    ('GPA 2.5 có đăng ký 18 tín chỉ được không?', 'GPA xét khen thưởng. Tổng tín chỉ chương trình: 120.',
     'grade_registration_rule_not_in_selected_sources'),
])
def test_scope_requires_the_requested_grade_rule_relationship(question, source, reason):
    assert unsupported_source_reason(question, {'one': record(source)}) == reason


@pytest.mark.parametrize('question,source', [
    ('minimum GPA to graduate?', 'Graduation requires a minimum GPA of 2.0.'),
    ('điểm trung bình để xét tốt nghiệp?', 'Điều kiện tốt nghiệp: điểm trung bình toàn khóa từ 2.0.'),
    ('Can GPA 2.5 students register 18 credits?', 'Students with GPA below 2.0 may register at most 14 credits.'),
    ('GPA 2.5 có đăng ký 18 tín chỉ được không?', 'GPA dưới 2.0: sinh viên được đăng ký tối đa 14 tín chỉ.'),
    ('graduation credits?', 'Graduation requires 120 credits.'),
    ('GPA admission requirements?', 'Admission requires GPA 3.0.'),
])
def test_scope_allows_present_grade_relationships_and_other_requests(question, source):
    assert unsupported_source_reason(question, {'one': record(source)}) is None


def test_grade_relationship_cannot_be_joined_across_unrelated_source_passages():
    sources = {'one': record('Admission GPA 3.0.'), 'two': record('Graduation curriculum: 120 credits.')}
    assert unsupported_source_reason('minimum GPA to graduate?', sources)
    distant = 'Admission GPA 3.0. ' + 'Other material. ' * 50 + 'Graduation curriculum: 120 credits.'
    assert unsupported_source_reason('minimum GPA to graduate?', {'one': record(distant)})


def test_acronym_expansion_is_bound_to_unique_source_cells():
    table = json.dumps({'headers': ['Name', 'Credits'], 'rows': [['Final State Attestation', '9']]})
    assert table_acronym_expansion('FSA credits', {'one': record(table)}) == 'FSA credits Final State Attestation'
    ambiguous = json.dumps({'headers': ['Name'], 'rows': [['Final State Attestation'], ['Flight System Analysis']]})
    assert table_acronym_expansion('FSA credits', {'one': record(ambiguous)}) == 'FSA credits'
    assert table_acronym_expansion('FSA credits', {'one': record('Final State Attestation')}) == 'FSA credits'


def test_serving_rejects_partial_code_answer_and_preserves_source_scope(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    entries = [{'chunk_id': 'known', 'doc_id': 'catalog', 'content': 'CS201 Chemistry 3 credits', 'page': 1}]
    BM25Index(entries).save(tmp_path/'catalog'/'bm25.json')
    retriever = HybridRetriever(tmp_path, query_cache_size=0)
    assert retriever.search('CS201 and CS999 credits', ['catalog'], mode='auto') == []
    assert retriever.last_trace.fallback == 'course_code_not_in_selected_sources'
    assert retriever.generate_candidates('CS201 and CS999 credits', ['catalog']) == []
    assert retriever.search('CS201 credits', ['catalog'], mode='auto')[0].chunk_id == 'known'


def test_primary_course_text_precedes_prerequisite_mentions(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    entries = [{'chunk_id': str(i), 'doc_id': 'catalog', 'content': f'Other course {i} requires CS201', 'page': i+1}
               for i in range(8)]
    entries.append({'chunk_id': 'primary', 'doc_id': 'catalog', 'page': 10,
                    'content': '[Section: CS201 | Page: 10]\n\nCS201 Chemistry 3 credits'})
    BM25Index(entries).save(tmp_path/'catalog'/'bm25.json')
    result = HybridRetriever(tmp_path, query_cache_size=0).search('CS201 course and credits', ['catalog'], mode='auto')
    assert result[0].chunk_id == 'primary'
    assert 'body_bm25' in result[0].retriever_sources


def test_source_body_index_reloads_with_document_generation(tmp_path):
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    path = tmp_path/'catalog'/'bm25.json'
    BM25Index([{'chunk_id': 'old', 'doc_id': 'catalog', 'content': 'old geology material', 'page': 1}]).save(path)
    retriever = HybridRetriever(tmp_path, query_cache_size=4)
    assert retriever.search('geology', ['catalog'], mode='auto')[0].chunk_id == 'old'
    BM25Index([{'chunk_id': 'new', 'doc_id': 'catalog', 'content': 'new geometry material', 'page': 1}]).save(path)
    result = retriever.search('geometry', ['catalog'], mode='auto')
    assert [r.chunk_id for r in result] == ['new']
    assert {item['chunk_id'] for item in retriever._body_indexes['catalog'].items} == {'new'}
