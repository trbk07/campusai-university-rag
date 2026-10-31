"""Visible marker checks: formatting equivalence must not permit changed facts."""
from dataclasses import replace
import pytest
from campusai.rag.claims import Claim
from campusai.rag.presentation import presentation_conflicts
from campusai.rag.presentation import omit_unverified_context
from campusai.rag.cache import build_rag_cache_key
from campusai.rag.grounding import GroundedAnswerGenerator
from tests.test_basic_rag import FakeLLM, evidence


def supported(text):
    return [Claim('one', text, citation_ids=('c1',), status='supported')]


def test_optional_unproved_scope_is_removed_without_whitelisting_a_fact():
    claim=supported('Quy chế áp dụng từ khóa tuyển sinh năm 2031.')
    assert omit_unverified_context('Quy chế 2468 áp dụng từ năm 2031.',claim,
        'Quy chế 2468 áp dụng khóa nào?')=='Quy chế áp dụng từ năm 2031.'
    assert '2468' in omit_unverified_context('Quy chế 2468 áp dụng từ năm 2031.',claim,
        'Quy chế 2468 đúng không?')
    assert '2469' in omit_unverified_context('Quy chế 2469 áp dụng từ năm 2031.',claim,
        'Quy chế 2468 áp dụng khóa nào?')
    assert omit_unverified_context('Điểm 6,9 (thang điểm 10) quy đổi thành B.',supported('B thuộc khoảng 6,2 đến 7,4.'),
        '6,9 điểm quy đổi ra sao?')=='Điểm 6,9 quy đổi thành B.'


def test_requested_scale_label_does_not_whitelist_its_digit_as_a_value():
    claim=supported('B quy đổi thành 3,2.')
    assert not presentation_conflicts('B là 3,2 trên thang điểm 5.',claim,question='B quy đổi thang 5 là mấy?')
    assert presentation_conflicts('B là 5 trên thang điểm 5.',claim,question='B quy đổi thang 5 là mấy?')
    assert presentation_conflicts('B là 3,2 trên thang điểm 6.',claim,question='B quy đổi thang 5 là mấy?')


def test_credit_input_is_exempt_only_after_a_literal_threshold_application():
    claim=supported('Nhắc nhở một cấp đối với học viên có số TC không đạt lớn hơn 11.')
    question='Em trượt 13 tín có bị nhắc nhở không?'
    answer='Nhắc nhở một cấp đối với học viên có số TC không đạt lớn hơn 11. Với 13 tín chỉ không đạt, điều kiện này được đáp ứng.'
    assert not presentation_conflicts(answer,claim,question=question)
    assert presentation_conflicts(answer.replace('13','10'),claim,question=question.replace('13','10'))
    assert presentation_conflicts(answer.replace('13 tín chỉ','13 USD'),claim,question=question)
    assert presentation_conflicts('Không. '+answer,claim,question=question)


def test_accented_requested_level_is_context_and_not_a_factual_quantity():
    claim=supported('Nhóm chuẩn được đăng ký tối đa 17 TC.')
    question='Cảnh báo mức 3 thì đăng ký thế nào?'
    assert not presentation_conflicts('Ở mức 3, nhóm chuẩn được đăng ký tối đa 17 TC.',claim,question=question)
    assert presentation_conflicts('Ở mức 3, nhóm chuẩn được đăng ký tối đa 3 TC.',claim,question=question)


@pytest.mark.parametrize('rule,question,answer',[
    ('Được đăng ký tối đa 11 tín chỉ trong kỳ phụ.','Đăng ký 13 tín kỳ phụ được không?',
     'Tối đa 11 tín chỉ; không thể đăng ký 13 tín chỉ.'),
    ('Được đề nghị trong thời hạn 11 ngày.','Sau 13 ngày còn kịp không?',
     'Không còn kịp sau 13 ngày; thời hạn là 11 ngày.'),
])
def test_outside_upper_bound_can_repeat_only_the_same_typed_input(rule,question,answer):
    assert not presentation_conflicts(answer,supported(rule),question=question)
    assert presentation_conflicts(answer.replace('13','10'),supported(rule),question=question.replace('13','10'))
    assert presentation_conflicts('Bạn có thể đăng ký 13 tín chỉ.',supported(rule),question=question)
    assert presentation_conflicts('Được đăng ký 13 tín chỉ không đạt.',supported(rule),question=question)


