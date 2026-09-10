"""Adaptive pipeline facade with a stable query contract."""
from .hybrid_rag import HybridRAG, RAGResponse
from agentic_rag.agent.planner import plan_question

class AdaptiveAgenticRAG(HybridRAG):
    def answer(self, question: str, *, top_k: int = 5) -> RAGResponse:
        response = super().answer(question, top_k=top_k)
        plan = plan_question(question)
        response.route = plan.route.name
        return response

