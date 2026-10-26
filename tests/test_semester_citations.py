"""Semester locators cannot be mistaken for a course row's factual numbers."""
import json
from dataclasses import replace

import pytest

from campusai.rag.source_citations import source_quote
from campusai.rag.grounding import GroundedAnswerGenerator, validate_citation
from tests.test_basic_rag import FakeLLM, evidence


def source(second_provider='Institute Z'):
    data = {'headers': ['No.', 'Discipline', 'Credits', 'Resources'], 'rows': [
        ['Semester 2', '', '', ''], ['', 'Compulsory Subjects', '', ''],
        ['1', 'Alpha', '3', 'Institute X'], ['', 'Credits per semester', '3', ''],
        ['Semester 5', '', '', ''], ['', 'Compulsory Subjects', '', ''],
        ['1', 'Alpha', '2', 'Institute Z'], ['2', 'Beta', '5', second_provider],
        ['', 'Credits per semester', '7', ''],
    ]}
    return replace(evidence(content=json.dumps(data)), content_type='table')


def claims(text):
    return [{'claim_id': 'one', 'text': text, 'citation_ids': ['c1']}]


def test_scope_number_is_separate_from_course_serial_and_credit_numbers():
    item = source()
    text = 'Semester 5 Compulsory Subjects 1 Alpha 2 Institute Z'
    quote = source_quote(item, claims(text), 'Học kỳ 5 do trường nào phụ trách?')
    assert quote is not None
    value = json.loads(quote)
    assert value['scope'] == 'Semester 5'
    assert value['rows'][0] == ['Semester 5', '', '', '']
    assert ['1', 'Alpha', '2', 'Institute Z'] in value['rows']
    assert ['1', 'Alpha', '3', 'Institute X'] not in value['rows']
    assert validate_citation({'chunk_id':'c1','page':item.page,'quote':quote}, item, require_quote=True).valid


@pytest.mark.parametrize('question', ['Học kỳ 2 do trường nào phụ trách?', 'hk2 bên nào dạy',
                                     'In semester 2, which institution teaches Alpha?'])
def test_wrong_semester_cannot_be_proved_by_a_number_in_another_column(question):
    assert source_quote(source(), claims('Semester 5 Alpha has 2 credits.'), question) is None


@pytest.mark.parametrize('text', ['Semester 5 Alpha has 5 credits.',
                                'Semester 5 Alpha 5', 'Semester 2 Alpha has 2 credits.'])
def test_identical_scope_and_credit_number_still_require_the_right_named_cell(text):
    assert source_quote(source(), claims(text), 'What is the source course credit value?') is None


def test_real_value_of_the_named_row_remains_supported():
    quote = source_quote(source(), claims('Semester 5 Alpha has 2 credits.'), 'In semester 5, what are the credits?')
    assert quote is not None and 'Institute X' not in quote


def test_scope_claim_cannot_be_proved_without_a_literal_marker_or_trusted_scope():
    item = source()
    data = json.loads(item.content)
    data['rows'] = [['1', 'Alpha', '5', 'Institute Z']]
    assert source_quote(replace(item, content=json.dumps(data)), claims('Semester 5 Alpha'), 'Semester 5 credits?') is None


def test_unknown_marker_cannot_inherit_the_previous_scope():
    item = source()
    data = json.loads(item.content)
    data['rows'].insert(6, ['Semester unknown', '', '', ''])
    assert source_quote(replace(item, content=json.dumps(data)), claims('Semester 5 Alpha has 2 credits.')) is None


def test_comparison_keeps_both_real_scope_markers_in_one_source_chunk():
    quote = source_quote(source(), claims('Semester 2 Alpha has 3 credits.')
                         + claims('Semester 5 Alpha has 2 credits.'), 'Compare semesters 2 and 5.')
    assert quote is not None
    assert 'Semester 2' in quote and 'Semester 5' in quote
    assert validate_citation({'chunk_id':'c1','page':source().page,'quote':quote}, source(), require_quote=True).valid


def test_provider_group_cannot_use_one_row_to_hide_a_different_provider():
    text = 'Semester 5 Compulsory Subjects 1 Alpha 2 Institute Z'
    payload = {'answer':'All semester 5 courses are taught by Institute Z.', 'claims':claims(text),
               'citations':[{'chunk_id':'c1'}], 'confidence':'high', 'abstained':False}
    generator = GroundedAnswerGenerator(FakeLLM(payload), source_citations=True)
    bad = generator.answer('Which institution teaches semester 5 courses?', [source('Institute Y')], 'en')
    assert bad.abstained
    good = generator.answer('Which institution teaches semester 5 courses?', [source()], 'en')
    assert not good.to_public_dict()['abstained']
    assert 'Beta' in good.citations[0].quote  # Complete provider-group evidence.


def test_conflicting_named_credit_rows_cannot_be_cherry_picked():
    item = source()
    data = json.loads(item.content)
    data['rows'].insert(-1, ['3', 'Alpha', '5', 'Institute Z'])
    assert source_quote(replace(item, content=json.dumps(data)), claims('Semester 5 Alpha has 2 credits.')) is None


def test_missing_credit_cell_cannot_use_the_equal_serial_number():
    item = source()
    data = json.loads(item.content)
    data['rows'][6] = ['2', 'Alpha', '', 'Institute Z']
    assert source_quote(replace(item, content=json.dumps(data)), claims('Semester 5 Alpha has 2 credits.')) is None


