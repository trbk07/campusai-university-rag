import json
from dataclasses import replace
import pytest

from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation
from campusai.rag.source_citations import source_quote
from tests.test_basic_rag import FakeLLM, evidence


def payload(text='MATH101 is required.', chunk='c1'):
    return {'answer': text, 'confidence': 'high', 'abstained': False,
            'claims': [{'claim_id': 'one', 'text': text, 'citation_ids': [chunk]}],
            'citations': [{'chunk_id': chunk}]}


def test_wrapped_one_column_prose_preserves_the_complete_source_sentence():
    rows=[['Applications must be submitted no later than 11'],['days after the assessment date.'],
          ['Other independent requirements apply.']]
    item=replace(evidence(content=json.dumps({'headers':['Regulations'],'rows':rows})),content_type='table')
    text='Applications must be submitted no later than 11 days after the assessment date.'
    answer=GroundedAnswerGenerator(FakeLLM(payload(text)),source_citations=True).answer('When are applications due?',[item],'en')
    assert not answer.abstained
    quote=json.loads(answer.citations[0].quote)
    assert quote==rows[:2] or quote.get('rows')==rows[:2]
    assert validate_citation(answer.citations[0],item).valid
    wrong=payload(text.replace('11','12'))
    assert GroundedAnswerGenerator(FakeLLM(wrong),source_citations=True).answer('When are applications due?',[item],'en').abstained


def test_independent_one_column_records_cannot_be_joined_into_a_new_fact():
    rows=[['Student Alpha: the permitted credit limit is 13'],['student Beta: the permitted credit limit is 21']]
    item=replace(evidence(content=json.dumps({'headers':['Students'],'rows':rows})),content_type='table')
    bad=payload('Student Alpha has a permitted credit limit of 21.')
    assert GroundedAnswerGenerator(FakeLLM(bad),source_citations=True).answer('What is the credit limit for Student Alpha?',[item],'en').abstained


def test_programme_group_is_preserved_when_adjacent_degrees_share_identical_values():
    headers = ['Chương trình', 'Người học', 'Thời gian', 'Khối lượng tối thiểu']
    rows = [['Kỹ sư', 'Tốt nghiệp cử nhân theo chương trình tích hợp', '1,5 năm', '48 tín chỉ'],
            ['Thạc sĩ', 'Tốt nghiệp cử nhân', '2 năm', '60 tín chỉ'],
            ['', 'Tốt nghiệp cử nhân theo chương trình tích hợp', '1,5 năm', '48 tín chỉ'],
            ['Tiến sĩ', 'Tốt nghiệp thạc sĩ', '3 năm', '106 tín chỉ']]
    item = replace(evidence(content=json.dumps({'headers': headers, 'rows': rows}, ensure_ascii=False)),
                   content_type='table')
    claim = {'text': 'Thạc sĩ | Tốt nghiệp cử nhân theo chương trình tích hợp | 1,5 năm | 48 tín chỉ',
             'citation_ids': [item.chunk_id]}
    quote = source_quote(item, [claim], question='Khối lượng của chương trình thạc sĩ trong bảng là bao nhiêu?')
    assert json.loads(quote) == {'scope': 'Thạc sĩ', 'headers': headers, 'rows': rows[1:3]}
    assert validate_citation({'chunk_id': item.chunk_id, 'page': item.page, 'quote': quote}, item).valid
    assert source_quote(item, [claim], question='Khối lượng của chương trình tiến sĩ trong bảng là bao nhiêu?') is None
    other = {**claim, 'text': 'Khối lượng của chương trình kỹ sư dành cho người tốt nghiệp cử nhân là 60 tín chỉ.'}
    quote = source_quote(item, [other], question='Khối lượng của chương trình kỹ sư là bao nhiêu?')
    assert quote is None  # No engineer row has that value in this source.


