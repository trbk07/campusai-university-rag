from campusai.retrieval.hybrid import RetrievalResult
from evaluation.retrieval.evaluate_candidate_coverage import audit_outputs, coverage_errors, evaluate_split


def _result(chunk_id, doc_id="doc"):
    return RetrievalResult(chunk_id, doc_id, 1, "content", "text", 1.0,
                           "hybrid_rrf", {"page_range": [1, 1]})


def test_candidate_recall_checks_gold_scope_and_provenance():
    rows = [{"qid": "q1", "question": "query", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "b"}], "filters": {}},
            {"qid": "q2", "question": "outside", "answerable": False,
             "gold_evidence": [], "filters": {}}]

    class Retriever:
        def generate_candidates(self, query, **_kwargs):
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
        def generate_candidates(self, *_args, **_kwargs):
            return [_result("a")]

    result = evaluate_split(rows, Retriever(), ["doc"], 40)
    assert result["candidate_recall"] == 0.0
    assert result["candidate_misses"][0]["qid"] == "q1"


def test_document_diagnostics_distinguish_wrong_document_wrong_chunk_and_missing_hop():
    rows = [{"qid": qid, "question": "q", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "b", "page": 1}], "filters": {}}
            for qid in ("wrong_doc", "wrong_chunk", "partial", "found", "out_of_scope", "wrong_page")]
    rows[2]["gold_evidence"].append({"doc_id": "other", "chunk_id": "c", "page": 1})
    rows[4]["doc_ids"] = ["other"]
    outputs = {"wrong_doc": [_result("b", "other").to_dict()],
               "wrong_chunk": [_result("a").to_dict()], "partial": [_result("b").to_dict()],
               "found": [_result("b").to_dict()], "out_of_scope": [_result("b").to_dict()],
               "wrong_page": [_result("b").to_dict()]}
    rows[5]["gold_evidence"][0]["page"] = 2
    plain = audit_outputs(rows, outputs, ["doc", "other"], 40)
    report = audit_outputs(rows, outputs, ["doc", "other"], 40, include_document_diagnostics=True)
    diagnostic = report.pop("document_diagnostics")
    assert report == plain
    assert "document_diagnostics" not in plain
    assert coverage_errors(plain, .99)
    assert diagnostic["all_document_recall"] == .5
    assert diagnostic["diagnosis_counts"] == {
        "no_gold_document_found": 2, "all_documents_found_evidence_missing": 2,
        "partial_documents_found": 1, "all_gold_evidence_found": 1}


def test_document_diagnostics_exclude_invalid_provenance_and_negatives():
    rows = [{"qid": "q", "question": "q", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "b"}], "filters": {}}]
    outputs = {"q": [_result("b").to_dict()]}
    report = audit_outputs(rows, outputs, ["doc"], 40, evidence={}, include_document_diagnostics=True)
    assert report["document_diagnostics"]["diagnosis_counts"]["no_gold_document_found"] == 1
    assert report["provenance_errors"] == 1
    rows[0].update(answerable=False, gold_evidence=[])
    report = audit_outputs(rows, outputs, ["doc"], 40, include_document_diagnostics=True)
    assert report["document_diagnostics"]["all_document_recall"] is None
    assert report["document_diagnostics"]["per_query"] == []
