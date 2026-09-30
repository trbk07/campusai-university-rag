import json

import pytest

from evaluation.phase6_human_schema import load_human_challenge


def _rows():
    rows = []
    for index in range(100):
        answerable = index < 90
        rows.append({
            "qid": f"human-{index:03d}", "split": "human_natural",
            "question": f"Natural question {index}?", "answerable": answerable,
            "gold_evidence": [{"doc_id": "doc", "chunk_id": "chunk"}] if answerable else [],
            "language": ("vi", "en", "vi-en")[index % 3], "difficulty": "hard" if index % 3 == 0 else "medium",
            "category": "prerequisite", "expected_route": "hybrid_rrf",
            "challenge_tags": ["negative"] if not answerable else [
                ["prerequisite", "typo_no_accent", "table", "multi_document",
                 "ambiguous", "short_meaningful", "exact_code", "code_switch",
                 "ocr_degraded"][index % 9]],
            "author_type": "human", "author": "reviewer-a", "reviewer": "reviewer-b",
            "annotation_status": "reviewed", "source_annotation": "Checked against document page 1",
        })
    return rows


def test_reviewed_human_challenge_accepts_valid_evidence(tmp_path):
    path = tmp_path / "human.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in _rows()), encoding="utf-8")
    assert len(load_human_challenge(path, {("doc", "chunk")})) == 100


def test_human_challenge_rejects_claimed_ai_authorship(tmp_path):
    rows = _rows()
    rows[0]["author_type"] = "generated"
    path = tmp_path / "human.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="human authorship"):
        load_human_challenge(path, {("doc", "chunk")})
