"""Dependency-free TF-IDF cosine retriever with a dense-retrieval-compatible API."""
from collections import Counter
import math
from .bm25_retriever import RetrievalResult, tokenize

class DenseRetriever:
    def __init__(self, items=(), *, text_key="text"):
        self.items = list(items); self.text_key = text_key
        docs = [self._text(item) for item in self.items]
        self.tokens = [tokenize(doc) for doc in docs]
        self.df = Counter(term for row in self.tokens for term in set(row))
        self.vectors = [self._vector(row) for row in self.tokens]
    def _text(self, item):
        return str(item.get(self.text_key, "")) if isinstance(item, dict) else str(getattr(item, self.text_key, item))
    def _vector(self, tokens):
        counts = Counter(tokens); total = len(tokens) or 1
        return {term: (count / total) * math.log((1 + len(self.items)) / (1 + self.df[term])) for term, count in counts.items()}
    def search(self, query: str, *, top_k: int = 5):
        query_vector = self._vector(tokenize(query)); qnorm = math.sqrt(sum(v*v for v in query_vector.values())) or 1.0
        scored = []
        for item, vector in zip(self.items, self.vectors):
            denom = qnorm * (math.sqrt(sum(v*v for v in vector.values())) or 1.0)
            score = sum(query_vector.get(key, 0.0) * value for key, value in vector.items()) / denom
            if score > 0: scored.append((score, item))
        scored.sort(key=lambda value: value[0], reverse=True)
        return [RetrievalResult(item, score, rank) for rank, (score, item) in enumerate(scored[:top_k], 1)]
    retrieve = search

