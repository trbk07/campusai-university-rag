import pytest

from campusai.retrieval.route_probability import RouteProbabilityModel, route_observations
from campusai.retrieval.hybrid import RetrievalResult
from campusai.retrieval.rerank_policy import Phase7Policy
from campusai.retrieval.routing import RoutingTrace
from evaluation.reranker.calibrate_hard_query_route import route_metrics
from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities


def test_grouped_route_uses_only_observable_features_and_skips_ood():
    rows, samples = [], []
    for index in range(60):
        difficulty = "hard" if index % 2 else "easy"
        rows.append({"qid": f"q{index}", "split": "dev", "difficulty": difficulty,
                     "paraphrase_group": f"family-{index}"})
        samples.append({"qid": f"q{index}", "difficulty": difficulty,
                        "confidence": .1 if difficulty == "hard" else .9,
                        "margin": .01 if difficulty == "hard" else .2,
                        "agreement": .4 if difficulty == "hard" else 1.,
                        "constraints": 2. if difficulty == "hard" else 0.,
                        "query_length": 8., "distinct_documents": 2., "concentration": .4})
    medium = {"qid": "medium", "difficulty": "medium", "confidence": .5,
              "margin": .1, "agreement": .7, "constraints": 1., "query_length": 8.,
              "distinct_documents": 2., "concentration": .4}
    artifact, diagnostics, feasible = fit_route_probabilities(
        samples + [medium], rows + [{"qid": "medium", "split": "dev", "difficulty": "medium",
                                      "paraphrase_group": "medium-family"}])
    model = RouteProbabilityModel.from_dict(artifact)
    assert feasible
    assert diagnostics["out_of_fold_metrics"]["hard_recall"] >= .95
    assert len(diagnostics["observations"]) == 60
    assert diagnostics["out_of_fold_metrics"]["easy_unnecessary_rerank_rate"] <= .20
    assert route_metrics(samples, 1., 1., route_model=artifact)["hard_recall"] == 1
    assert model.selects(samples[1]) and not model.selects(samples[0])
    assert not model.selects({**samples[1], "query_length": 10000.})
    candidates = [RetrievalResult("a", "doc", 1, "source", "text", .8, "hybrid_rrf",
                                  {"page_range": [1, 1]}, fusion_score=.2,
                                  confidence_score=.1, retriever_ranks={"bm25": 1, "dense": 2}),
                  RetrievalResult("b", "doc", 1, "source", "text", .7, "hybrid_rrf",
                                  {"page_range": [1, 1]}, fusion_score=.1,
                                  confidence_score=.2, retriever_ranks={"bm25": 2})]
    query = "one two three four five six seven eight"
    policy = Phase7Policy("v1", *(["a" * 64] * 4), 0., 0., 1., 1., route_model=artifact)
    assert policy.route(query, candidates, RoutingTrace(route="hybrid_rrf"))[0] == model.selects(
        route_observations(query, candidates))
    with pytest.raises(ValueError, match="dev"):
        fit_route_probabilities(samples, [{**row, "split": "holdout"} for row in rows])
    with pytest.raises(ValueError, match="features"):
        model.selects({"difficulty": "hard"})
