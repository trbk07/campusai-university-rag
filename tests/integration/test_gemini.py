"""Opt-in live Gemini contract test (never runs in offline CI)."""
import os
from pathlib import Path
import pytest
from campusai.llm import GeminiClient, SQLiteLLMCache
from campusai.llm.factory import _read_config

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_INTEGRATION") != "1" or not os.getenv("GEMINI_API_KEY"),
    reason="set RUN_LLM_INTEGRATION=1 and GEMINI_API_KEY to run live tests",
)


def test_gemini_cache_contract(tmp_path):
    config = _read_config(Path(__file__).resolve().parents[2] / 'configs/product_llm.yaml')['llm']
    client = GeminiClient(
        os.environ["GEMINI_API_KEY"],
        model=config['model'], generation_config=config['generation_config'],
        cache=SQLiteLLMCache(str(tmp_path / "llm.sqlite")),
        max_retries=config['max_retries'], timeout=config['timeout_seconds'],
        retry_only_503=config.get('retry_only_503', False),
    )
    first = client.complete("Reply with the word OK.")
    second = client.complete("Reply with the word OK.")
    assert first.text
    assert second.cached is True
    assert second.usage == first.usage
    assert second.latency_ms == first.latency_ms