def test_requested_admission_notice_year_is_scope_not_an_unproved_quantity():
    question = 'What institution code is stated in the 2025 undergraduate admission notice?'
    claim = supported('Mã cơ sở đào tạo trong tuyển sinh: QHI')
    answer = 'The 2025 undergraduate admission notice specifies institution code QHI.'
    assert not presentation_conflicts(answer, claim, question=question)
    assert presentation_conflicts(answer.replace('2025', '2026'), claim, question=question)
    assert presentation_conflicts('The institution offers 2025 credits.', claim, question=question)


@pytest.mark.parametrize('answer,claim', [
    ('The deadline is 17:00 on August 30, 2022.', 'The deadline is 17h00 on 30/08/2022.'),
    ('The result is announced on 9 September 2022.', 'The result is announced on 09/09/2022.'),
    ('The deadline is 08:05 on 2024-02-29.', 'The deadline is 8h05 on 29/02/2024.'),
])
def test_whole_calendar_and_clock_identity_survives_presentation_format(answer, claim):
    assert not presentation_conflicts(answer, supported(claim))


@pytest.mark.parametrize('source', [
    'Thông báo được ban hành ngày 14 tháng 06 năm 2021.',
    'Thong bao duoc ban hanh ngay 14 thang 6 nam 2021.',
])
def test_vietnamese_whole_date_matches_english_without_dropping_components(source):
    assert not presentation_conflicts('The notice was issued on June 14, 2021.', supported(source))
    assert presentation_conflicts('The notice was issued on June 15, 2021.', supported(source))
    assert presentation_conflicts('The notice was issued on July 14, 2021.', supported(source))
    assert presentation_conflicts('The notice was issued on June 14, 2022.', supported(source))


def test_decomposed_vietnamese_dates_and_invalid_calendar_values():
    import unicodedata
    source=unicodedata.normalize('NFD','Hạn nộp là ngày 29 tháng 2 năm 2024 lúc 08h05.')
    assert not presentation_conflicts('The deadline is 08:05 on February 29, 2024.', supported(source))
    assert presentation_conflicts('The deadline is February 28, 2023.',
                                  supported('Hạn nộp là ngày 29 tháng 2 năm 2023.'))


@pytest.mark.parametrize('answer', [
    'The deadline is 17:17 on 30/08/2022.',
    'The deadline is 00:17 on 30/08/2022.',
    'The deadline is 17:00 on 08/30/2022.',
    'The deadline is 17:00 on 30/09/2022.',
    'The deadline is 17:00 on August 30, 2023.',
    'The deadline is 24:00 on 30/08/2022.',
])
def test_changed_or_invalid_time_and_date_are_not_licensed_by_number_overlap(answer):
    assert presentation_conflicts(answer, supported('The deadline is 17h00 on 30/08/2022.'))


def test_calendar_value_roles_do_not_collapse_into_a_bag_of_numbers():
    assert presentation_conflicts('The deadline is 02/01/2022.', supported('The deadline is 01/02/2022.'))
    assert presentation_conflicts('The deadline is January 2, 2022.', supported('The deadline is 1 February 2022.'))
    assert presentation_conflicts('The deadline is 29/02/2023.', supported('The deadline is 28/02/2023.'))


@pytest.mark.parametrize('visible,claim', [('ABC7101', 'ABC 7101'), ('ABC 7101', 'ABC7101'),
    ('abc7101', 'abc 7101'), ('ABC\n7101', 'ABC7101'), ('UNI.ABC7101A', 'UNI.ABC 7101A')])
def test_code_spacing_does_not_create_a_new_visible_entity(visible, claim):
    assert not presentation_conflicts(f'Course {visible} has 8 credits.', supported(f'Course {claim} has 8 credits.'))


