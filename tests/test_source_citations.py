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


def test_source_protocol_builds_verified_quote_and_page_without_model_guessing():
    llm = FakeLLM(payload())
    row = evidence(content='Opening.\n' * 100 + 'MATH101 is required.\n' + 'Closing.\n' * 100)
    answer = GroundedAnswerGenerator(llm, source_citations=True).answer('Which course is required?', [row])
    assert not answer.abstained
    citation = answer.citations[0]
    assert citation.page == row.page and citation.quote in row.content
    assert 'MATH101 is required.' in citation.quote
    assert validate_citation(citation, row, require_quote=True).valid


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
