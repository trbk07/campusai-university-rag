"""Necessary award conditions cannot be borrowed from another named award."""
from copy import deepcopy

import pytest

from campusai.rag.award_conditions import lookup_award_condition
from campusai.rag.grounding import validate_citation


def document():
    text = ('Điều 4: Danh hiệu “Sinh viên Chăm chỉ” được trao cho các sinh viên có kết quả '
            'học tập loại Tốt và không có học phần nào có điểm dưới B-.\n'
            'Sinh viên được nhận giấy khen.\n'
            'Điều 5: Danh hiệu “Sinh viên Tiến bộ” được trao cho các sinh viên không có '
            'học phần nào có điểm dưới D.\nĐiều 6: Điều khoản khác.')
    return {'doc_id':'awards','items':[dict(chunk_id='rule',doc_id='awards',page=2,content=text,
        content_type='text',metadata={'source_name':'awards.pdf','source_hash':'awards','page_range':[2,2]})]}


def project(question='có một môn dưới B- là bay danh hiệu sv chăm chỉ à',doc=None):
    return lookup_award_condition(question,[doc or document()],doc_ids=['awards'])


def test_necessary_grade_rule_uses_the_named_award_and_actual_source_grade():
    answer,results=project()
    assert not answer.abstained and 'không đáp ứng' in answer.answer
    assert 'B-' in answer.answer and 'Chăm chỉ' in answer.answer
    assert 'Tiến bộ' not in answer.citations[0].quote
    assert validate_citation(answer.citations[0],results[0],require_quote=True).valid


@pytest.mark.parametrize('question',[
    'có một môn dưới C+ là bay danh hiệu sv chăm chỉ à',
    'có một môn dưới B- là bay danh hiệu sv chưa có à',
    'có một môn bằng B- là bay danh hiệu sv chăm chỉ à',
    'có một môn dưới B- là bay danh hiệu sv chăm chỉ và được mấy tiền',
    'em đã bị thu hồi giấy khen chăm chỉ chưa',
])
def test_unknown_titles_other_operators_and_extra_intents_fall_back(question):
    assert project(question) is None


@pytest.mark.parametrize('replace',[
    ('không có học phần nào','được phép có một học phần'),
    ('không có học phần nào','không cần không có học phần nào'),
    ('không có học phần nào','không bắt buộc không có học phần nào'),
    ('không có học phần nào','không yêu cầu không có học phần nào'),
    ('dưới B-.','dưới B- hoặc đủ điều kiện ngoại lệ.'),
    ('Sinh viên được nhận giấy khen.','Ngoại trừ sinh viên chuyển ngành.'),
    ('Điều 5:','Nếu cần ngoại lệ. Điều 5:'),
])
def test_exceptions_and_incomplete_scope_cannot_be_dropped(replace):
    doc=document(); doc['items'][0]['content']=doc['items'][0]['content'].replace(*replace)
    assert project(doc=doc) is None


def test_conflicting_duplicate_policy_cannot_be_cherry_picked():
    doc=document(); other=deepcopy(doc['items'][0]); other['chunk_id']='other'
    other['content']=other['content'].replace('dưới B-.','dưới C+.'); doc['items'].append(other)
    assert project(doc=doc) is None


def test_an_unknown_policy_for_the_same_named_award_cannot_be_ignored():
    doc=document(); other=deepcopy(doc['items'][0]); other['chunk_id']='unknown'
    other['content']=other['content'].replace('được trao cho','chưa xác định điều kiện cho')
    doc['items'].append(other)
    assert project(doc=doc) is None


def test_award_source_selection_is_explicit():
    doc=document()
    for ids,docs in [(None,[doc]),(['other'],[doc]),(['awards','other'],[doc]),(['awards'],[doc,doc])]:
        assert lookup_award_condition('có một môn dưới B- là bay danh hiệu sv chăm chỉ à',docs,doc_ids=ids) is None


@pytest.mark.parametrize('source_grade',['B−','B＋','B++'])
def test_an_unparsed_grade_modifier_cannot_be_read_as_the_bare_letter(source_grade):
    doc=document(); doc['items'][0]['content']=doc['items'][0]['content'].replace('dưới B-.','dưới '+source_grade+'.')
    assert project('có một môn dưới B là bay danh hiệu sv chăm chỉ à',doc) is None


def definition_case():
    from campusai.rag.grounding import Citation
    from campusai.rag.claims import Claim
    from campusai.retrieval.hybrid import RetrievalResult
    quote = ('Điều 8: Danh hiệu “Sinh viên Nghiên cứu” được trao cho các sinh viên đạt '
             'kết quả học tập từ 2.7 trở lên, giữ một chức vụ trong câu lạc bộ và có '
             'đóng góp tích cực cho nghiên cứu khoa học.')
    summary = ('Theo quy định, danh hiệu “Sinh viên Nghiên cứu” được trao cho sinh viên '
               'đạt kết quả học tập từ 2.7 trở lên và giữ một chức vụ trong câu lạc bộ.')
    result = RetrievalResult('rule', 'awards', 3, quote, 'text', 1., 'bm25', {})
    citation = Citation('rule', 'awards', 3, quote, page_range=(3, 3))
    claim = Claim('one', summary, citation_ids=('rule',), status='supported')
    return summary, (citation,), (claim,), [result]


def test_complete_normative_definition_retains_the_last_required_conjunct():
    from campusai.rag.award_conditions import complete_award_definition
    from campusai.rag.grounding import _grounding_finalize
    summary, citations, claims, results = definition_case()
    expected = citations[0].quote
    assert complete_award_definition(summary, citations, claims, results) == expected
    answer = _grounding_finalize(summary, citations,
        {'claims': [{'claim_id': 'one', 'text': summary, 'citation_ids': ['rule']}]}, results, 'vi')
    assert not answer.abstained and answer.answer == expected
    assert 'đóng góp tích cực' in answer.answer and '2.7' in answer.answer
    assert answer.claims[0].text == expected
    assert complete_award_definition(answer.answer, answer.citations, answer.claims, results) is None


@pytest.mark.parametrize('mutation', ['source_mismatch', 'wrong_title', 'partial_quote', 'second_definition',
                                     'extra_public_sentence', 'personal_outcome', 'unsupported', 'english'])
def test_definition_completion_cannot_borrow_or_drop_other_assertions(mutation):
    from dataclasses import replace
    from campusai.rag.award_conditions import complete_award_definition
    summary, citations, claims, results = definition_case()
    language = 'vi'
    if mutation == 'source_mismatch': results = [replace(results[0], content='Unrelated source.')]
    elif mutation == 'wrong_title': summary = summary.replace('Nghiên cứu', 'Chăm chỉ')
    elif mutation == 'partial_quote': citations = (replace(citations[0], quote=citations[0].quote[:-1]),)
    elif mutation == 'second_definition': citations = (replace(citations[0], quote=citations[0].quote+' Another definition.'),)
    elif mutation == 'extra_public_sentence': summary += ' Tiền thưởng là 500 nghìn đồng.'
    elif mutation == 'personal_outcome': summary = 'Bạn đã được nhận danh hiệu này.'
    elif mutation == 'unsupported': claims = (replace(claims[0], status='unsupported'),)
    elif mutation == 'english': language = 'en'
    assert complete_award_definition(summary, citations, claims, results, language) is None
