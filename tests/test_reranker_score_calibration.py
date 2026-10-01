from campusai.retrieval.hybrid import RetrievalResult
from evaluation.calibrate_reranker_scores import calibrate


def _result(name):
    return RetrievalResult(name, "doc", 1, name, "text", .4,
                           "hybrid_rrf", {"page_range": [1, 1]})


def test_phase7_score_calibration_uses_dev_proposals_and_preserves_negative_fpr():
    rows = [{"qid": "positive", "answerable": True,
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "gold"}]},
            {"qid": "negative", "answerable": False, "gold_evidence": []}]
    baseline = {"positive": [_result("decoy"), _result("gold")], "negative": []}
    proposals = {"positive": {"results": [baseline["positive"][1], baseline["positive"][0]],
                              "top_score": 2.0, "margin": .5}}
    selected, comparison = calibrate(rows, baseline, proposals)
    assert comparison["feasible"]
    assert comparison["selected"]["mrr"] > comparison["baseline"]["mrr"]
    assert comparison["selected"]["negative_fpr"] == 0.0
    assert selected["threshold"] <= 2.0
