"""Natural single-course requests must keep headed row proof and every intent."""
import json

import pytest

from campusai.rag.context import resolve_query
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult


def source(*, doc='catalogue', code='ZZZ3340', credits='7', prerequisites='ABC1001\nABC1002',
           name='Hình học vi phân *\nDifferential Geometry', chunk='row', headers=None):
    return RetrievalResult(chunk, doc, 4, json.dumps({
        'headers': headers or ['Course code', 'Course name', 'Credits', 'Hours', 'Prerequisites'],
        'rows': [[code, name, credits, '75', prerequisites]],
    }, ensure_ascii=False), 'table', .95, 'hybrid',
        {'table_id': chunk, 'source_name': 'catalogue.pdf', 'page_range': [4, 4]})


class NoGeneration:
    def generate_json(self, *_args, **_kwargs):
        raise AssertionError('A complete headed-row lookup must not call the model')


@pytest.mark.parametrize('question,credit,edges', [
    ('môn này mấy tín nhỉ', True, 0),
    ('can hoc gi truoc va may tin vay', True, 2),
    ('cần học trước những môn nào nhỉ', False, 2),
    ('Môn Hình học vi phân có bao nhiêu tín chỉ?', True, 0),
    ('How many credits does Differential Geometry have?', True, 0),
    ('What are the prerequisites for Differential Geometry?', False, 2),
    ('What are the prerequisites and credits for Differential Geometry?', True, 2),
])
def test_natural_course_request_from_row_needs_no_model(question, credit, edges):
    resolved = resolve_query(question, history=[
        {'role': 'user', 'content': 'Mình đang tìm hiểu môn Hình học vi phân trong chương trình Toán.'},
        {'role': 'assistant', 'content': 'UNVERIFIED: this course has 999 credits.'},
    ])
    answer = GroundedAnswerGenerator(NoGeneration()).answer(resolved.resolved, [source()], 'en')
    assert not answer.abstained
    assert not answer.to_public_dict()['abstained']
    assert len(answer.claims) == int(credit) + edges
    assert all(c.status == 'supported' for c in answer.claims)
    assert len(answer.citations) == 1 and answer.citations[0].page == 4
    row = json.loads(answer.citations[0].quote)
    assert row[0] == 'ZZZ3340' and row[2] == '7' and row[4] == 'ABC1001\nABC1002'
    if credit:
        assert '7 credits' in answer.answer
    if edges:
        assert all(code in answer.answer for code in ('ABC1001', 'ABC1002', 'ZZZ3340'))
    assert '999' not in answer.answer


@pytest.mark.parametrize('question', [
    'Môn Hình học vi phân có bao nhiêu tín chỉ và tôi được mấy điểm?',
    'Môn Hình học vi phân có bao nhiêu tín chỉ nếu tôi chuyển ngành?',
    'How many credits does Differential Geometry have in 2035?',
    'Compare Differential Geometry and Linear Algebra credits.',
    'How many credits does the prerequisite of Differential Geometry have?',
])
def test_extra_requests_and_dependent_hops_are_not_reduced_to_a_single_cell(question):
    from campusai.rag.course_lookup import deterministic_course_lookup
    assert deterministic_course_lookup(question, [source()], 'en') is None


@pytest.mark.parametrize('records', [
    [source(headers=['Course code', 'Course name', 'Hours', 'Other', 'Prerequisites'])],
    [source(credits='7/9')],
    [source(), source(credits='8', chunk='other')],
    [source(), source(doc='another', chunk='other')],
    [source(), source(code='ZZZ3350', chunk='other')],
    [source(name='Hình học vi phân nâng cao\nAdvanced Differential Geometry')],
])
def test_missing_units_conflicting_rows_or_partial_names_are_not_proof(records):
    from campusai.rag.course_lookup import deterministic_course_lookup
    assert deterministic_course_lookup('Môn Hình học vi phân có bao nhiêu tín chỉ?', records, 'en') is None


@pytest.mark.parametrize('cell', ['', 'ABC1001 or ABC1002', 'ABC1001 hoặc ABC1002',
                                  'ABC1001 (grade B)', 'ABC1001 + approval',
                                  'None', 'ABC1001, ABC1001'])
def test_blank_conditional_or_disjunctive_prerequisites_are_not_an_and_list(cell):
    from campusai.rag.course_lookup import deterministic_course_lookup
    assert deterministic_course_lookup('What are the prerequisites for Differential Geometry?',
                                       [source(prerequisites=cell)], 'en') is None


