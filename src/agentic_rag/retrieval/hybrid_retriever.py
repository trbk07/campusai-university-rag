"""Hybrid lexical retrieval with an optional dense retriever."""
from .bm25_retriever import BM25Retriever, RetrievalResult, reciprocal_rank_fusion


class HybridRetriever:
    def __init__(self, items=(), *, lexical=None, dense=None, text_key="text"):
        self.items = list(items)
        self.lexical = lexical or BM25Retriever(self.items, text_key=text_key)
        self.dense = dense

    def search(self, query: str, *, top_k: int = 5, candidate_k: int | None = None) -> list[RetrievalResult]:
        count = candidate_k or max(top_k * 3, 10)
        lists = [self.lexical.search(query, top_k=count)]
        if self.dense is not None:
            dense_results = self.dense.search(query, top_k=count)
            lists.append(dense_results)
        return reciprocal_rank_fusion(lists, top_k=top_k)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        return self.search(query, top_k=top_k)

