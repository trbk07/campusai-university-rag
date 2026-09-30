from types import SimpleNamespace

from evaluation.retrieval_failure_cases import failure_cases


def test_failure_export_contains_route_ranks_scores_and_root_cause():
    result = SimpleNamespace(chunk_id="wrong", doc_id="doc", page=1, rank=1,
                             confidence_score=0.7, retriever_ranks={"bm25": 2, "dense": 1})
    rows = [{"qid": "q1", "question": "natural question", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "gold"}]}]
    traces = [{"query_id": "q1", "route": "hybrid_rrf"}]
    cases = failure_cases(rows, {"q1": [result]}, traces, 0.6,
                          family="human_natural", split="human_natural")
    assert cases[0]["root_cause_category"] == "missing_evidence"
    assert cases[0]["ranks"][0] == {"chunk_id": "wrong", "bm25_rank": 2,
                                    "dense_rank": 1, "fusion_rank": 1, "acceptance_score": 0.7}
    assert cases[0]["threshold"] == 0.6
