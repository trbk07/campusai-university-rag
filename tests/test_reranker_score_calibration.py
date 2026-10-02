from campusai.retrieval.hybrid import RetrievalResult
from evaluation.calibrate_reranker_scores import calibrate
from evaluation.calibrate_reranker_scores import calibrated_outputs, _quality
import pytest


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


def test_low_score_abstention_can_remove_negative_evidence_without_changing_rank_ambiguity():
    rows = [{"qid": "p", "answerable": True, "gold_evidence": [{"doc_id":"doc", "chunk_id":"gold"}]},
            {"qid": "n", "answerable": False, "gold_evidence": []}]
    baseline = {"p": [_result("gold")], "n": [_result("decoy")]}
    proposals = {"p": {"results": baseline['p'], "top_score": 2.0, "margin": 0.0},
                 "n": {"results": baseline['n'], "top_score": -2.0, "margin": 3.0}}
    _, legacy = calibrate(rows, baseline, proposals)
    assert not legacy['feasible'] and legacy['selected']['negative_fpr'] == 1.0
    policy, result = calibrate(rows, baseline, proposals, 'abstain')
    assert result['feasible'] and result['selected']['answerable_recall_at_5'] == 1.0
    assert result['selected']['negative_fpr'] == 0.0
    outputs = calibrated_outputs(baseline, proposals, policy)
    assert outputs['p'] == baseline['p'] and outputs['n'] == []
    assert _quality(rows, outputs) == result['selected']


def test_infeasible_abstention_fit_reports_the_outputs_of_its_actual_fallback_policy():
    rows = [{"qid": "p", "answerable": True, "gold_evidence": [{"doc_id":"doc", "chunk_id":"gold"}]},
            {"qid": "n", "answerable": False, "gold_evidence": []}]
    baseline = {'p': [_result('gold')], 'n': [_result('decoy')]}
    proposals = {qid: {'results': output, 'top_score': 1.0, 'margin': 0.0} for qid,output in baseline.items()}
    policy,result = calibrate(rows, baseline, proposals, 'abstain')
    assert not result['feasible']
    assert _quality(rows, calibrated_outputs(baseline,proposals,policy)) == result['selected']
    with pytest.raises(ValueError, match='dev'):
        calibrate([{**row,'split':'holdout'} for row in rows],baseline,proposals)
    with pytest.raises(ValueError, match='decision'):
        calibrate(rows,baseline,{**proposals, 'n': {**proposals['n'],'top_score':float('nan')}})
