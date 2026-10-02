import pytest

from campusai.retrieval.evidence_policy import EvidenceProbabilityModel, evidence_features
from campusai.retrieval.hybrid import RetrievalResult
from evaluation.calibrate_evidence_probabilities import calibrate_probabilities, proposal_features
from evaluation.calibrate_reranker_scores import calibrated_outputs
from evaluation.evaluate_candidate_coverage import audit_outputs, coverage_errors


def result(name, *, score=.8):
    return RetrievalResult(name, "doc", 1, "evidence " + name, "text", score,
                           "hybrid_rrf", {"page_range": [1, 1]}, rank=1)


def test_grouped_probability_replays_observable_features_and_keeps_uncertain_phase6():
    rows, baseline, proposals = [], {}, {}
    for i in range(90):
        qid = f"q{i}"
        label = i % 3
        rows.append({"qid": qid, "split": "dev", "question": f"Find evidence for item {i}",
                     "paraphrase_group": f"group-{i}", "answerable": label != 0,
                     "gold_evidence": [{"doc_id": "doc", "chunk_id": "gold", "page": 1}] if label else []})
        gold, decoy = result("gold"), result("decoy")
        baseline[qid] = ([result(f"decoy-{j}") for j in range(5)] + [gold]
                         if label == 2 else [gold] if label else [decoy])
        ranked = [gold, decoy] if label == 2 else [decoy, gold]
        scores = [5., 0.] if label == 2 else ([-5., -6.] if label == 0 else [0., -.5])
        proposals[qid] = {"results": ranked[:1], "top_score": scores[0],
                          "margin": scores[0] - scores[1],
                          "evidence_inputs": {"ranked_candidates": [item.to_dict() for item in ranked],
                                              "scores": scores}}
    policy, diagnostics = calibrate_probabilities(rows, baseline, proposals)
    model = EvidenceProbabilityModel.from_dict(policy["evidence_model"])
    assert diagnostics["feasible"] is True
    assert diagnostics["out_of_fold"]["records"] == 90
    assert diagnostics["selected"]["negative_fpr"] == 0
    assert calibrated_outputs(baseline, proposals, policy, rows=rows)["q0"] == []
    assert model.action(proposal_features(rows[2], baseline["q2"], proposals["q2"])) == "rerank"
    too_far = evidence_features("query", [result("gold")], [result("gold")], [5.])
    too_far["query_length"] = 10000
    assert model.action(too_far) == "phase6"
    with pytest.raises(ValueError, match="dev"):
        calibrate_probabilities([{**row, "split": "holdout"} for row in rows], baseline, proposals)
    with pytest.raises(ValueError, match="requires raw"):
        calibrated_outputs(baseline, proposals, policy)


def test_candidate_strata_expose_missing_second_hop():
    base = result("gold").to_dict()
    rows = [{"qid": "multi", "question": "compare 2022 semesters 1 and 2", "answerable": True,
             "difficulty": "hard", "category": "curriculum", "tags": ["table", "multi_hop"],
             "gold_evidence": [{"doc_id": "doc", "chunk_id": "gold", "page": 1},
                               {"doc_id": "doc", "chunk_id": "other", "page": 1}]},
            {"qid": "negative", "question": "absent", "answerable": False,
             "gold_evidence": [], "tags": []}]
    report = audit_outputs(rows, {"multi": [base], "negative": [base]}, ["doc"], 40)
    assert report["candidate_recall"] == 1
    assert report["all_gold_recall"] == 0
    assert report["strata"]["cohort:multi_hop"]["evidence_recall"] == .5
    assert report["strata"]["cohort:year"]["all_gold_recall"] == 0
    assert report["negative_candidate_rate"] == 1
    assert coverage_errors(report, .95)
