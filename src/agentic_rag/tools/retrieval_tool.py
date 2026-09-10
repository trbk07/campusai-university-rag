"""Tool wrapper for retrieval with stable, serializable results."""
from .base_tool import ToolResult, failure, success

class RetrievalTool:
    def __init__(self, retriever): self.retriever = retriever
    def run(self, query: str, *, top_k: int = 5) -> ToolResult:
        if not query or not query.strip(): return failure("Query must not be empty")
        results = self.retriever.retrieve(query, top_k=top_k)
        return success([{"item": result.item, "score": result.score, "rank": result.rank} for result in results])

def retrieve(retriever, query: str, top_k: int = 5) -> ToolResult:
    return RetrievalTool(retriever).run(query, top_k=top_k)

