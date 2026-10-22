"""Independent conversation and misleading-answer cases reported as user behavior."""
import pytest

from campusai.document_info import document_info_response
from campusai.rag.context import resolve_query
from campusai.rag.grounding import GroundedAnswerGenerator
from tests.test_basic_rag import FakeLLM, evidence


@pytest.mark.parametrize('question', [
    'Stack là gì và nó hoạt động thế nào?',
    'What is a queue and how does it work?',
    'Explain a linked list and give an example of how it works.',
    'CS101 là gì và nó có mấy tín chỉ?',
    'thế tổng hợp phần queue đi',
    'vậy tóm tắt chương về arrays giúp mình',
])
def test_named_subject_in_current_question_does_not_require_old_topic(question):
    for history in ([], [{'role':'user','content':'Tài liệu có mấy trang?'}]):
        result = resolve_query(question, history=history)
        assert not result.needs_clarification and result.resolved == question


@pytest.mark.parametrize('question', [
    'cái này hoạt động sao?', 'no hoat dong the nao?', 'thêm ví dụ nữa',
    'ngắn gọn hơn', 'đơn giản hơn chút', 'this one?', 'give me another example',
    'tl;dr', 'nói rõ chỗ này',
])
def test_elliptical_human_followup_is_anchored_or_clarified(question):
    missing = resolve_query(question)
    assert missing.needs_clarification
    resolved = resolve_query(question, history=[{'role':'user','content':'Giải thích queue trong tài liệu'}])
    assert not resolved.needs_clarification
    assert 'Giải thích queue' in resolved.resolved


@pytest.mark.parametrize('question', [
    'Bạn cho mình biết tài liệu này có tổng cộng bao nhiêu trang nhé?',
    'file này bao nhiêu trang bạn ơi?', 'pdf co nhieu trang ko, cu the la bao nhieu trang?',
    'tài liệu này nhiêu trang?', 'có bn trang thế?', 'bạn đếm giúp số trang của file này với',
    'How long is this PDF in pages?', 'Could you tell me how many pages this PDF has?',
])
def test_natural_page_count_variants_use_pdf_information(question):
    result = document_info_response(question, [{'doc_id':'one','name':'My Notes.pdf','page_count':7}])
    assert result is not None and not result['answer']['abstained']
    assert result['document_info']['documents'][0]['page_count'] == 7


def response(answer, claim):
    return {'answer':answer,'confidence':'high','abstained':False,
            'claims':[{'claim_id':'fact','text':claim,'citation_ids':['c1']}],
            'citations':[{'chunk_id':'c1'}]}


@pytest.mark.parametrize('answer,claim,source', [
    ('Course MATH101 has 99 credits.', 'Course MATH101 has 3 credits.', 'Course MATH101 has 3 credits.'),
    ('Môn MATH101 có 99 tín chỉ.', 'Course MATH101 has 3 credits.', 'Course MATH101 has 3 credits.'),
    ('MATH999 is required.', 'MATH101 is required.', 'MATH101 is required.'),
    ('MATH101 is not required.', 'MATH101 is required.', 'MATH101 is required.'),
    ('The fee is 9000 VND.', 'The fee is 3000 VND.', 'The fee is 3000 VND.'),
    ('The threshold is 15%.', 'The threshold is 15 credits.', 'The threshold is 15 credits.'),
])
def test_supported_hidden_claims_cannot_cover_false_visible_answer(answer, claim, source):
    generated = GroundedAnswerGenerator(FakeLLM(response(answer,claim)), source_citations=True).answer(
        'Explain the document requirement.', [evidence(content=source)])
    assert generated.abstained and not generated.to_public_dict()['citations']


@pytest.mark.parametrize('answer,claim', [
    ('1. Course MATH101 has 3 credits.', 'Course MATH101 has 3 credits.'),
    ('Môn MATH101 có 3 tín chỉ.', 'Course MATH101 has 3 credits.'),
    ('Course MATH101 has 3.0 credits.', 'Course MATH101 has 3 credits.'),
])
def test_equivalent_numbers_translation_and_list_labels_are_not_false_conflicts(answer,claim):
    generated = GroundedAnswerGenerator(FakeLLM(response(answer,claim)), source_citations=True).answer(
        'Explain the document requirement.', [evidence(content='Course MATH101 has 3 credits.')])
    assert not generated.abstained
