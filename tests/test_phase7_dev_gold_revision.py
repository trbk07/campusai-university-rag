"""Dev corrections must not launder old approvals or promote consumed inputs."""
from copy import deepcopy
import hashlib

import pytest

from scripts.benchmarks.prepare_phase7_dev_gold_revision import revise_rows


@pytest.fixture
def inputs():
    old = {"qid": "human-candidate-0156", "split": "dev", "answerable": True,
           "question": "What is EMA2036E and how many credits?", "doc_ids": ["doc"],
           "gold_evidence": [{"doc_id": "doc", "chunk_id": "wrong", "page": 3}],
           "author": "original author", "paraphrase_group": "consumed-group", "release_eligible": True,
           "review_status": "approved", "reviewer": "old reviewer", "reviewed_at": "2026-10-03T00:00:00Z",
           "review_checks": {"evidence_sufficient": True}}
    evidence = {("doc", "wrong"): {"content": "EMA2036E\nEngineering Mechanics 2", "page": 3},
                ("doc", "right"): {"content": "EMA2036E | Engineering Mechanics 1 | 3", "page": 3}}
    fact = {"doc_id": "doc", "chunk_id": "right", "page": 3, "table_row": 14, "code": "EMA2036E",
            "name": "Engineering Mechanics 1", "name_lines": ["Engineering Mechanics 1"], "credits": 3,
            "source_content_sha256": hashlib.sha256(evidence["doc", "right"]["content"].encode()).hexdigest()}
    review = {"document": "doc", "decisions": [{"number": 156, "code": "EMA2036E", "page": 3,
               "table_row": 14, "credits": 3, "action": "replace_gold", "reason": "Wrong course name; credits absent."}]}
    return [old], review, evidence, [fact]


def test_corrected_gold_preserves_consumed_identity_and_clears_old_approval(inputs):
    original = deepcopy(inputs)
    rows, audit, claims = revise_rows(*inputs)
    assert inputs == original
    row = rows[0]
    assert row["gold_evidence"] == [{"doc_id": "doc", "chunk_id": "right", "page": 3}]
    for field in ("qid", "split", "question", "author", "paraphrase_group", "doc_ids"):
        assert row[field] == inputs[0][0][field]
    assert row["review_status"] == "pending" and not row["review_checks"] and not row["reviewer"]
    assert not row["release_eligible"]
    assert audit[0]["prior_review"]["reviewer"] == "old reviewer"
    assert claims[row["qid"]][1]["value"] == 3


@pytest.mark.parametrize("split", ["test", "holdout"])
def test_rejects_any_heldout_row(inputs, split):
    inputs[0][0]["split"] = split
    with pytest.raises(ValueError, match="dev rows only"):
        revise_rows(*inputs)


@pytest.mark.parametrize("field,value", [("credits", 30), ("table_row", 15), ("page", 4)])
def test_rejects_tampered_source_decision(inputs, field, value):
    inputs[1]["decisions"][0][field] = value
    with pytest.raises(ValueError, match="source row or credit"):
        revise_rows(*inputs)


def test_rejects_wrong_scope(inputs):
    inputs[0][0]["doc_ids"] = ["another-doc"]
    with pytest.raises(ValueError, match="scope"):
        revise_rows(*inputs)


def test_rejects_changed_source_content(inputs):
    inputs[2]["doc", "right"]["content"] += " changed"
    with pytest.raises(ValueError, match="source content hash"):
        revise_rows(*inputs)


def test_rejects_duplicate_review_or_rows(inputs):
    inputs[1]["decisions"] *= 2
    with pytest.raises(ValueError, match="review qids"):
        revise_rows(*inputs)
    inputs[0].append(deepcopy(inputs[0][0]))
    with pytest.raises(ValueError, match="duplicate dev qids"):
        revise_rows(*inputs)


def test_retained_gold_is_still_dev_only(inputs):
    inputs[1]["decisions"][0]["action"] = "retain_gold"
    rows, _, _ = revise_rows(*inputs)
    assert rows[0]["gold_evidence"] == inputs[0][0]["gold_evidence"]
    assert rows[0]["release_eligible"] is False
