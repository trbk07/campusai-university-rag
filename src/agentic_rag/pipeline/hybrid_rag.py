"""Deterministic retrieval-to-evidence RAG pipeline."""
from dataclasses import dataclass
from typing import Any
from agentic_rag.retrieval.hybrid_retriever import HybridRetriever
from agentic_rag.verification.answer_verifier import verify_answer

@dataclass
class RAGResponse:
    answer: str
    evidence: list[dict[str, Any]]
    citations: list[str]
    verification: dict[str, Any]
    route: str = "fact"

class HybridRAG:
    def __init__(self, items=(), retriever=None):
        self.items = list(items)
        self.retriever = retriever or HybridRetriever(self.items)
    def answer(self, question: str, *, top_k: int = 5) -> RAGResponse:
        results = self.retriever.retrieve(question, top_k=top_k)
        evidence = []
        for index, result in enumerate(results):
            item = result.item
            evidence_id = str(item.get("id", index)) if isinstance(item, dict) else str(index)
            text = str(item.get("text", item)) if isinstance(item, dict) else str(item)
            evidence.append({"id": evidence_id, "text": text, "score": result.score})
        citations = [row["id"] for row in evidence]
        answer = evidence[0]["text"] if evidence else "Không tìm thấy bằng chứng phù hợp."
        verification = verify_answer(answer, evidence={row["id"]: row["text"] for row in evidence}, citations=citations)
        return RAGResponse(answer, evidence, citations, verification)
    query = answer

class HybridRAGPipeline(HybridRAG): pass