@pytest.mark.parametrize('quote', ['["ALP301", "3"]', 'ALP301 3', 'ALP301 | 3', '3'])
def test_cited_table_row_cannot_borrow_a_value_from_an_uncited_neighbour(quote):
    item = replace(evidence(content=json.dumps({'headers': ['Course code', 'Credits'],
        'rows': [['ALP301', '3'], ['BET401', '4']]})), content_type='table')
    bad = {'answer': 'BET401 has 4 credits.', 'confidence': 'high', 'abstained': False,
        'claims': [{'claim_id': 'one', 'text': 'BET401 has 4 credits.', 'citation_ids': ['c1']}],
        'citations': [{'chunk_id': 'c1', 'page': item.page, 'quote': quote}]}
    answer = GroundedAnswerGenerator(FakeLLM(bad)).answer('What is the credit value of BET401?', [item], 'en')
    assert answer.abstained and not answer.to_public_dict()['claims']


def test_legacy_identity_only_quote_uses_its_own_row_and_keeps_conflicting_duplicates():
    item = replace(evidence(content=json.dumps({'headers': ['Course code', 'Credits'],
        'rows': [['ALP301', '3'], ['BET401', '4']]})), content_type='table')
    good = {'answer':'ALP301 has 3 credits.', 'confidence':'high', 'abstained':False,
        'claims':[{'claim_id':'one','text':'ALP301 has 3 credits.','citation_ids':['c1']}],
        'citations':[{'chunk_id':'c1','page':item.page,'quote':'ALP301'}]}
    generator = GroundedAnswerGenerator(FakeLLM(good))
    assert not generator.answer('What are the credits?', [item], 'en').abstained
    conflict = replace(item, content=json.dumps({'headers':['Course code','Credits'],
        'rows':[['ALP301','3'],['ALP301','4']]}))
    assert generator.answer('What are the credits?', [conflict], 'en').abstained


def test_different_grade_in_another_clause_cannot_validate_a_missing_f_grade():
    item = evidence(content='Điểm D là đạt. Điểm C là điều kiện tốt nghiệp. Người học được hoãn thi.')
    text = 'Điểm học phần là điểm F.'
    result = GroundedAnswerGenerator(FakeLLM(payload(text)), source_citations=True).answer('Khi nào điểm học phần là điểm F?', [item], 'vi')
    assert result.abstained and result.reason == 'contradicted_claim'
    actual = replace(item, content='Điểm học phần là điểm F.')
    result = GroundedAnswerGenerator(FakeLLM(payload(text)), source_citations=True).answer('Khi nào điểm học phần là điểm F?', [actual], 'vi')
    assert not result.abstained


def test_source_protocol_builds_verified_quote_and_page_without_model_guessing():
    llm = FakeLLM(payload())
    row = evidence(content='Opening.\n' * 100 + 'MATH101 is required.\n' + 'Closing.\n' * 100)
    answer = GroundedAnswerGenerator(llm, source_citations=True).answer('Which course is required?', [row])
    assert not answer.abstained
    citation = answer.citations[0]
    assert citation.page == row.page and citation.quote in row.content
    assert 'MATH101 is required.' in citation.quote
    assert validate_citation(citation, row, require_quote=True).valid


@pytest.mark.parametrize('other_doc,repeated,complete', [(False,False,True), (True,False,True),
                                                       (False,True,True), (False,False,False)])
def test_page_id_can_move_only_to_unique_literal_proof_in_complete_same_document(other_doc, repeated, complete):
    wrong = evidence(content='The graduate office opens on Monday.')
    exact = replace(wrong, chunk_id='exact', page=8,
        metadata={**wrong.metadata, 'page_range': [8,8]}, content='The application closes on Friday.',
        doc_id='other-doc' if other_doc else wrong.doc_id)
    results = [wrong, exact]
    if repeated: results.append(replace(exact, chunk_id='repeated', page=9, metadata={**exact.metadata, 'page_range':[9,9]}))
    original = payload('The application closes on Friday.')
    result = GroundedAnswerGenerator(FakeLLM(original), source_citations=True).answer(
        'When does the application close?', results, 'en', verified_document_absence=complete)
    if complete and not other_doc and not repeated:
        assert not result.abstained and result.citations[0].page == 8
        assert result.claims[0].citation_ids == ('exact',)
    else:
        assert not any(c.chunk_id == 'exact' for c in result.citations)
    assert original['citations'] == [{'chunk_id':'c1'}]
    assert original['claims'][0]['citation_ids'] == ['c1']


