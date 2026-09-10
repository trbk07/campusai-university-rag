"""Optional LLM protocol; core pipeline remains deterministic without an API key."""
from typing import Protocol, Any

class LLMClient(Protocol):
    def complete(self, prompt: str, **kwargs: Any) -> str: ...

class NullLLMClient:
    def complete(self, prompt: str, **kwargs: Any) -> str:
        raise RuntimeError("No LLM client configured; use a deterministic answer builder or inject an LLMClient")

