import json
from concurrent.futures import ThreadPoolExecutor

from campusai.rag.cache import RAGAnswerCache, build_rag_cache_key
from campusai.rag.grounding import GroundedAnswerGenerator, build_context, estimate_tokens, format_citation
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
        "citations": [{"chunk_id": "c1", "doc_id": "doc-1", "page": 3, "page_range": [3, 3],
                       "quote": "MATH101 is required."}],
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


def test_context_budget_includes_serialized_separators():
    items = [evidence("c1", content="a" * 100), evidence("c2", content="b" * 100)]
    single_lengths = sum(len(build_context([item])) for item in items)
    context = build_context(items, max_chars=single_lengths)
    assert len(context) <= single_lengths
    assert "chunk_id=c1" in context and "chunk_id=c2" in context
    token_limit = single_lengths // 4
    context = build_context(items, max_tokens=token_limit)
    assert estimate_tokens(context) <= token_limit


def test_context_skips_block_without_room_for_excerpt_and_truncation_marker():
    item = evidence(content="x" * 200)
    metadata_length = len(build_context([evidence(content="x")])) - 1
    for remaining in (1, len("\n[truncated=true]")):
        assert build_context([item], max_chars=metadata_length + remaining) == ""


def test_context_excludes_generated_header_preserving_source_and_table_json():
    table = '{"headers": ["Course", "Credits"], "rows": [["MATH101", "3"]]}'
    original = "[Document type: curriculum | Academic years: 2025, 2026 | Page: 3]\n" + table
    item = evidence(content=original, metadata={"table_id": "t1"})
    context = build_context([item])
    assert "Academic years:" not in context
    assert "page=3" in context and "table_id=t1" in context
    assert table in context
    assert item.content == original


def test_context_preserves_bracketed_source_text_and_respects_combined_budgets():
    items = [evidence(str(i), content="[Original source heading]\n" + "đúng " * 100) for i in range(3)]
    assert "[Original source heading]" in build_context(items)
    for chars in (0, 100, 125, 240, 1000):
        for tokens in (0, 30, 60, 250):
            context = build_context(items, max_chars=chars, max_tokens=tokens)
            assert len(context) <= chars
            assert estimate_tokens(context) <= tokens
            assert not context.endswith("content:\n\n[truncated=true]")


def test_context_prompt_revision_isolated_from_old_cached_answers():
    from campusai.rag.cache import PROMPT_VERSION

    assert PROMPT_VERSION != "grounding-v1"
    args = dict(question="q", language="en", doc_ids=["doc-1"], filters={}, top_k=5,
                mode="hybrid", model="fake-model", corpus_version="v1", context_budget={})
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, prompt_version="grounding-v1")
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, prompt_version="grounding-context-v2")
    assert build_rag_cache_key(**args) != build_rag_cache_key(**args, prompt_version="grounding-context-v3")


def test_invalid_public_citation_is_not_cached_and_recovers_when_quote_is_fixed():
    llm = FakeLLM(valid_payload())
    llm.payload["citations"][0].pop("quote")
    retriever = type("Retriever", (), {"reranker": None, "search": lambda *_a, **_kw: [evidence()]})()
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm))
    try:
        first = service.ask("Which course is required?", corpus_version="fixed")
        assert first.to_public_dict()["abstained"] is True
        llm.payload = valid_payload()
        second = service.ask("Which course is required?", corpus_version="fixed")
        assert not second.to_public_dict()["abstained"]
        assert llm.calls == 2 and not service.last_cache_hit
        third = service.ask("Which course is required?", corpus_version="fixed")
        assert not third.to_public_dict()["abstained"] and service.last_cache_hit
        assert llm.calls == 2
    finally:
        service.close()


def test_vietnamese_and_english_prompts_are_grounded_and_secret_free():
    llm = FakeLLM(valid_payload())
    generator = GroundedAnswerGenerator(llm, max_context_chars=2000)
    vi = generator.prompt("Môn nào bắt buộc?", [evidence()], "vi")
    en = generator.prompt("Which course is required?", [evidence()], "en")
    assert "Chỉ dùng thông tin trong EVIDENCE" in vi
    assert "Use only the supplied evidence" in en
    assert "STRICT SCOPE AND CITATIONS" in en
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


