"""Run the approved packet collector with urllib-client close compatibility.

GeminiClient opens/closes each urllib response inside the request context and
has no persistent session/close method. The prepared collector calls close
unconditionally; supply a documented no-op without changing its approved
prompt packet or provider's generate methods. No mocked provider is used.
"""
from campusai.llm.client import GeminiClient
from scripts.benchmarks.phase7_repaired_answer_pilot import main


def close_stateless_client(self):
    """There is no persistent HTTP session in this cache-disabled client."""
    if self.cache is not None:
        self.cache.close()


if __name__ == '__main__':
    if not hasattr(GeminiClient, 'close'):
        GeminiClient.close = close_stateless_client
    raise SystemExit(main())