@pytest.mark.parametrize('visible', ['XYZ 7101', 'ABC 7102', 'ABC 7101A', 'UNI.ABC7101'])
def test_changed_prefix_digits_suffix_or_namespace_stays_unsupported(visible):
    assert presentation_conflicts(f'Course {visible} has 8 credits.', supported('Course ABC 7101 has 8 credits.'))


@pytest.mark.parametrize('answer', ['Course ABC7101 has 9 credits.', 'Course ABC7101 has 8 USD.',
                                   'Course ABC7101 has 8 credits in 2026.'])
def test_code_normalization_does_not_relax_number_unit_or_year_checks(answer):
    assert presentation_conflicts(answer, supported('Course ABC 7101 has 8 credits.'))


def test_ordinary_words_and_years_are_not_merged_into_course_markers():
    assert not presentation_conflicts('We have 300 credits in 2025.', supported('The programme has 300 credits in 2025.'))
    assert presentation_conflicts('We have 301 credits in 2025.', supported('The programme has 300 credits in 2025.'))


def test_opposed_negation_is_still_detected_across_code_spacing():
    assert presentation_conflicts('Course ABC7101 is not required.', supported('Course ABC 7101 is required.'))
    assert not presentation_conflicts('Course ABC7101 is required.', supported('Course ABC 7101 is required.'))


def test_same_course_formats_publish_through_the_generator_without_rewriting_the_answer():
    import json
    table = {'headers': ['Course code', 'Credits'], 'rows': [['ABC 7101', '8']]}
    result = replace(evidence(content=json.dumps(table)), content_type='table')
    payload = {'answer': 'According to the document, course ABC7101 carries 8 credits.',
        'confidence': 'high', 'abstained': False, 'citations': [{'chunk_id': 'c1'}],
        'claims': [{'claim_id': 'one', 'text': 'Course ABC 7101 has 8 credits.', 'citation_ids': ['c1']}]}
    # Exercise provider presentation rather than the bounded local lookup.
    answer = GroundedAnswerGenerator(FakeLLM(payload), source_citations=True).answer('Report the credit value for ABC7101.', [result])
    assert not answer.abstained and answer.answer == payload['answer']
    payload['answer'] = payload['answer'].replace('ABC7101', 'XYZ7101')
    assert GroundedAnswerGenerator(FakeLLM(payload), source_citations=True).answer('How many credits?', [result]).abstained


def test_pre_fix_answer_cache_cannot_reuse_incomplete_quotes_or_false_abstentions():
    args = dict(question='Course credits?', language='en', doc_ids=['doc-1'], filters=None,
                top_k=5, mode='hybrid', corpus_version='v1', model='offline', context_budget={})
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, grounding_policy_version='grounding-v6')


def test_proved_article_label_does_not_become_an_unproved_quantity():
    claims=supported('The threshold is 10 percent.')
    assert not presentation_conflicts('Under Article 9, the threshold is 10 percent.',claims,locations={('article','9')})
    assert presentation_conflicts('Under Article 9, the threshold is 9 percent.',claims,locations={('article','9')})
    assert presentation_conflicts('Under Article 8, the threshold is 10 percent.',claims,locations={('article','9')})


def test_heading_proofs_require_actual_directly_cited_source_content():
    from campusai.rag.evidence import EvidenceRegistry
    from campusai.rag.grounding import Citation
    from campusai.rag.presentation import location_proofs
    from campusai.retrieval.hybrid import RetrievalResult
    result=RetrievalResult('source','doc',3,'Điều 9: The threshold is 10 percent.','text',1.0,'source',{})
    registry=EvidenceRegistry([result])
    citation=Citation('source','doc',3,'The threshold is 10 percent.')
    proofs=location_proofs([citation],registry)
    assert ('article','9') in proofs and ('page','3') in proofs
    assert ('article','8') not in proofs and ('page','9') not in proofs