@pytest.mark.parametrize(('reason', 'verified', 'expected'), [
    ('document_does_not_mention', True, 'document_does_not_mention'),
    ('unsupported_claim', False, 'unsupported_claim'),
])
def test_orphan_model_citation_does_not_replace_abstention_reason(reason, verified, expected):
    model = {'answer': 'The document does not establish this fact.', 'confidence': 'low',
        'abstained': True, 'abstention_reason': reason, 'claims': [],
        'citations': [{'chunk_id': 'stale-provider-id'}]}
    answer = GroundedAnswerGenerator(FakeLLM(model), source_citations=True).answer(
        'Which fact is established?', [evidence()], language='en',
        verified_document_absence=verified)
    assert answer.abstained and answer.reason == expected
    assert answer.to_public_dict()['citations'] == []


@pytest.mark.parametrize(('reason', 'verified', 'expected'), [
    ('document_does_not_mention', True, 'document_does_not_mention'),
    ('unsupported_claim', False, 'unsupported_claim'),
])
def test_orphan_model_citation_does_not_replace_abstention_reason(reason, verified, expected):
    model = {'answer': 'The document does not establish this fact.', 'confidence': 'low',
        'abstained': True, 'abstention_reason': reason, 'claims': [],
        'citations': [{'chunk_id': 'stale-provider-id'}]}
    answer = GroundedAnswerGenerator(FakeLLM(model), source_citations=True).answer(
        'Which fact is established?', [evidence()], language='en',
        verified_document_absence=verified)
    assert answer.abstained and answer.reason == expected
    assert answer.to_public_dict()['citations'] == []


@pytest.mark.parametrize('text,chunk', [('MATH101 has 99 credits.', 'c1'),
    ('MATH101 is required.', 'unknown'), ('MATH101 is not required.', 'c1')])
def test_source_ids_do_not_make_unsupported_claims_valid(text, chunk):
    answer = GroundedAnswerGenerator(FakeLLM(payload(text, chunk)), source_citations=True).answer(
        'Which course is required?', [evidence()])
    assert answer.abstained and not answer.to_public_dict()['citations']


def test_source_mode_does_not_silently_repair_bad_legacy_coordinates():
    bad = payload()
    bad['citations'][0]['page'] = 999
    answer = GroundedAnswerGenerator(FakeLLM(bad), source_citations=True).answer('Which course?', [evidence()])
    assert answer.abstained


def test_table_quote_is_one_original_row_not_stitched_cells():
    table = {'headers': ['Course', 'Credits'], 'rows': [['MAT1042', '3'], ['CSC2001', '4']]}
    row = replace(evidence(content=json.dumps(table, ensure_ascii=False)), content_type='table')
    claims = [{'text': 'Course MAT1042 has 3 credits.', 'citation_ids': ['c1']}]
    quote = source_quote(row, claims)
    assert json.loads(quote) == table['rows'][0]
    assert validate_citation({'chunk_id': 'c1', 'page': 3, 'quote': quote}, row, require_quote=True).valid
    assert source_quote(row, []) is None


def test_admission_table_quote_uses_short_programme_code_not_nearby_row_words():
    table = {'headers': ['TT', 'Mã xét tuyển', 'Tên ngành1 xét tuyển', 'Mã ngành2',
                         'Tên chương trình', 'Chỉ tiêu', 'Phương thức tuyển sinh', 'Ghi chú'],
             'rows': [['1.', 'CN1', 'Công nghệ thông tin', '7480201', 'Công nghệ thông tin', '420',
                       'Phương thức xét tuyển thẳng – Mã : 301; ĐGNL (HSA) – Mã : 401; '
                       'CCQT SAT – Mã : 415; phương thức khác – Mã : 500; THPT – Mã : 100; '
                       'riêng CN10 và CN21 thêm tổ hợp B00', ''],
                      ['2.', 'CN2', 'Kỹ thuật máy tính', '7480106', 'Kỹ thuật máy tính', '420', '', '']]}
    row = replace(evidence(content=json.dumps(table, ensure_ascii=False)), content_type='table')
    claims = [{'text': 'Mã ngành theo danh mục quốc gia của mã xét tuyển CN2 là 7480106.',
               'citation_ids': ['c1']}]
    assert json.loads(source_quote(row, claims)) == table['rows'][1]


