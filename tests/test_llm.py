from finrag.llm.cache import SQLiteLLMCache
from finrag.llm.client import OpenAICompatibleClient

def test_cache_keeps_original_metadata(tmp_path):
    cache = SQLiteLLMCache(str(tmp_path / "cache.sqlite"))
    cache.put("k", "answer", {"total_tokens": 3}, 12.5)
    hit = cache.get("k")
    assert hit and hit.text == "answer" and hit.usage["total_tokens"] == 3
    assert hit.latency_ms == 12.5

def test_client_uses_cache_without_network(tmp_path):
    cache = SQLiteLLMCache(str(tmp_path / "cache.sqlite"))
    client = OpenAICompatibleClient("http://invalid", "key", "model", cache=cache)
    cache_key_payload = '{"messages": [{"content": "hi", "role": "user"}], "model": "model"}'
    import hashlib
    cache.put(hashlib.sha256(cache_key_payload.encode()).hexdigest(), "cached", {}, 9)
    response = client.complete("hi")
    assert response.cached and response.text == "cached"
