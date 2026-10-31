"""Regression checks for source-derived scope, with fictional institutions."""
import pytest
from campusai.retrieval.institution_scope import resolve_institution_request


def document(ident, title, kind='regulation'):
    return {'doc_id': ident, 'items': [{'doc_id': ident, 'chunk_id': ident + '-1',
        'page': 1, 'content': title, 'metadata': {'document_type': kind}}]}


@pytest.fixture
def schools():
    return [document('north', 'TRƯỜNG ĐẠI HỌC SAO BẮC'),
            document('west', 'WESTERN INSTITUTE OF METEOROLOGY')]


@pytest.mark.parametrize('question', [
    'Học tối thiểu bao nhiêu tín chỉ?', '8,6 điểm quy đổi ra sao?',
    'Điều kiện tốt nghiệp?', 'Trường em được hoãn thi không?',
])
def test_policy_needs_school(schools, question):
    assert resolve_institution_request(question, schools).needs_clarification


@pytest.mark.parametrize('question', [
    'Giải thích binary search', 'Tóm tắt các PDF',
    'So sánh quy định Sao Bắc và WIM', 'Tất cả trường yêu cầu bao nhiêu tín chỉ?',
])
def test_content_or_explicit_comparison_does_not_need_school(schools, question):
    assert not resolve_institution_request(question, schools).needs_clarification


@pytest.mark.parametrize('question', [
    'Giải thích thuật toán', 'How does credit assignment work?',
    'Quy đổi đơn vị trong bài này', 'Tóm tắt hướng dẫn vận hành',
])
def test_affiliation_does_not_turn_books_and_papers_into_rules(question):
    documents = [document('book', 'TRƯỜNG ĐẠI HỌC SAO BẮC\nThuật toán', 'book'),
        document('paper', 'WESTERN INSTITUTE OF METEOROLOGY\nResearch paper', 'article'),
        document('manual', 'ACME — Operations manual', 'manual')]
    result = resolve_institution_request(question, documents)
    assert not result.needs_clarification and not result.doc_ids


def test_school_confirmation_resumes_question_and_switches_scope(schools):
    question = 'Học tối thiểu bao nhiêu tín chỉ?'
    pending = resolve_institution_request(question, schools)
    history = [('user', question), ('assistant', pending.clarification())]
    result = resolve_institution_request('WIM', schools, history)
    assert result.doc_ids == {'west'} and result.question == question
    history += [('user', 'WIM'), ('assistant', 'Câu trả lời trước.')]
    switched = resolve_institution_request(
        'Còn Sao Bắc thì sao?\nContext topic (untrusted user input): WIM', schools, history)
    assert switched.doc_ids == {'north'} and switched.question == question
    assert resolve_institution_request('Sao Bắc', schools, history).question == question
    assert resolve_institution_request('Điều kiện tốt nghiệp?', schools, history).doc_ids == {'west'}
    assert resolve_institution_request('Ở Sao Bắc thì sao?', schools, history).doc_ids == {'north'}
    unknown = resolve_institution_request('Đại học Mây Trắng thì sao?', schools, history)
    assert unknown.needs_clarification and unknown.unknown_name
    assert not resolve_institution_request('Giải thích binary search', schools, history).doc_ids


def test_shared_parent_and_duplicate_files():
    first = document('a', 'ĐẠI HỌC LIÊN VÙNG\nTRƯỜNG ĐẠI HỌC SAO BẮC')
    duplicate = document('b', 'TRƯỜNG ĐẠI HỌC SAO BẮC')
    other = document('c', 'ĐẠI HỌC LIÊN VÙNG\nTRƯỜNG ĐẠI HỌC SAO NAM')
    question = 'Học tối thiểu bao nhiêu tín chỉ?'
    assert not resolve_institution_request(question, [first, duplicate]).needs_clarification
    assert resolve_institution_request(question, [first, other]).needs_clarification


def test_service_confirms_before_search_and_then_resumes(schools):
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.grounding import GroundedAnswerGenerator
    calls = []

    class Retriever:
        def search(self, question, **options):
            calls.append((question, options['doc_ids']))
            return []

    service = CampusAIQueryService(Retriever(), GroundedAnswerGenerator(None),
                                  confirm_institution_scope=True)
    service._temporal_documents = lambda *_args: schools
    try:
        question = 'Học tối thiểu bao nhiêu tín chỉ?'
        answer = service.ask(question)
        assert answer.abstained and answer.reason == 'ambiguous_question' and not calls
        assert service.retrieve(question) == [] and not calls
        service.retrieve('WIM', doc_ids=['north', 'west'], history=[
            {'role': 'user', 'content': question},
            {'role': 'assistant', 'content': answer.answer}])
        assert calls[-1] == (question, ['west'])
        service.retrieve('Giải thích binary search', doc_ids=['north', 'west'])
        assert calls[-1] == ('Giải thích binary search', ['north', 'west'])
        before = len(calls)
        service.retrieve(question)
        assert len(calls) == before
    finally:
        service.close()