@pytest.mark.parametrize('question,answer,claim', [
    ('Use the adjusted UET curriculum issued in 2023. What is the programme duration?',
     'Theo chương trình đào tạo ban hành năm 2023, thời gian đào tạo là 4 năm.',
     '- Thời gian đào tạo: 4 năm'),
    ('For admission cohort 2022, which PO includes teamwork skills?',
     'For admission cohort 2022, PO3 includes teamwork skills.',
     'PO3: Có kỹ năng giao tiếp, làm việc nhóm, phát hiện và giải quyết vấn đề.'),
])
def test_repeated_question_scope_year_is_not_treated_as_a_new_answer_fact(question, answer, claim):
    assert not presentation_conflicts(answer, supported(claim), question=question)


def test_scope_year_allowance_does_not_hide_a_changed_answer_value_or_unasked_year():
    question='For admission cohort 2022, what is the programme duration?'
    claim='The programme duration is 4 years.'
    assert presentation_conflicts('For admission cohort 2022, the programme duration is 5 years.',
                                  supported(claim), question=question)
    assert presentation_conflicts('For admission cohort 2022, the programme duration is 4 years in 2023.',
                                  supported(claim), question=question)


def test_repeated_semester_or_article_scope_is_not_treated_as_an_unverified_answer_number():
    question='In semester 4 of this curriculum, how many credits does the course carry?'
    claim='Strength of Materials carries 3 credits.'
    assert not presentation_conflicts('In semester 4, Strength of Materials carries 3 credits.',
                                      supported(claim), question=question)
    assert presentation_conflicts('In semester 5, Strength of Materials carries 3 credits.',
                                  supported(claim), question=question)
    question='What does Article 2 state about the admission cohort?'
    assert not presentation_conflicts('Article 2 applies from admission cohort 2022.',
                                      supported('The admission cohort is 2022.'), question=question)


@pytest.mark.parametrize('locator', ['7.2(a)', '9.1', '12.4.3(b)', '15'])
def test_hierarchical_source_locator_is_masked_as_one_whole_value(locator):
    question = f'Under section {locator}, how many bonus points apply?'
    assert not presentation_conflicts(f'Under section {locator}, 3.0 bonus points apply.',
        supported('Được cộng 3.0 điểm.'), question=question)
    assert presentation_conflicts(f'Under section {locator}, 2.0 bonus points apply.',
        supported('Được cộng 3.0 điểm.'), question=question)
    assert presentation_conflicts('Under section 99.1, 3.0 bonus points apply.',
        supported('Được cộng 3.0 điểm.'), question=question)
    assert not presentation_conflicts(f'Section {locator}. 3.0 bonus points apply.',
        supported('Được cộng 3.0 điểm.'), question=question)


def test_route_identifier_requires_both_question_scope_and_a_physical_quote():
    question = 'What minimum course count applies for ROUTE19+?'
    answer = 'For ROUTE19+, at least 04 courses are required.'
    claims = supported('Tích lũy trước tối thiểu 04 học phần.')
    assert not presentation_conflicts(answer, claims, question=question, source_scope_codes={'route19'})
    assert presentation_conflicts(answer, claims, question=question)
    assert presentation_conflicts(answer.replace('ROUTE19', 'ROUTE20'), claims,
        question=question, source_scope_codes={'route19'})
    assert presentation_conflicts(answer.replace('04 courses', '19 courses'), claims,
        question=question, source_scope_codes={'route19'})


def test_affirmative_confirmation_cannot_override_a_contradictory_reviewed_credit_value():
    question='The field knowledge block requires 20 credits. Is that correct? State the source value.'
    answer='Yes, that is correct. The general knowledge block requires 26 credits.'
    claims=supported('The general knowledge block requires 26 credits.')
    assert presentation_conflicts(answer, claims, question=question)


def test_correction_to_a_wrong_question_premise_still_passes_when_cited():
    question='The field knowledge block requires 20 credits. Is that correct? State the source value.'
    answer='No. The field knowledge block requires 19 credits.'
    claims=supported('The field knowledge block requires 19 credits.')
    assert not presentation_conflicts(answer, claims, question=question)


