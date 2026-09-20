from finrag.retrieval.bm25_index import BM25Index
from finrag.retrieval.dense_index import DenseIndex
from finrag.retrieval.fusion import reciprocal_rank_fusion
from finrag.retrieval.hybrid import HybridRetriever


def items():
    return [
        {"chunk_id": "a", "doc_id": "doc", "content": "doanh thu revenue 2024", "page": 1},
        {"chunk_id": "b", "doc_id": "doc", "content": "chi phí expense 2024", "page": 2},
    ]


def test_bm25_and_dense_return_provenance_ids():
    records = items()
    assert BM25Index(records, "vi").search("doanh thu", 1)[0][0] == "a"
    dense = DenseIndex(records)
    dense.build(records)
    assert dense.search("revenue", 1)[0][0] == "a"


def test_rrf_prefers_items_seen_in_both_rankings():
    fused = reciprocal_rank_fusion([[('a', 1), ('b', 0.5)], [('a', 1), ('b', 0.5)]], rrf_k=1)
    assert fused[0][0] == "a"
    assert fused[0][1] > fused[-1][1]


def test_hybrid_applies_filters_before_top_k(tmp_path):
    records = [
        {"chunk_id": "a", "doc_id": "doc", "content": "doanh thu 2024", "page": 1, "content_type": "text", "metadata": {"language": "vi"}},
        {"chunk_id": "b", "doc_id": "doc", "content": "doanh thu 2023", "page": 2, "content_type": "text", "metadata": {"language": "en"}},
    ]
    index_dir = tmp_path / "index" / "doc"
    BM25Index(records, "vi").save(index_dir / "bm25.json")
    dense = DenseIndex(records)
    dense.build(records)
    dense.save(index_dir / "dense.json")

    results = HybridRetriever(tmp_path / "index").search(
        "doanh thu", ["doc"], filters={"language": "en"}, top_k=1
    )
    assert [result.chunk_id for result in results] == ["b"]