@pytest.mark.parametrize('identifier', ['HSA', 'SAT'])
def test_repeated_source_clause_is_bound_to_the_requested_admission_test(identifier):
    phrase = 'còn thời hạn sử dụng trong vòng 2 năm kể từ ngày dự thi'
    source = f'2.3.\nXét tuyển theo HSA: {phrase}.\n2.4.\nXét tuyển theo SAT: {phrase}.'
    row = evidence(content=source)
    claims = [{'text': phrase, 'citation_ids': ['c1']}]
    quote = source_quote(row, claims, question=f'What test-age limit applies to {identifier} results?')
    heading = '2.3.' if identifier == 'HSA' else '2.4.'
    assert quote == f'{heading}\nXét tuyển theo {identifier}: {phrase}.'
    assert validate_citation({'chunk_id': 'c1', 'page': 3, 'quote': quote}, row, require_quote=True).valid


def test_scoped_table_quote_keeps_the_requested_semester_and_contiguous_source_rows():
    table = {'headers': ['№', 'Discipline', 'Credits', 'Resources'], 'rows': [
        ['Semester 1', '', '', ''], ['', 'Compulsory Subjects', '', ''],
        ['1', 'Introduction to Information Technology', '3', 'VNU-UET'],
        ['7', 'English 1', '3', 'VNU-UET'], ['Semester 2', '', '', ''],
        ['6', 'English 2', '2', 'VNU-UET']]}
    content = 'Table headers: № | Discipline | Credits | Resources\n\n' + json.dumps(table, ensure_ascii=False)
    row = replace(evidence(content=content), content_type='table')
    claims = [{'text': 'English 1 has 3 credits.', 'citation_ids': ['c1']}]
    quote = source_quote(row, claims, question='In semester 1, how many credits does English 1 carry?')
    value = json.loads(quote)
    assert value == {'scope': 'Semester 1', 'headers': table['headers'], 'rows': table['rows'][:4]}
    assert validate_citation({'chunk_id': 'c1', 'page': 3, 'quote': quote}, row, require_quote=True).valid
    wrong_scope = json.dumps({'scope': 'Semester 2', 'headers': table['headers'],
                              'rows': table['rows'][:4]}, ensure_ascii=False)
    assert not validate_citation({'chunk_id': 'c1', 'page': 3, 'quote': wrong_scope}, row, require_quote=True).valid


def test_explicit_pdf_table_scope_is_bound_to_metadata_and_exact_row():
    table = {'headers': ['№', 'Discipline', 'Credits'], 'rows': [['2', 'Strength of Materials', '3']]}
    content = ('Table scope: Semester 4\nTable headers: № | Discipline | Credits\n\n'
               + json.dumps(table, ensure_ascii=False))
    row = replace(evidence(content=content), content_type='table',
        metadata={'table_scope': 'Semester 4', 'table_scope_provenance': 'explicit_pdf_marker'})
    quote = source_quote(row, [{'text': 'Strength of Materials has 3 credits.', 'citation_ids': ['c1']}],
                         question='In semester 4, how many credits does Strength of Materials carry?')
    assert json.loads(quote) == {'scope': 'Semester 4', 'headers': table['headers'], 'rows': table['rows']}
    assert validate_citation({'chunk_id': 'c1', 'page': 3, 'quote': quote}, row, require_quote=True).valid


def test_legacy_mode_keeps_strict_provider_page_and_quote_contract():
    old = payload()
    old['citations'] = [{'chunk_id': 'c1', 'page': 999, 'quote': 'MATH101 is required.'}]
    assert GroundedAnswerGenerator(FakeLLM(old)).answer('Which course?', [evidence()]).abstained


