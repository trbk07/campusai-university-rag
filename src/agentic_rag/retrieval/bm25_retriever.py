"""Dependency-free lexical retrieval with BM25-style scoring."""
from dataclasses import dataclass
import math
import re
from collections import Counter
from typing import Any, Iterable

_TOKEN = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


def tokenize(text: object) -> list[str]:
    return [token.casefold() for token in _TOKEN.findall(str(text))]


@dataclass(frozen=True)
class RetrievalResult:
    item: Any
    score: float
    rank: int


class BM25Retriever:
    def __init__(self, items: Iterable[Any] = (), *, text_key: str = "text", k1: float = 1.5, b: float = 0.75):
        self.text_key, self.k1, self.b = text_key, k1, b
        self.items = list(items)
        self._tokens = [tokenize(self._text(item)) for item in self.items]
        self._df = Counter(token for tokens in self._tokens for token in set(tokens))
        self._avgdl = sum(map(len, self._tokens)) / len(self._tokens) if self._tokens else 0.0

    def _text(self, item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get(self.text_key, ""))
        return str(getattr(item, self.text_key, item))

    def search(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        query_tokens = tokenize(query)
        n = len(self.items)
        if not query_tokens or not n:
            return []
        scores = []
        for item, tokens in zip(self.items, self._tokens):
            counts = Counter(tokens)
            score = 0.0
            for term in query_tokens:
                if not counts[term]:
                    continue
                df = self._df[term]
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                norm = counts[term] * (self.k1 + 1) / (counts[term] + self.k1 * (1 - self.b + self.b * len(tokens) / (self._avgdl or 1)))
                score += idf * norm
            scores.append((score, item))
        scores.sort(key=lambda pair: pair[0], reverse=True)
        return [RetrievalResult(item, score, rank) for rank, (score, item) in enumerate(scores[:top_k], 1) if score > 0]

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        return self.search(query, top_k=top_k)


BM25 = BM25Retriever

def reciprocal_rank_fusion(result_lists: Iterable[Iterable[RetrievalResult]], *, k: int = 60, top_k: int = 10) -> list[RetrievalResult]:
    scores: dict[int, float] = {}
    items: dict[int, Any] = {}
    for results in result_lists:
        for rank, result in enumerate(results, 1):
            key = id(result.item)
            items[key] = result.item
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores, key=scores.get, reverse=True)[:top_k]
    return [RetrievalResult(items[key], scores[key], rank) for rank, key in enumerate(ordered, 1)]

__all__ = ["BM25Retriever", "BM25", "RetrievalResult", "tokenize", "reciprocal_rank_fusion"]

