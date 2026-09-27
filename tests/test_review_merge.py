import pytest

from scripts.merge_review import merge


def _row(identifier="r1", **overrides):
    row = {
        "id": identifier, "split": "dev", "source_group": "doc-a",
        "template_group": "template-a", "semantic_topic": "topic-a",
        "adversarial_pattern": "none", "review_status": "draft",
        "annotator_id": "auto-draft", "answerable": True,
        "expected_status": "found", "gold_claims": [],
        "gold_abstention_reason": None,
    }
    row.update(overrides)
    return row


def _write(path, rows):
    import json
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_review_merge_preserves_frozen_provenance(tmp_path):
    draft, review = tmp_path / "draft.jsonl", tmp_path / "review.jsonl"
    _write(draft, [_row()])
    _write(review, [_row(review_status="reviewed", annotator_id="reviewer-1",
                         gold_claims=[{"text": "fact", "evidence": [{"doc_id": "doc-a", "page": 1, "quote": "fact"}]}])])
    rows = merge(draft, review)
    assert rows[0]["review_status"] == "reviewed"
    assert rows[0]["annotator_id"] == "reviewer-1"


def test_review_merge_rejects_split_changes(tmp_path):
    draft, review = tmp_path / "draft.jsonl", tmp_path / "review.jsonl"
    _write(draft, [_row()])
    _write(review, [_row(split="holdout", review_status="reviewed", annotator_id="reviewer-1")])
    with pytest.raises(ValueError, match="frozen field split"):
        merge(draft, review)
