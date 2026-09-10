"""Compatibility alias for the deterministic RAG pipeline."""
from .hybrid_rag import HybridRAG, RAGResponse

class NaiveRAG(HybridRAG): pass

