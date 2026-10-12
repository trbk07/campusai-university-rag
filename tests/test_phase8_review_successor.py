import copy

import pytest

from evaluation.phase8.repair_reviewed_benchmark import (
    OUT, FREEZE, REPAIRS, create, load, repaired_rows, rows_at, verify_freeze,
)


def test_repair_changes_only_two_question_fields_and_keeps_historical_rejections():
    before = rows_at("evaluation/phase8/benchmark_candidate_v4.jsonl")
    after = rows_at(OUT)
    assert after == repaired_rows(before)
    changes = {a["qid"]: {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
               for a, b in zip(after, before, strict=True) if a != b}
    assert changes == {qid: {"question"} for qid in REPAIRS}
    old = load("evaluation/results/phase8-automated-review-v4.json")
    assert {d["qid"] for d in old["decisions"] if d["decision"] == "Reject"} == set(REPAIRS)


def test_successor_freeze_checks_all_bindings_and_does_not_claim_product_pass():
    result = verify_freeze()
    assert result["accepted_provenance_pass"] == result["accept"] == result["reviewed"] == 30
    assert result["freeze_status"] == "FROZEN_FOR_REGRESSION_EVALUATION"
    assert result["provider_calls"] == 0


@pytest.mark.parametrize("field,value,match", [
    ("phase8_pass", True, "must not promote"),
    ("human_signature_added", True, "must not promote"),
    ("rows", 298, "population mismatch"),
    ("cross_split_groups", 1, "group leakage"),
])
def test_freeze_rejects_false_approval_or_population(field, value, match):
    manifest = copy.deepcopy(load(FREEZE))
    manifest[field] = value
    with pytest.raises(ValueError, match=match):
        verify_freeze(manifest)


def test_successor_generation_cannot_overwrite_reviewed_artifacts():
    with pytest.raises(ValueError, match="refusing to overwrite"):
        create()
