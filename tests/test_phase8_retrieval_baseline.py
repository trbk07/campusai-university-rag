from __future__ import annotations

import pytest

from evaluation.phase8.run_retrieval_baseline import (
    bind_custom_candidate, grouped_ci, select_rows, split_metrics,
)


def test_r18_selection_is_frozen_balanced_and_discloses_exposure():
    rows, bindings = select_rows()
    selection = bindings["selection"]

    assert len(rows) == 280
    assert selection["split_counts"] == {"holdout": 140, "test": 140}
    assert selection["selected_ids_sha256"] == "d8534b944ff2c3ee2dad93c93d682e9b18797d9a0d96d05e6e6627543435b77c"
    assert selection["connected_groups"] == 87
    assert selection["prior_phase7_exposure"] is True
    assert selection["fresh_validation"] is False
    assert selection["source_review_mode"] == "owner_self_review"


def test_group_bootstrap_is_deterministic_and_fails_closed_for_one_group():
    values = {"a": 1.0, "b": 0.5, "c": 0.0, "d": 1.0}
    groups = {"a": "g1", "b": "g1", "c": "g2", "d": "g2"}

    first = grouped_ci(values, groups, iterations=1000, seed=7)
    second = grouped_ci(values, groups, iterations=1000, seed=7)
    assert first == second
    assert first["status"] == "measured"
    assert first["groups"] == 2
    assert len(first["ci95"]) == 2

    one_group = grouped_ci(values, {key: "only" for key in values})
    assert one_group["status"] == "not_estimable"
    assert one_group["ci95"] is None


def test_split_metrics_keep_test_and_holdout_denominators_separate():
    rows = [
        {"qid": "t1", "split": "test", "answerable": True},
        {"qid": "t2", "split": "test", "answerable": False},
        {"qid": "h1", "split": "holdout", "answerable": True},
    ]
    per_query = {
        "t1": {"recall": {"1": 1.0, "3": 1.0, "5": 1.0, "10": 1.0}, "mrr": 1.0},
        "t2": {"recall": {"1": 0.0, "3": 0.0, "5": 0.0, "10": 0.0}, "mrr": 0.0},
        "h1": {"recall": {"1": 0.0, "3": 1.0, "5": 1.0, "10": 1.0}, "mrr": 0.5},
    }
    report = split_metrics(rows, {"t1": [object()], "t2": [], "h1": [object()]},
                          per_query, {"t1": "gt", "t2": "nt", "h1": "gh"})

    assert report["test"]["records"] == 2
    assert report["test"]["recall_at_k"]["5"]["denominator"] == 2
    assert report["test"]["answerable_recall_at_k"]["5"]["denominator"] == 1
    assert report["test"]["unanswerable_false_positive_rate"]["numerator"] == 0
    assert report["test"]["unanswerable_false_positive_rate"]["denominator"] == 1
    assert report["holdout"]["records"] == 1
    assert report["holdout"]["answerable_mrr"]["denominator"] == 1


def test_custom_candidate_binding_checks_bounds_and_connected_split_leakage():
    rows = [{
        "qid": f"q{i:03d}", "question": f"Question about fact number {i} from source {i}.",
        "split": "test" if i < 50 else "holdout", "source_group": f"source-{i}",
        "paraphrase_group": f"question-{i}", "tags": ["fact"],
    } for i in range(100)]
    binding = bind_custom_candidate(rows)
    assert binding["selection"]["split_counts"] == {"holdout": 50, "test": 50}
    assert binding["selection"]["connected_groups"] == 100
    assert binding["review"]["status"] == "pending"
    assert binding["selection"]["fresh_validation"] is False

    rows[-1]["source_group"] = rows[0]["source_group"]
    with pytest.raises(ValueError, match="connected-group split leakage"):
        bind_custom_candidate(rows)
