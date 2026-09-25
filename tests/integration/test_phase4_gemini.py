"""Opt-in live-provider Basic RAG contract evidence."""

import os

import pytest

from campusai.llm import GeminiClient, SQLiteLLMCache
from campusai.rag.grounding import ANSWER_SCHEMA, GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_INTEGRATION") != "1" or not os.getenv("GEMINI_API_KEY"),
    reason="set RUN_LLM_INTEGRATION=1 and GEMINI_API_KEY to run live Phase 4 evidence",
)


def test_live_gemini_grounded_answer_has_valid_fixture_citation(tmp_path):
    client = GeminiClient(
        os.environ["GEMINI_API_KEY"],
        model=os.getenv("PHASE4_LLM_MODEL", "gemini-3.8-flash"),
        cache=SQLiteLLMCache(str(tmp_path / "phase4-live.sqlite")),
        max_retries=1,
    )
    result = RetrievalResult(
        "phase4-live-c1",
        "golden-graduation",
        1,
        "Graduation requires 130 credits and completion of an internship.",
        "text",
        1.0,
        "hybrid",
        {"page_range": [1, 1], "source_name": "Graduation conditions", "heading_path": ["Graduation"]},
    )
    generator = GroundedAnswerGenerator(client, max_context_chars=3000, max_context_tokens=700)
    # Keep the provider error visible in live CI instead of reducing it to the
    # product-level ``llm_error`` abstention before the assertion below.
    client.generate_json(
        generator.prompt(
            "How many credits and what additional requirement are needed for graduation?",
            [result],
            language="en",
        ),
        schema=ANSWER_SCHEMA,
    )
    answer = generator.answer(
        "How many credits and what additional requirement are needed for graduation?",
        [result],
        language="en",
    )
    assert answer.abstained is False
    assert answer.citations
    assert answer.citations[0].chunk_id == "phase4-live-c1"
    assert answer.citations[0].doc_id == "golden-graduation"
    assert answer.citations[0].page == 1
