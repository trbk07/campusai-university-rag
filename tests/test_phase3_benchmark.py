import json
from pathlib import Path

from evaluation.benchmark import validate_records
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.run_retrieval_benchmark import _corpus_metadata, _indexed_document_ids, _negative_metrics, _percentile, load_calibration_threshold, load_jsonl


def test_negative_records_may_have_empty_gold_evidence():
    record = {"qid": "n1", "split": "test", "question": "unknown", "category": "negative", "query_type": "negative", "difficulty": "easy", "gold_answer": {"text": ""}, "gold_evidence": []}
    assert validate_records([record], "test", expected_count=1) == []


def test_negative_metrics_report_abstention_and_false_positive_rates():
    records = [{"qid": "n1", "category": "negative"}, {"qid": "n2", "query_type": "negative"}]
    assert _negative_metrics(records, {"n1": 0, "n2": 2}, 5) == {
        "n": 2, "abstention_rate": 0.5, "false_positive_rate": 0.5, "mean_results": 1, "top_k": 5
    }


def test_corpus_metadata_reads_manifest_fields(tmp_path):
    root = tmp_path / "doc"
    root.mkdir()
    (root / "dense.json").write_text(json.dumps({"manifest": {
        "model_name": "model", "model_revision": "r1", "provider": "hash",
        "embedding_dimension": 256, "item_count": 3, "corpus_hash": "abc"
    }, "items": [{}, {}, {}]}), encoding="utf-8")
    metadata = _corpus_metadata(tmp_path, ["doc"])
    assert metadata["document_count"] == 1
    assert metadata["chunk_count"] == 3
    assert metadata["models"] == ["model"]


def test_benchmark_indexes_all_complete_documents_not_gold_scope(tmp_path):
    for doc_id in ("doc-a", "doc-b"):
        root = tmp_path / doc_id
        root.mkdir()
        (root / "bm25.json").write_text("{}", encoding="utf-8")
        (root / "dense.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "incomplete").mkdir()
    assert _indexed_document_ids(tmp_path) == ["doc-a", "doc-b"]


def test_phase3_test_split_has_one_hundred_valid_records():
    path = Path("data/benchmark/retrieval_test.jsonl")
    records = load_jsonl(path)
    assert len(records) == 100
    assert validate_records(records, "test", expected_count=100) == []
    assert {record["language"] for record in records} == {"vi", "en", "mixed"}
    assert {record["difficulty"] for record in records} == {"easy", "medium", "hard"}


def test_score_threshold_is_validated_and_reported():
    retriever = HybridRetriever("missing", query_cache_size=0)
    try:
        retriever.search("q", [], top_k=1, score_threshold=-0.1)
    except ValueError as error:
        assert "score_threshold" in str(error)
    else:
        raise AssertionError("negative score threshold must fail")


def test_percentile_is_deterministic():
    assert _percentile([3.0, 1.0, 2.0], 50) == 2.0
    assert _percentile([], 95) is None


def test_calibration_report_loads_locked_threshold(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"mode": "hybrid_rerank", "calibration_split": "dev", "result": {"threshold": 0.46367466}}), encoding="utf-8")
    threshold, source = load_calibration_threshold(path)
    assert threshold == 0.46367466
    assert source["mode"] == "hybrid_rerank"


def test_calibration_report_rejects_missing_mode(tmp_path):
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps({"result": {"threshold": 0.2}}), encoding="utf-8")
    try:
        load_calibration_threshold(path)
    except ValueError as error:
        assert "retrieval mode" in str(error)
    else:
        raise AssertionError("calibration report without a mode must fail")
