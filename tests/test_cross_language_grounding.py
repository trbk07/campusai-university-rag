"""Keep cross-language claims source-verifiable without relaxing validators."""
from copy import deepcopy

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult
from tests.test_basic_rag import FakeLLM


def evidence():
    return RetrievalResult('stack-chunk','stack-document',3,
        'A stack uses LIFO, last in first out. A queue uses FIFO, first in first out.',
        'text',1.0,'hybrid',{'language':'en','page_range':[3,3],'source_name':'Stacks.pdf'})


def payload():
    return {'answer':'Stack sử dụng LIFO: phần tử vào sau được lấy ra trước.',
        'confidence':'high','abstained':False,
        'claims':[{'claim_id':'stack-order','text':'A stack uses LIFO, last in first out.','citation_ids':['stack-chunk']}],
        'citations':[{'chunk_id':'stack-chunk','page':3,'quote':'A stack uses LIFO, last in first out.'}]}


def test_vietnamese_answer_keeps_verifiable_original_english_claim():
    provider = FakeLLM(payload())
    answer = GroundedAnswerGenerator(provider).answer('Stack dùng LIFO hay FIFO?',[evidence()],language='vi')
    assert not answer.abstained and answer.to_public_dict()['citations'][0]['page'] == 3
    assert answer.claims[0].text == 'A stack uses LIFO, last in first out.'
    assert 'Do not translate verification claims' in provider.prompts[0]
    assert 'a claim must not add any fact that the answer omits' in provider.prompts[0]
    assert 'ngắn gọn' in provider.prompts[0]


def test_cross_language_prompt_does_not_admit_unsupported_claims():
    wrong = deepcopy(payload())
    wrong['claims'][0]['text'] = 'Stack yêu cầu đăng ký tín chỉ và phê duyệt của giáo viên.'
    answer = GroundedAnswerGenerator(FakeLLM(wrong)).answer('Stack hoạt động thế nào?',[evidence()],language='vi')
    assert answer.abstained and answer.to_public_dict()['citations'] == []


def test_source_wording_guidance_applies_to_same_language_without_translation_instruction():
    generator = GroundedAnswerGenerator(None)
    assert 'Do not translate verification claims' not in generator.prompt('What order?',[evidence()],language='en')
    assert 'exact wording of the cited evidence' in generator.prompt('What order?',[evidence()],language='en')
    assert 'Do not copy a neighboring role or list item' in generator.prompt(
        'Which roles are listed?',[evidence()],language='en')
    item = evidence()
    item.metadata['language'] = 'vi'
    assert 'Do not translate verification claims' not in generator.prompt('Thứ tự nào?',[item],language='vi')