def test_prerequisite_edges_need_the_exact_target_cell():
    from campusai.rag.multi_hop_evidence import prerequisite_claim_support, prerequisite, find_premise
    records = [source()]
    assert prerequisite_claim_support('Course ABC1001 is a prerequisite of course ZZZ3340.', records)[0]
    assert not prerequisite_claim_support('Course ABC1003 is a prerequisite of course ZZZ3340.', records)[0]
    assert not prerequisite_claim_support('Course ZZZ3340 is a prerequisite of course ABC1001.', records)[0]
    # A multi-prerequisite cell still cannot become one arbitrary dependent hop.
    assert prerequisite(find_premise(records, 'catalogue', code='ZZZ3340')) is None


@pytest.mark.parametrize('separator', ['\n', ', ', '; ', ' + ', ' and ', ' và '])
def test_unconditional_source_list_keeps_every_prerequisite(separator):
    answer = GroundedAnswerGenerator(NoGeneration()).answer(
        'What are the prerequisites for Differential Geometry?',
        [source(prerequisites=separator.join(['ABC1001', 'ABC1002']))], 'en')
    assert not answer.abstained and len(answer.claims) == 2
    assert all(c.status == 'supported' for c in answer.claims)


def test_complete_english_language_segment_is_supported_but_its_last_word_is_not():
    from campusai.rag.multi_hop_evidence import name_matches
    name = 'Hình học vi phân *\nDifferential\nGeometry'
    assert name_matches('Differential Geometry', name)
    assert not name_matches('Geometry', name)
    question = resolve_query('môn này mấy tín nhỉ', history=[
        {'role': 'user', 'content': 'Mình đang hỏi môn Differential Geometry.'}]).resolved
    assert not GroundedAnswerGenerator(NoGeneration()).answer(question, [source(name=name)]).abstained


def test_a_wrapped_english_name_is_not_two_short_course_names():
    from campusai.rag.course_lookup import deterministic_course_lookup
    from campusai.rag.multi_hop_evidence import name_matches
    name = 'Differential\nGeometry'
    assert not name_matches('Differential', name)
    assert not name_matches('Geometry', name)
    assert deterministic_course_lookup('How many credits does Differential have?',
                                       [source(name=name)], 'en') is None
    answer = GroundedAnswerGenerator(NoGeneration()).answer(
        'How many credits does Differential Geometry have?', [source(name=name)], 'en')
    assert not answer.abstained and '7 credits' in answer.answer




@pytest.mark.parametrize('topic', [
    'Mình hỏi môn Hình học vi phân nếu chuyển ngành.',
    'What about a waiver for course Differential Geometry?',
    'Mình hỏi môn Hình học vi phân và môn Linear Algebra.',
    'Mình hỏi môn Hình học vi phân và Một môn chưa có trong bảng.',
    'Mình muốn so sánh môn Hình học vi phân với các lựa chọn khác.',
])
def test_a_conditional_or_multi_course_user_topic_is_not_a_single_unconditional_cell(topic):
    from campusai.rag.course_lookup import deterministic_course_lookup
    question = resolve_query('môn này mấy tín nhỉ', history=[{'role': 'user', 'content': topic}]).resolved
    records = [source(), source(code='ZZZ3350', name='Linear Algebra', chunk='algebra')]
    assert deterministic_course_lookup(question, records, 'en') is None


def test_old_cached_refusal_is_bypassed_and_corrected_lookup_survives_restart(tmp_path, monkeypatch):
    from campusai.rag import service as service_module
    from campusai.rag.cache import RAGAnswerCache, build_rag_cache_key
    from campusai.rag.grounding import _abstention
    from campusai.rag.service import CampusAIQueryService
    from tests.test_basic_rag import FakeRetriever
    path = str(tmp_path / 'answers.sqlite3')
    question = 'How many credits does Differential Geometry have?'
    def application(generator):
        return CampusAIQueryService(FakeRetriever([source()]), generator,
                                    cache=RAGAnswerCache(path), default_mode='hybrid')
    old_generator = GroundedAnswerGenerator(NoGeneration())
    monkeypatch.setattr(old_generator, 'answer', lambda *_a, **_kw: _abstention('unsupported_claim'))
    with monkeypatch.context() as legacy:
        legacy.setattr(service_module, 'build_rag_cache_key',
                       lambda **kw: build_rag_cache_key(**kw, grounding_policy_version='grounding-v29'))
        old = application(old_generator)
        try:
            assert old.ask(question, doc_ids=['catalogue'], language='en').abstained
        finally:
            old.close()
    for cached in [False, True]:
        current = application(GroundedAnswerGenerator(NoGeneration()))
        try:
            answer = current.ask(question, doc_ids=['catalogue'], language='en')
            assert not answer.abstained and '7 credits' in answer.answer
            assert current.last_cache_hit is cached
        finally:
            current.close()
