import json
from concurrent.futures import ThreadPoolExecutor

from campusai.rag.cache import RAGAnswerCache, build_rag_cache_key
from campusai.rag.grounding import GroundedAnswerGenerator, build_context, format_citation
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.index_builder import build_document_indexes
from campusai.retrieval.hybrid import RetrievalResult
from campusai.schemas import Chunk, Document


def evidence(chunk_id="c1", score=1.0, content="MATH101 is required.", metadata=None):
    return RetrievalResult(
        chunk_id, "doc-1", 3, content, "text", score, "hybrid",
        {"page_range": [3, 3], "source_name": "Curriculum", "heading_path": ["Prerequisites"], **(metadata or {})},
    )


class FakeLLM:
    model = "fake-model"

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
        self.prompts = []

    def generate_json(self, prompt, schema=None, **_kwargs):
        self.calls += 1
        self.prompts.append(prompt)
        return self.payload


def valid_payload():
    return {
        "answer": "MATH101 is required.",
        "confidence": "high",
        "abstained": False,
        "citations": [{"chunk_id": "c1", "doc_id": "doc-1", "page": 3, "page_range": [3, 3]}],
    }


def test_context_contains_only_top_k_evidence_and_provenance():
    context = build_context([evidence("c1"), evidence("c2", content="second")], max_chars=1000)
    assert "chunk_id=c1" in context and "chunk_id=c2" in context
    assert "page=3" in context and "doc_id=doc-1" in context
    assert "[EVIDENCE]" in context


def test_context_budget_truncates_content_without_losing_metadata():
    context = build_context([evidence(content="x" * 2000)], max_chars=1000, max_tokens=80)
    assert "chunk_id=c1" in context
    assert "page=3" in context
    assert "truncated=true" in context
    assert len(context) <= 1000


def test_vietnamese_and_english_prompts_are_grounded_and_secret_free():
    llm = FakeLLM(valid_payload())
    generator = GroundedAnswerGenerator(llm, max_context_chars=2000)
    vi = generator.prompt("Môn nào bắt buộc?", [evidence()], "vi")
    en = generator.prompt("Which course is required?", [evidence()], "en")
    assert "Chỉ dùng thông tin trong EVIDENCE" in vi
    assert "Use only the supplied evidence" in en
    assert "c1" in vi and "Curriculum" in en
    assert "api_key" not in vi.lower() and "secret" not in en.lower()


def test_fact_answer_is_short_json_serializable_and_has_document_page():
    answer = GroundedAnswerGenerator(FakeLLM(valid_payload())).answer("Which course?", [evidence()], "en")
    payload = answer.to_dict()
    json.dumps(payload, ensure_ascii=False)
    assert answer.abstained is False
    assert format_citation(answer.citations[0], "en") == "[Curriculum, page 3]"
    assert len(answer.answer) < 1600


def test_invalid_model_output_and_fabricated_citation_abstain():
    invalid = GroundedAnswerGenerator(FakeLLM({"answer": "", "confidence": "high", "citations": []})).answer("q", [evidence()])
    assert invalid.abstained and invalid.reason == "empty_model_answer"
    fabricated = GroundedAnswerGenerator(FakeLLM({**valid_payload(), "citations": [{"chunk_id": "missing", "page": 99}]})).answer("q", [evidence()])
    assert fabricated.abstained and fabricated.reason == "citation_not_in_evidence"


def test_negative_no_evidence_and_low_relevance_do_not_call_llm():
    llm = FakeLLM(valid_payload())
    generator = GroundedAnswerGenerator(llm, min_retrieval_score=0.5)
    assert generator.answer("outside", [], "en").reason == "no_retrieval_evidence"
    assert generator.answer("outside", [evidence(score=0.1)], "en").reason == "no_relevant_evidence"
    assert llm.calls == 0


class FakeRetriever:
    def __init__(self, result):
        from pathlib import Path
        self.index_root = Path(".tmp/phase4-test-index")
        self.reranker = None
        self.result = result
        self.calls = 0

    def search(self, *_args, **_kwargs):
        self.calls += 1
        return self.result


def test_cache_hit_skips_retrieval_and_llm_and_version_isolated():
    retriever = FakeRetriever([evidence()])
    llm = FakeLLM(valid_payload())
    with RAGAnswerCache(":memory:") as cache:
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm), cache=cache)
        first = service.ask("Which course?", language="en", corpus_version="sha256:v1")
        second = service.ask("  Which   course? ", language="en", corpus_version="sha256:v1")
        third = service.ask("Which course?", language="en", corpus_version="sha256:v2")
        assert not first.cache_hit
        assert second.cache_hit and third.cache_hit is False
        assert llm.calls == 2 and retriever.calls == 2


def test_cache_single_flight_avoids_duplicate_concurrent_llm_calls():
    retriever = FakeRetriever([evidence()])
    llm = FakeLLM(valid_payload())
    with RAGAnswerCache(":memory:") as cache:
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm), cache=cache)
        with ThreadPoolExecutor(max_workers=4) as pool:
            answers = list(pool.map(lambda _index: service.ask("same", language="en", corpus_version="v1"), range(4)))
        assert any(not answer.cache_hit for answer in answers)
        assert llm.calls == 1 and retriever.calls == 1


def test_cache_key_is_sha256_and_does_not_contain_secret():
    key = build_rag_cache_key(
        question="q", language="vi", doc_ids=["doc"], filters={}, top_k=5,
        mode="hybrid", corpus_version="sha256:v1", model="m",
        context_budget={"max_chars": 1000, "max_tokens": 200},
    )
    assert len(key) == 64 and "secret" not in key and "api" not in key.lower()


def test_cache_key_changes_for_every_scope_dimension():
    base = dict(
        question="q", language="vi", doc_ids=["doc"], filters={}, top_k=5,
        mode="hybrid", corpus_version="sha256:v1", model="m",
        context_budget={"max_chars": 1000, "max_tokens": 200},
    )
    original = build_rag_cache_key(**base)
    for field, value in {
        "language": "en", "doc_ids": ["other"], "filters": {"year": 2026},
        "top_k": 3, "mode": "dense", "corpus_version": "sha256:v2", "model": "other",
        "context_budget": {"max_chars": 900, "max_tokens": 200},
    }.items():
        changed = dict(base)
        changed[field] = value
        assert build_rag_cache_key(**changed) != original


def test_corpus_version_changes_when_bm25_manifest_changes(tmp_path):
    root = tmp_path / "index"
    doc_id = "d" * 64
    first_doc = Document(doc_id, "fixture.pdf", 1, chunks=[Chunk("c1", doc_id, 1, "course prerequisite")])
    build_document_indexes(first_doc, root)
    retriever = FakeRetriever([])
    retriever.index_root = root
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(None))
    first = service.corpus_version()
    second_doc = Document(doc_id, "fixture.pdf", 1, chunks=[Chunk("c1", doc_id, 1, "course tuition changed")])
    build_document_indexes(second_doc, root)
    assert service.corpus_version() != first
