"""A multi-course semester lookup must establish every requested identity."""
from copy import deepcopy
import json

import pytest

from campusai.rag.course_schedule import lookup_course_schedule
from campusai.rag.grounding import validate_citation


def document():
    data = {'headers': ['Course code', 'Course name', 'Semester', 'Credits'], 'rows': [
        ['ABC801', 'Distributed Systems', '3', '9'],
        ['ABC802', 'Numerical Analysis', '4', '8'],
    ]}
    return {'doc_id': 'plan', 'items': [{'chunk_id': 'table', 'page': 2, 'content_type': 'table',
        'content': json.dumps(data), 'metadata': {'source_name': 'plan.pdf', 'page_range': [2, 2]}}]}


def project(question='ABC801 và ABC802 học ở kỳ nào', doc=None):
    return lookup_course_schedule(question, [doc or document()], doc_ids=['plan'])


def test_every_requested_course_has_its_own_literal_semester():
    answer, results = project()
    assert not answer.abstained
    assert 'ABC801 (Distributed Systems) học ở học kỳ 3' in answer.answer
    assert 'ABC802 (Numerical Analysis) học ở học kỳ 4' in answer.answer
    assert len(answer.claims) == 2 and len(answer.citations) == 1
    assert validate_citation(answer.citations[0], results[0], require_quote=True).valid


@pytest.mark.parametrize('mutation', [
    lambda d: d['rows'].pop(),
    lambda d: d['rows'][1].__setitem__(2, ''),
    lambda d: d['rows'][1].__setitem__(2, '3, 4'),
    lambda d: d['rows'][1].__setitem__(2, 'if approved: 4'),
    lambda d: d['headers'].__setitem__(2, 'Contact hours'),
    lambda d: d['headers'].append('Semester'),
    lambda d: d['rows'].append(['ABC802', 'Numerical Analysis', '5', '8']),
    lambda d: d['rows'].append(['ABC802', 'Different Subject', '4', '8']),
    lambda d: d['rows'][1].__setitem__(0, 'ABC802 / ABC803'),
    lambda d: d['rows'][1].__setitem__(3, 'if approved'),
])
def test_incomplete_or_conflicting_second_subject_cannot_be_dropped(mutation):
    doc = document(); data = json.loads(doc['items'][0]['content']); mutation(data)
    doc['items'][0]['content'] = json.dumps(data)
    assert project(doc=doc) is None


@pytest.mark.parametrize('question', [
    'ABC801 và ABC802 học ở kỳ nào và học phí bao nhiêu',
    'ABC801 và ABC802 học ở kỳ nào nếu chuyển ngành',
    'ABC801 và ABC999 học ở kỳ nào',
    'ABC801 và ABC801 học ở kỳ nào',
    'ABC801 học ở kỳ nào',
])
def test_unknown_subjects_extra_intents_and_duplicate_requests_fall_back(question):
    assert project(question) is None


def test_a_lower_ranked_conflicting_table_cannot_be_ignored():
    doc = document(); other = deepcopy(doc['items'][0]); other['chunk_id'] = 'lower'
    data = json.loads(other['content']); data['rows'][1][2] = '6'
    other['content'] = json.dumps(data); doc['items'].append(other)
    assert project(doc=doc) is None


def test_only_explicitly_selected_single_source_is_used():
    for ids, docs in [(None, [document()]), (['other'], [document()]), (['plan', 'other'], [document()])]:
        assert lookup_course_schedule('ABC801 và ABC802 học ở kỳ nào', docs, doc_ids=ids) is None


def test_standard_abbreviations_select_source_names_without_fixing_codes_or_values():
    doc = document(); data = json.loads(doc['items'][0]['content'])
    data['rows'] = [
        ['XYZ901', 'Trí tuệ nhân tạo nâng cao\nAdvanced Artificial Intelligence', '7', '4'],
        ['XYZ902', 'Xử lý ngôn ngữ tự nhiên và ứng dụng\nNatural Language Processing and\nApplications', '5', '6'],
    ]
    doc['items'][0]['content'] = json.dumps(data, ensure_ascii=False)
    answer, _ = project('AI nâng cao với NLP trong hướng dẫn thạc sĩ KHMT học ở kỳ nào vậy', doc)
    assert 'XYZ901' in answer.answer and 'học kỳ 7' in answer.answer
    assert 'XYZ902' in answer.answer and 'học kỳ 5' in answer.answer


def test_a_phrase_inside_a_different_course_name_is_not_an_identity():
    doc = document(); data = json.loads(doc['items'][0]['content'])
    data['rows'][0][1] = 'Introduction to Distributed Systems'
    doc['items'][0]['content'] = json.dumps(data)
    assert project('Distributed Systems và Numerical Analysis học ở kỳ nào', doc) is None


def test_production_service_returns_both_facts_without_a_model_call(tmp_path):
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.bm25_index import BM25Index
    from campusai.retrieval.hybrid import HybridRetriever
    class NoGeneration:
        def generate_json(self, *args, **kwargs):
            raise AssertionError('Complete source rows require no provider call')
    doc = document(); BM25Index(doc['items'], 'en').save(tmp_path/'plan'/'bm25.json')
    service = CampusAIQueryService(HybridRetriever(tmp_path), GroundedAnswerGenerator(NoGeneration()), default_mode='bm25')
    try:
        answer = service.ask('ABC801 và ABC802 học ở kỳ nào', doc_ids=['plan'])
        assert not answer.abstained and len(answer.claims) == 2
        assert service.retriever.last_trace.route == 'source_course_schedule'
        assert service.ask('ABC801 và ABC802 học ở kỳ nào', doc_ids=['plan']).cache_hit
    finally:
        service.close()
