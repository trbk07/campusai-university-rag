from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.dense_index import DenseIndex
from campusai.retrieval.fusion import reciprocal_rank_fusion
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.reranker import Reranker


def items():
    return [
        {"chunk_id": "a", "doc_id": "doc", "content": "hoc phan tien quyet semester 2024", "page": 1},
        {"chunk_id": "b", "doc_id": "doc", "content": "hoc phi tuition 2024", "page": 2},
    ]


def test_bm25_and_dense_return_provenance_ids():
    records = items()
    assert BM25Index(records, "vi").search("hoc phan", 1)[0][0] == "a"
    dense = DenseIndex(records)
    dense.build(records)
    assert dense.search("semester", 1)[0][0] == "a"


def test_rrf_prefers_items_seen_in_both_rankings():
    fused = reciprocal_rank_fusion([[('a', 1), ('b', 0.5)], [('a', 1), ('b', 0.5)]], rrf_k=1)
    assert fused[0][0] == "a"
    assert fused[0][1] > fused[-1][1]


def test_hybrid_applies_filters_before_top_k(tmp_path):
    records = [
        {"chunk_id": "a", "doc_id": "doc", "content": "hoc phan 2024", "page": 1, "content_type": "text", "metadata": {"language": "vi"}},
        {"chunk_id": "b", "doc_id": "doc", "content": "hoc phan 2023", "page": 2, "content_type": "text", "metadata": {"language": "en"}},
    ]
    index_dir = tmp_path / "index" / "doc"
    BM25Index(records, "vi").save(index_dir / "bm25.json")
    dense = DenseIndex(records)
    dense.build(records)
    dense.save(index_dir / "dense.json")

    results = HybridRetriever(tmp_path / "index").search(
        "hoc phan", ["doc"], filters={"language": "en"}, top_k=1
    )
    assert [result.chunk_id for result in results] == ["b"]


def test_reranker_caps_candidate_work():
    candidates = [
        {"chunk_id": "a", "content": "prerequisite"},
        {"chunk_id": "b", "content": "course"},
        {"chunk_id": "c", "content": "unrelated"},
    ]
    result = Reranker(max_candidates=2).rerank("prerequisite", candidates, top_k=3)
    assert {item_id for item_id, _score in result} <= {"a", "b"}


def test_hybrid_reuses_query_embedding_across_documents(tmp_path, monkeypatch):
    records = [
        {"chunk_id": "a", "doc_id": "a", "content": "prerequisite", "page": 1},
        {"chunk_id": "b", "doc_id": "b", "content": "prerequisite", "page": 1},
    ]
    for doc_id in ("a", "b"):
        index_dir = tmp_path / "index" / doc_id
        doc_items = [item for item in records if item["doc_id"] == doc_id]
        BM25Index(doc_items, "en").save(index_dir / "bm25.json")
        dense = DenseIndex(doc_items)
        dense.build(doc_items)
        dense.save(index_dir / "dense.json")

    calls = {"count": 0}
    original = DenseIndex.encode_query

    def counted(self, query):
        calls["count"] += 1
        return original(self, query)

    monkeypatch.setattr(DenseIndex, "encode_query", counted)
    results = HybridRetriever(tmp_path / "index").search("prerequisite", ["a", "b"], top_k=1)
    assert results
    assert calls["count"] == 1


def test_hybrid_fast_path_does_not_invoke_reranker(tmp_path):
    records = [{"chunk_id": "a", "doc_id": "doc", "content": "prerequisite", "page": 1}]
    index_dir = tmp_path / "index" / "doc"
    BM25Index(records, "en").save(index_dir / "bm25.json")
    dense = DenseIndex(records)
    dense.build(records)
    dense.save(index_dir / "dense.json")

    class FailingReranker:
        model_name = "should-not-load"

        def rerank(self, *_args, **_kwargs):
            raise AssertionError("fast hybrid path unexpectedly invoked reranker")

    results = HybridRetriever(
        tmp_path / "index", reranker=FailingReranker()
    ).search("prerequisite", ["doc"], mode="hybrid", top_k=1)
    assert results[0].retriever == "hybrid"


def test_hybrid_reranker_failure_falls_back_to_fused_results(tmp_path):
    records = [{"chunk_id": "a", "doc_id": "doc", "content": "prerequisite", "page": 1}]
    index_dir = tmp_path / "index" / "doc"
    BM25Index(records, "en").save(index_dir / "bm25.json")
    dense = DenseIndex(records)
    dense.build(records)
    dense.save(index_dir / "dense.json")

    class FailingReranker:
        model_name = "remote-reranker"

        def rerank(self, *_args, **_kwargs):
            raise RuntimeError("temporary model outage")

    results = HybridRetriever(
        tmp_path / "index", reranker=FailingReranker()
    ).search("prerequisite", ["doc"], mode="hybrid_rerank", top_k=1)
    assert results[0].retriever == "hybrid"


def test_reranker_threshold_is_applied_after_reranking(tmp_path):
    records = [
        {"chunk_id": "a", "doc_id": "doc", "content": "prerequisite", "page": 1},
        {"chunk_id": "b", "doc_id": "doc", "content": "course", "page": 2},
    ]
    index_dir = tmp_path / "index" / "doc"
    BM25Index(records, "en").save(index_dir / "bm25.json")
    dense = DenseIndex(records)
    dense.build(records)
    dense.save(index_dir / "dense.json")

    class FixedReranker:
        model_name = "fixed"

        def rerank(self, _query, candidates, top_k=5):
            return [(item["chunk_id"], 0.9 if item["chunk_id"] == "a" else 0.1) for item in candidates[:top_k]]

    results = HybridRetriever(tmp_path / "index", reranker=FixedReranker()).search(
        "prerequisite", ["doc"], mode="hybrid_rerank", score_threshold=0.5, top_k=2
    )
    assert [result.chunk_id for result in results] == ["a"]
