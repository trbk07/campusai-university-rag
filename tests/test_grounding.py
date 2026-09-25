from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import choose_query_mode
from campusai.retrieval.hybrid import RetrievalResult


def result(chunk_id="c1", page=3):
    return RetrievalResult(
        chunk_id,
        "doc-1",
        page,
        "Điều kiện tiên quyết: MATH101.",
        "text",
        1.0,
        "hybrid",
        {"document_type": "curriculum"},
    )


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def generate_json(self, prompt, schema=None, **kwargs):
        assert "chunk_id=c1" in prompt
        assert schema["required"]
        return self.payload


def test_grounded_answer_accepts_only_retrieved_citations():
    generator = GroundedAnswerGenerator(
        FakeLLM(
            {
                "answer": "Cần hoàn thành MATH101.",
                "confidence": "high",
                "abstained": False,
                "citations": [{"chunk_id": "c1", "page": 3, "quote": "MATH101"}],
            }
        )
    )
    answer = generator.answer("Môn tiên quyết là gì?", [result()])
    assert answer.abstained is False
    assert answer.citations[0].page == 3


def test_grounded_answer_abstains_on_fabricated_citation():
    generator = GroundedAnswerGenerator(
        FakeLLM(
            {
                "answer": "Không chắc.",
                "confidence": "low",
                "abstained": False,
                "citations": [{"chunk_id": "missing", "page": 99}],
            }
        )
    )
    answer = generator.answer("Câu hỏi", [result()])
    assert answer.abstained is True
    assert answer.reason == "citation_not_in_evidence"


def test_no_evidence_abstains_without_calling_llm():
    answer = GroundedAnswerGenerator(FakeLLM({})).answer("Câu hỏi", [])
    assert answer.abstained is True
    assert answer.reason == "no_retrieval_evidence"


def test_hard_questions_only_use_reranker_when_available():
    assert choose_query_mode("So sánh hai chương trình", reranker_available=False) == "hybrid"
    assert choose_query_mode("So sánh hai chương trình", reranker_available=True) == "hybrid_rerank"
