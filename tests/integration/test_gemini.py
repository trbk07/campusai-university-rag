"""Opt-in live Gemini contract test (never runs in offline CI)."""
import os
import pytest
from campusai.llm import GeminiClient, SQLiteLLMCache

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_INTEGRATION") != "1" or not os.getenv("GEMINI_API_KEY"),
    reason="set RUN_LLM_INTEGRATION=1 and GEMINI_API_KEY to run live tests",
)


def test_gemini_cache_contract(tmp_path):
    client = GeminiClient(
        os.environ["GEMINI_API_KEY"],
        model="gemini-3.8-flash",
        cache=SQLiteLLMCache(str(tmp_path / "llm.sqlite")),
        max_retries=1,
    )
    first = client.complete("Reply with the word OK.")
    second = client.complete("Reply with the word OK.")
    assert first.text
    assert second.cached is True
    assert second.usage == first.usage
    assert second.latency_ms == first.latency_ms