def test_distinct_claims_on_one_table_keep_all_original_rows_in_the_public_quote():
    table = {'headers': ['Course code', 'Credits'], 'rows': [['ABC7101', '3'], ['XYZ8202', '5']]}
    result = replace(evidence(content=json.dumps(table)), content_type='table')
    model = {'answer': 'Course ABC7101 has 3 credits. Course XYZ8202 has 5 credits.',
        'confidence': 'high', 'abstained': False, 'citations': [{'chunk_id': 'c1'}],
        'claims': [{'claim_id': 'a', 'text': 'Course ABC7101 has 3 credits.', 'citation_ids': ['c1']},
                   {'claim_id': 'b', 'text': 'Course XYZ8202 has 5 credits.', 'citation_ids': ['c1']}]}
    answer = GroundedAnswerGenerator(FakeLLM(model), source_citations=True).answer('State both course credits.', [result])
    assert not answer.abstained
    assert json.loads(answer.to_public_dict()['citations'][0]['quote']) == table['rows']
    assert validate_citation(answer.citations[0], result, require_quote=True).valid
    model['claims'][1]['text'] = 'Course XYZ8202 has 3 credits.'
    model['answer'] = 'Course ABC7101 has 3 credits. Course XYZ8202 has 3 credits.'
    assert GroundedAnswerGenerator(FakeLLM(model), source_citations=True).answer('State both course credits.', [result]).abstained


def test_table_identity_column_prevents_citing_a_prerequisite_row_instead():
    table = {'headers': ['Course code', 'Credits', 'Prerequisite'],
             'rows': [['XYZ8202', '3', 'ABC7101'], ['ABC7101', '3', '']]}
    result = replace(evidence(content=json.dumps(table)), content_type='table')
    claims = [{'text': 'Course ABC7101 has 3 credits.', 'citation_ids': ['c1']}]
    assert json.loads(source_quote(result, claims)) == table['rows'][1]


def test_multiple_facts_on_one_source_row_do_not_duplicate_that_row():
    table = {'headers': ['Course code', 'Credits', 'Name'], 'rows': [['ABC7101', '3', 'Research methods']]}
    result = replace(evidence(content=json.dumps(table)), content_type='table')
    claims = [{'text': text, 'citation_ids': ['c1']} for text in
              ['Course ABC7101 has 3 credits.', 'ABC7101 is Research methods.']]
    assert json.loads(source_quote(result, claims)) == table['rows'][0]


@pytest.mark.parametrize('combined', [False, True])
def test_source_quote_never_drops_or_truncates_required_rows_to_fit_a_budget(combined):
    size = 650 if combined else 1250
    table = {'headers': ['Course code', 'Credits', 'Description'],
             'rows': [['ABC7101', '3', 'a' * size], ['XYZ8202', '5', 'b' * size]]}
    result = replace(evidence(content=json.dumps(table)), content_type='table')
    claims = [{'text': 'Course ABC7101 has 3 credits.', 'citation_ids': ['c1']}]
    if combined: claims.append({'text': 'Course XYZ8202 has 5 credits.', 'citation_ids': ['c1']})
    assert source_quote(result, claims) is None


def test_compound_claim_selects_whole_source_rows_for_both_named_courses():
    table = {'headers': ['Course code', 'Credits'], 'rows': [['ABC7101', '3'], ['XYZ8202', '5']]}
    result = replace(evidence(content=json.dumps(table)), content_type='table')
    claims = [{'text': 'Course ABC7101 has 3 credits and course XYZ8202 has 5 credits.', 'citation_ids': ['c1']}]
    assert json.loads(source_quote(result, claims)) == table['rows']


@pytest.mark.parametrize('headers', [None, {}, [None]])
def test_malformed_table_headers_fail_closed(headers):
    result = replace(evidence(content=json.dumps({'headers': headers, 'rows': [['ABC7101', '3']]})), content_type='table')
    assert source_quote(result, [{'text': 'Course ABC7101 has 3 credits.', 'citation_ids': ['c1']}]) is None


def test_source_quote_keeps_adjacent_article_heading_as_visible_locator_proof():
    source = 'Article 6. Earlier unrelated statement.\nArticle 7.\nThe programme lasts four years.\nArticle 8. Another statement.'
    result = replace(evidence(content=source), content_type='text')
    quote = source_quote(result, [{'text': 'The programme lasts four years.', 'citation_ids': ['c1']}])
    assert quote == 'Article 7.\nThe programme lasts four years.'


