"""Deterministic lexical reranker; optional model rerankers can implement the same API."""
from .bm25_retriever import RetrievalResult, tokenize

class LexicalReranker:
    def score(self, query: str, item) -> float:
        query_terms = set(tokenize(query)); text = item.get("text", "") if isinstance(item, dict) else getattr(item, "text", item)
        terms = tokenize(text)
        return len(query_terms & set(terms)) / len(query_terms) if query_terms else 0.0
    def rerank(self, query: str, results, *, top_k: int = 5):
        ranked = sorted(results, key=lambda result: self.score(query, result.item), reverse=True)[:top_k]
        return [RetrievalResult(result.item, self.score(query, result.item), rank) for rank, result in enumerate(ranked, 1)]
    __call__ = rerank

Reranker = LexicalReranker

