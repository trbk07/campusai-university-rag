from evaluation.calibrate_hard_query_route import fit_route, route_metrics


def test_phase7_route_fit_uses_only_supplied_dev_features():
    samples = ([{"qid": f"h{index}", "difficulty": "hard", "confidence": .4,
                 "margin": .01} for index in range(20)]
               + [{"qid": f"e{index}", "difficulty": "easy", "confidence": .9,
                   "margin": .2} for index in range(20)])
    confidence, margin, metrics, feasible = fit_route(samples)
    assert feasible
    assert metrics["hard_recall"] == 1.0
    assert metrics["easy_unnecessary_rerank_rate"] == 0.0
    assert route_metrics(samples, confidence, margin) == metrics


def test_phase7_route_fit_reports_unachievable_gate():
    samples = [{"qid": "h", "difficulty": "hard", "confidence": .5, "margin": .1},
               {"qid": "e", "difficulty": "easy", "confidence": .5, "margin": .1}]
    _confidence, _margin, _metrics, feasible = fit_route(samples)
    assert not feasible