def test_transient_llm_failure_does_not_pin_abstention_in_answer_cache():
    from campusai.llm.client import LLMProviderError

    class RecoveringLLM(FakeLLM):
        def generate_json(self, prompt, **kwargs):
            if self.calls == 0:
                self.calls += 1
                raise LLMProviderError("temporary provider failure")
            return super().generate_json(prompt, **kwargs)

    retriever = FakeRetriever([evidence()])
    llm = RecoveringLLM(valid_payload())
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm))
    try:
        failed = service.ask("Which course?", language="en", corpus_version="v1")
        recovered = service.ask("Which course?", language="en", corpus_version="v1")
        cached = service.ask("Which course?", language="en", corpus_version="v1")
        assert failed.abstained and failed.reason == "llm_error"
        assert failed.answer == "The answer service is temporarily unavailable. Please try again later."
        assert not recovered.abstained and not recovered.cache_hit
        assert cached.cache_hit and not cached.abstained
        assert llm.calls == 2 and retriever.calls == 2
    finally:
        service.close()


def test_gemini_http_503_reports_service_error_then_recovers_without_cache_poisoning(monkeypatch):
    import io
    import urllib.error
    from campusai.llm.client import GeminiClient

    attempts = []

    def transport(request, timeout):
        attempts.append(request)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(request.full_url, 503, "UNAVAILABLE", {}, io.BytesIO(
                b'{"error":{"status":"UNAVAILABLE","message":"High demand; private-provider-detail"}}'))
        payload = valid_payload()
        payload["citations"] = [{"chunk_id": "c1", "page": 3, "quote": "MATH101 is required."}]
        return io.BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(payload)}]}}]}).encode())

    monkeypatch.setattr("urllib.request.urlopen", transport)
    monkeypatch.setattr("campusai.llm.client._sleep_backoff",
                        lambda *args: (_ for _ in ()).throw(AssertionError("unexpected retry")))
    client = GeminiClient("fake-local-test-key", max_retries=0, cache=None)
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(client),
                                   cache=RAGAnswerCache(":memory:"))
    try:
        failed = service.ask("Which course?", language="vi", corpus_version="503-recovery")
        assert len(attempts) == 1 and failed.abstained and failed.reason == "llm_error"
        public = failed.to_public_dict()
        assert public["answer"] == "Dịch vụ trả lời đang gặp lỗi; vui lòng thử lại sau."
        assert public["citations"] == [] and public["claims"] == []
        assert "private-provider-detail" not in json.dumps(public)
        recovered = service.ask("Which course?", language="vi", corpus_version="503-recovery")
        cached = service.ask("Which course?", language="vi", corpus_version="503-recovery")
        assert not recovered.abstained and not recovered.cache_hit
        assert not cached.abstained and cached.cache_hit and len(attempts) == 2
    finally:
        service.close()


def test_contradicted_abstention_never_publishes_rejected_claims_or_citations():
    payload = {
        "answer": "CS101 requires 9 credits.", "confidence": "high", "abstained": False,
        "citations": [{"chunk_id": "c1", "page": 3, "quote": "CS101 requires 3 credits."}],
        "claims": [{"claim_id": "claim-1", "text": "CS101 requires 9 credits.", "citation_ids": ["c1"]}],
    }
    answer = GroundedAnswerGenerator(FakeLLM(payload)).answer(
        "How many credits does CS101 require?", [evidence(content="CS101 requires 3 credits.")])
    assert answer.abstained and answer.reason == "contradicted_claim"
    internal = answer.to_dict()
    assert internal["claims"] and internal["claims"][0]["status"] == "contradicted"
    public = answer.to_public_dict()
    assert public["abstained"] and public["claims"] == [] and public["citations"] == []
    assert "9 credits" not in public["answer"]


