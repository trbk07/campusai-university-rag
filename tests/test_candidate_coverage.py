from campusai.retrieval.hybrid import RetrievalResult
from evaluation.retrieval.evaluate_candidate_coverage import evaluate_split


def _result(chunk_id, doc_id="doc"):
    return RetrievalResult(chunk_id, doc_id, 1, "content", "text", 1.0,
                           "hybrid_rrf", {"page_range": [1, 1]})


def test_candidate_recall_checks_gold_scope_and_provenance():
    rows = [{"qid": "q1", "question": "query", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "b"}], "filters": {}},
            {"qid": "q2", "question": "outside", "answerable": False,
             "gold_evidence": [], "filters": {}}]

    class Retriever:
        def search(self, query, **_kwargs):
            return [_result("a"), _result("b")] if query == "query" else []

    result = evaluate_split(rows, Retriever(), ["doc"], 40)
    assert result["candidate_recall"] == 1.0
    assert result["provenance_errors"] == 0
    assert result["scope_errors"] == 0
    assert result["candidate_misses"] == []


def test_candidate_recall_does_not_hide_missing_gold():
    rows = [{"qid": "q1", "question": "query", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "b"}], "filters": {}}]

    class Retriever:
        def search(self, *_args, **_kwargs):
            return [_result("a")]

    result = evaluate_split(rows, Retriever(), ["doc"], 40)
    assert result["candidate_recall"] == 0.0
    assert result["candidate_misses"][0]["qid"] == "q1"