def test_table_footnote_date_is_answered_from_the_matching_exact_source_clause():
    question = ('According to the asterisk footnote for institutions numbered 1 through 8, '
                'what issue date is given for the English certificate?')
    source = ('(*) Đối với chứng chỉ ngoại ngữ tiếng Anh: các cơ sở đào tạo có số thứ tự từ '
              '1 đến 8 được cấp từ ngày 15/5/2019.')
    row = replace(evidence(content=source), page=9,
        metadata={'page_range': [9, 9], 'source_hash': 'source-sha', 'source_name': 'admission notice'})
    answer = GroundedAnswerGenerator(FakeLLM({}), source_citations=True).answer(
        question, [row], language='en')
    assert not answer.abstained
    assert '15/5/2019' in answer.answer
    assert answer.citations[0].page == 9 and source in answer.citations[0].quote
    assert validate_citation(answer.citations[0], row, require_quote=True).valid


def test_public_answer_does_not_keep_an_unrequested_adjacent_role():
    answer_text = ('Yes, the programme lists university teaching and teaching-assistant roles '
                   'as possible career options.')
    claim_text = ('Giảng viên/Trợ giảng tại các trường Cao đẳng và Đại học, nghiên cứu viên tại '
                  'các Trung tâm/Viện nghiên cứu trong lĩnh vực Điện tử Viễn thông')
    source = ('Giảng viên/Trợ giảng tại các trường Cao đẳng và Đại học, nghiên cứu viên tại '
              'các Trung tâm/Viện nghiên cứu trong lĩnh vực Điện tử Viễn thông')
    row = evidence(content=source)
    model = {'answer': answer_text, 'confidence': 'high', 'abstained': False,
        'claims': [{'claim_id': 'one', 'text': claim_text, 'citation_ids': ['c1']}],
        'citations': [{'chunk_id': 'c1'}]}
    answer = GroundedAnswerGenerator(FakeLLM(model), source_citations=True).answer(
        'For possible careers, does the programme list university teaching or teaching-assistant work?',
        [row], language='en')
    assert not answer.abstained
    assert answer.answer == answer_text
    assert 'Giảng viên/Trợ giảng' in answer.claims[0].text
    assert 'nghiên cứu viên' not in answer.claims[0].text


def test_credit_abbreviation_does_not_change_the_supported_quantity():
    row=evidence(content='Sinh viên được đăng ký tối đa 11 TC trong kỳ phụ.')
    model={'answer':'Tối đa 11 tín chỉ trong kỳ phụ.','confidence':'high','abstained':False,
        'claims':[{'claim_id':'one','text':'Sinh viên được đăng ký tối đa 11 tín chỉ trong kỳ phụ.','citation_ids':['c1']}],
        'citations':[{'chunk_id':'c1'}]}
    answer=GroundedAnswerGenerator(FakeLLM(model),source_citations=True).answer('Kỳ phụ tối đa bao nhiêu tín chỉ?',[row])
    assert not answer.abstained
    model['claims'][0]['text']=model['claims'][0]['text'].replace('11','12')
    assert GroundedAnswerGenerator(FakeLLM(model),source_citations=True).answer('Kỳ phụ tối đa bao nhiêu tín chỉ?',[row]).abstained


def test_table_footnote_date_is_answered_from_the_matching_exact_source_clause():
    question = ('According to the asterisk footnote for institutions numbered 1 through 8, '
                'what issue date is given for the English certificate?')
    source = ('(*) Đối với chứng chỉ ngoại ngữ tiếng Anh: các cơ sở đào tạo có số thứ tự từ '
              '1 đến 8 được cấp từ ngày 15/5/2019.')
    row = replace(evidence(content=source), page=9,
        metadata={'page_range': [9, 9], 'source_hash': 'source-sha', 'source_name': 'admission notice'})
    answer = GroundedAnswerGenerator(FakeLLM({}), source_citations=True).answer(
        question, [row], language='en')
    assert not answer.abstained
    assert '15/5/2019' in answer.answer
    assert answer.citations[0].page == 9 and source in answer.citations[0].quote
    assert validate_citation(answer.citations[0], row, require_quote=True).valid