def test_cache_single_flight_avoids_duplicate_concurrent_llm_calls():
    retriever = FakeRetriever([evidence()])
    llm = FakeLLM(valid_payload())
    with RAGAnswerCache(":memory:") as cache:
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm), cache=cache)
        with ThreadPoolExecutor(max_workers=4) as pool:
            answers = list(pool.map(lambda _index: service.ask("same", language="en", corpus_version="v1"), range(4)))
        assert any(not answer.cache_hit for answer in answers)
        assert llm.calls == 1 and retriever.calls == 1


def test_generation_setting_change_cannot_reuse_an_old_answer():
    llm = FakeLLM(valid_payload())
    llm.generation_config = {"temperature": 1, "thinkingConfig": {"thinkingLevel": "low"}}
    service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
    try:
        first = service.ask("Which course?", language="en", corpus_version="v1")
        llm.generation_config["thinkingConfig"]["thinkingLevel"] = "medium"
        second = service.ask("Which course?", language="en", corpus_version="v1")
        third = service.ask("Which course?", language="en", corpus_version="v1")
        assert not first.cache_hit and not second.cache_hit and third.cache_hit
        assert llm.calls == 2
    finally:
        service.close()


def test_native_schema_mode_invalidates_both_answer_cache_routes():
    for source_pages in (False, True):
        llm = FakeLLM(valid_payload())
        service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
        def ask():
            return (service.ask_source_pages('Which course?', [evidence()], language='en') if source_pages
                    else service.ask('Which course?', language='en', corpus_version='v1'))
        try:
            ask()
            original_calls=llm.calls
            # An explicit legacy default preserves the old fingerprint.
            llm.response_format_mode='json_object'
            ask()
            assert service.last_cache_hit and llm.calls==original_calls
            llm.response_format_mode='json_schema'
            ask()
            assert not service.last_cache_hit and llm.calls==original_calls+1
            ask()
            assert service.last_cache_hit and llm.calls==original_calls+1
        finally:
            service.close()


def test_optional_system_policy_invalidates_both_cache_routes():
    for source_pages in (False, True):
        llm=FakeLLM(valid_payload())
        service=CampusAIQueryService(FakeRetriever([evidence()]),GroundedAnswerGenerator(llm))
        def ask():
            return (service.ask_source_pages('Which course?',[evidence()],language='en') if source_pages
                    else service.ask('Which course?',language='en',corpus_version='v1'))
        try:
            ask();before=llm.calls
            llm.default_system_prompt=None;ask()
            assert service.last_cache_hit and llm.calls==before
            llm.default_system_prompt='Preserve all necessary source qualifiers.';ask()
            assert not service.last_cache_hit and llm.calls==before+1
            ask();assert service.last_cache_hit
        finally:
            service.close()


def test_schema_references_use_all_retrieved_ids_and_leave_legacy_schema_unchanged():
    llm=FakeLLM(valid_payload())
    generator=GroundedAnswerGenerator(llm,source_citations=True)
    old=generator.response_schema()
    llm.response_format_mode='json_schema'
    schema=generator.response_schema([evidence('c1'),evidence('decoy')])
    assert schema['properties']['citations']['items']['properties']['chunk_id']['enum']==['c1','decoy']
    assert schema['properties']['claims']['items']['properties']['citation_ids']['items']['enum']==['c1','decoy']
    assert list(schema['properties'])[:2]==['citations','claims']
    llm.response_format_mode='json_object'
    assert generator.response_schema([evidence('c1')])==old


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


def test_corpus_version_changes_when_bm25_manifest_changes(tmp_path, request):
    root = tmp_path / "index"
    doc_id = "d" * 64
    first_doc = Document(doc_id, "fixture.pdf", 1, chunks=[Chunk("c1", doc_id, 1, "course prerequisite")])
    build_document_indexes(first_doc, root)
    retriever = FakeRetriever([])
    retriever.index_root = root
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(None))
    request.addfinalizer(service.close)
    first = service.corpus_version()
    second_doc = Document(doc_id, "fixture.pdf", 1, chunks=[Chunk("c1", doc_id, 1, "course tuition changed")])
    build_document_indexes(second_doc, root)
    assert service.corpus_version() != first
