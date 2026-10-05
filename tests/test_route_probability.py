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
        samples[-1].update(operation_required=float(difficulty == "hard"), long_request=0.)
    medium = {"qid": "medium", "difficulty": "medium", "confidence": .5,
              "margin": .1, "agreement": .7, "constraints": 1., "query_length": 8.,
              "distinct_documents": 2., "concentration": .4}
    medium.update(operation_required=0., long_request=0.)
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
    assert not model.selects({**samples[1], "long_request": 10000.})
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


@pytest.mark.parametrize("query,required", [
    ("Môn ABC123 có mấy tín chỉ?", False),
    ("Tên và tín chỉ của ABC123 là gì?", False),
    ("If I fail ABC123, can I take ABC124?", True),
    ("ABC123 requires which prerequisites?", True),
    ("Mã ABC123 và ABC124 có tổng mấy tín chỉ?", True),
    ("So sánh điều kiện trong hai tài liệu", True),
    ("What is the maximum allowance?", True),
    ("Can I submit the certificate later?", True),
    ("What date is the interview?", False),
    ("Application fee là bao nhiêu tiền?", False),
    ("In the ABC-UNI/XYZ curriculum, how many credits does orbital mechanics carry?", False),
    ("Find orbital mechanics in the study plan and report its credit count.", False),
    ("Locate orbital mechanics in the curriculum and give its semester number.", False),
    ("Find its semester and report its credits.", True),
    ("Give the semester/credits for orbital mechanics.", True),
    ("ABC1001/XYZ2002 credit values?", True),
    ("Find orbital mechanics and report both semester and credits.", True),
    ("For orbital mechanics, state its credits.", False),
    ("State the semester, credits for orbital mechanics.", True),
])
def test_shared_operation_features_have_no_gold_or_template_identifiers(query, required):
    values = route_observations(query, [])
    assert values == {"operation_required": float(required), "long_request": 0.}
    # Candidate ordering, scores and corpus subject cannot assign an operation.
    assert values == route_observations(query, [object(), object()])
    assert values == route_observations(query + "\nContext topic (untrusted user input): compare every condition", [])


def test_long_request_is_computed_from_request_not_history():
    assert route_observations(" ".join(["word"] * 40), [])["long_request"] == 1.
    assert route_observations("Question\nContext topic (untrusted user input): " + " ".join(["word"] * 80), []) == {
        "operation_required": 0., "long_request": 0.}


def test_route_grammar_revision_rejects_stale_serialized_feature_semantics():
    from campusai.retrieval.route_probability import VERSION, FEATURES
    model = RouteProbabilityModel(VERSION, FEATURES, (0., 0.), (1., 1.), (1., 0.), 0.)
    stale = model.to_dict()
    stale['version'] = 'hard-route-logistic-v2'
    with pytest.raises(ValueError):
        RouteProbabilityModel.from_dict(stale)