def test_scoped_named_total_and_course_code_are_distinct_projections():
    item = source()
    assert source_quote(item, claims('Semester 5 has 7 credits.')) is not None
    data = {'headers':['No.','Course code','Credits','Resources'], 'rows':[
        ['Semester 5','','',''], ['1','CS301','2','Institute Z'], ['', 'Credits per semester','2','']]}
    item = replace(item, content=json.dumps(data))
    assert source_quote(item, claims('Semester 5 CS301 has 2 credits.')) is not None
    assert source_quote(item, claims('Semester 5 CS999 has 2 credits.')) is None


def test_old_scoped_refusal_is_bypassed_and_corrected_citation_survives_restart(tmp_path, monkeypatch):
    from campusai.rag import service as service_module
    from campusai.rag.cache import RAGAnswerCache, build_rag_cache_key
    from campusai.rag.grounding import _abstention
    from campusai.rag.service import CampusAIQueryService
    from tests.test_basic_rag import FakeRetriever
    question = 'Which institution teaches semester 5 courses?'
    text = 'Semester 5 Compulsory Subjects 1 Alpha 2 Institute Z'
    data = {'answer':'All semester 5 courses are taught by Institute Z.', 'claims':claims(text),
            'citations':[{'chunk_id':'c1'}], 'confidence':'high', 'abstained':False}
    path = str(tmp_path/'answers.sqlite3')
    def application(generator):
        return CampusAIQueryService(FakeRetriever([source()]), generator,
            cache=RAGAnswerCache(path), default_mode='hybrid')
    old_generator = GroundedAnswerGenerator(FakeLLM(data), source_citations=True)
    monkeypatch.setattr(old_generator, 'answer', lambda *_a, **_kw: _abstention('unsupported_claim'))
    with monkeypatch.context() as legacy:
        legacy.setattr(service_module, 'build_rag_cache_key',
                       lambda **kw: build_rag_cache_key(**kw, grounding_policy_version='grounding-v31'))
        old = application(old_generator)
        try:
            assert old.ask(question, doc_ids=['doc-1'], language='en').abstained
        finally:
            old.close()
    for cached in [False, True]:
        current = application(GroundedAnswerGenerator(FakeLLM(data), source_citations=True))
        try:
            assert not current.ask(question, doc_ids=['doc-1'], language='en').to_public_dict()['abstained']
            assert current.last_cache_hit is cached
        finally:
            current.close()


def test_explicit_semester_column_binds_the_course_without_requiring_a_group_marker():
    data = {'headers':['Course code','Course name','Credits','Semester'], 'rows':[
        ['CS301','Alpha','3','2'], ['CS302','Beta','2','3']]}
    item = replace(source(),content=json.dumps(data))
    for text in ['CS301 is placed in semester 2.', 'Alpha is placed in semester 2.']:
        quote = source_quote(item,claims(text),'Which semester is Alpha placed in?')
        assert json.loads(quote)==data['rows'][0]
        assert validate_citation({'chunk_id':'c1','page':item.page,'quote':quote},item,require_quote=True).valid
    assert source_quote(item,claims('CS301 is placed in semester 3.'),'Which semester is Alpha placed in?') is None
    assert source_quote(item,claims('Gamma is placed in semester 2.'),'Which semester is Gamma placed in?') is None


def test_one_named_course_provider_does_not_require_other_courses_to_share_it():
    text = 'Semester 5 Compulsory Subjects 1 Alpha 2 Institute Z'
    quote = source_quote(source('Institute Y'),claims(text),'Which institution teaches Alpha in semester 5?')
    assert quote is not None and 'Institute Y' not in quote


@pytest.mark.parametrize('location',['semester 8','kỳ 8','học kỳ thứ 8','hoc ky thu 8','kì 8'])
def test_compact_source_marker_supports_a_spaced_location_without_lending_its_number(location):
    data = {'headers':['No.','Discipline','Credits','Resources'], 'rows':[
        ['Semester2','','',''], ['1','Other project','3','Institute X'],
        ['Semester8','','',''], ['1','Research Project','9','Institute Z']]}
    item = replace(source(),content=json.dumps(data))
    model = {'answer':f'Research Project has 9 credits and belongs to {location}.',
        'claims':claims('Research Project has 9 credits.')+[
            {'claim_id':'two','text':'Research Project belongs to Semester8.','citation_ids':['c1']}],
        'citations':[{'chunk_id':'c1'}],'confidence':'high','abstained':False}
    question='What are the credits and semester for Research Project?'
    answer=GroundedAnswerGenerator(FakeLLM(model),source_citations=True).answer(question,[item],'en')
    assert not answer.to_public_dict()['abstained']
    for text in ['Research Project has 8 credits and belongs to semester 8.',
                 'Research Project has 9 credits and belongs to semester 2.']:
        altered={**model,'answer':text}
        assert GroundedAnswerGenerator(FakeLLM(altered),source_citations=True).answer(question,[item],'en').abstained


def test_subtotal_label_is_not_a_claim_about_a_thirtieth_semester():
    from campusai.rag.semester_citations import references
    assert references('Credits per semester 30') == set()
    quote=source_quote(source(),claims('Credits per semester 7'),'How many credits in semester 5?')
    assert quote is not None and 'Semester 5' in quote