def test_requested_grade_scale_label_is_not_a_converted_value():
    claims=supported('B quy đổi thành 2,3;')
    question='Điểm chữ B và điểm hệ 4 là gì?'
    assert not presentation_conflicts('B quy đổi hệ 4 là 2,3.',claims,question=question)
    assert presentation_conflicts('B quy đổi hệ 5 là 2,3.',claims,question=question)
    assert presentation_conflicts('B quy đổi hệ 4 là 4.',claims,question=question)


def test_optional_scale_decoration_does_not_hide_a_wrong_converted_value():
    from campusai.rag.presentation import omit_unverified_context
    claims=supported('B quy đổi thành 2,3;')
    question='Điểm chữ B quy đổi ra sao?'
    cleaned=omit_unverified_context('B quy đổi thành 2,3 điểm theo thang điểm 4.',claims,question)
    assert 'thang điểm 4' not in cleaned and '2,3' in cleaned
    assert not presentation_conflicts(cleaned,claims,question=question)
    wrong=omit_unverified_context('B quy đổi thành 2,4 điểm theo thang điểm 4.',claims,question)
    assert presentation_conflicts(wrong,claims,question=question)
    assert 'thang điểm 4' in omit_unverified_context('B quy đổi thành 2,3 điểm theo thang điểm 4.',claims,'B quy đổi trên thang điểm 4 ra sao?')


def test_institution_expansion_needs_a_literal_source_name_for_each_side():
    from campusai.rag.presentation import institution_names_supported
    from campusai.retrieval.hybrid import RetrievalResult
    source=RetrievalResult('s','d',1,'Trường Đại học Sao Bắc và Đại học Âm nhạc Miền Tây.','text',1,'test',{})
    assert institution_names_supported('Đại học Sao Bắc và Đại học Âm nhạc Miền Tây có quy định khác nhau.',[source])
    assert not institution_names_supported('Đại học Sao Bắc và Đại học Sao Nam (WIM) có quy định khác nhau.',[source])
    assert institution_names_supported('SBU và WIM có quy định khác nhau.',[source])


def test_visible_prose_quote_must_support_the_claim_not_another_paragraph():
    from campusai.retrieval.hybrid import RetrievalResult
    result=RetrievalResult('c1','doc',1,'The library opens on Monday. The registrar closes on Friday.','text',1.0,'source',{})
    payload={'answer':'The registrar closes on Friday.','abstained':False,'confidence':'high',
        'claims':[{'claim_id':'one','text':'The registrar closes on Friday.','citation_ids':['c1']}],
        'citations':[{'chunk_id':'c1','page':1,'quote':'The library opens on Monday.'}]}
    response=GroundedAnswerGenerator(FakeLLM(payload)).answer('When does the registrar close?',[result],language='en')
    assert response.abstained


def test_exact_source_claim_selects_its_own_paragraph_instead_of_a_common_word_window():
    from campusai.rag.source_citations import source_quote
    from campusai.retrieval.hybrid import RetrievalResult
    text=('The student study result is assessed annually. '*45)+ 'Article 6: The student study result threshold is at least 3.0.'
    result=RetrievalResult('c1','doc',1,text,'text',1.0,'source',{})
    quote=source_quote(result,[{'text':'The student study result threshold is at least 3.0.','citation_ids':['c1']}])
    assert 'Article 6:' in quote and 'at least 3.0.' in quote and len(quote)<=1200
def test_bilingual_question_scope_keeps_the_same_locator_without_licensing_other_numbers():
    from campusai.rag.presentation import presentation_conflicts
    from campusai.rag.claims import Claim
    claim=Claim('award','A third prize receives 4.5 points.','fact',1,('c',),
                'supported',1.0,('c',),False)
    question='Under section 7.2(a), how many bonus points does a third prize receive?'
    assert not presentation_conflicts('Theo mục 7.2(a), giải ba được cộng 4.5 điểm.',[claim],
                                      question=question,locations={('page','8')})
    assert presentation_conflicts('Theo mục 9.9(a), giải ba được cộng 4.5 điểm.',[claim],
                                  question=question,locations={('page','8')})
    assert presentation_conflicts('Theo mục 7.2(a), giải ba được cộng 5.5 điểm.',[claim],
                                  question=question,locations={('page','8')})

