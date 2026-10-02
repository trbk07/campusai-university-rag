"""Preserve upload scope, natural input and honest benchmark annotations."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import pytest
from evaluation.build_student_natural_benchmark import CATEGORIES, parse_spec, query_input, validate_rows
from evaluation.release_artifacts import sha256

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/benchmark/student_natural_queries.jsonl"


def dataset():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]


def test_dataset_retains_all_forms_and_manifest_integrity():
    rows = dataset()
    manifest = json.loads(DATASET.with_suffix(".manifest.json").read_text(encoding="utf-8"))
    assert validate_rows(rows) == []
    assert len(rows) == manifest["records"] == 480
    assert sha256(DATASET) == manifest["dataset_sha256"]
    assert sha256(DATASET.with_suffix(".spec")) == manifest["spec_sha256"]
    assert b"\r\n" not in DATASET.read_bytes()
    assert set(manifest["categories"]) == CATEGORIES
    assert dict(Counter(row["category"] for row in rows)) == manifest["categories"]
    assert all(row["author_type"] == "ai" and row["release_eligible"] is False for row in rows)


def test_intents_and_supporting_uploads_do_not_cross_splits():
    groups, sources = defaultdict(list), defaultdict(set)
    for row in dataset():
        groups[row["intent"]].append(row)
        for item in row["gold_evidence"]:
            sources[item["doc_id"]].add(row["split"])
    assert len(groups) == 80
    assert all(len(group) == 6 and len({row["query"] for row in group}) == 6
               and len({row["split"] for row in group}) == 1 for group in groups.values())
    assert all(len(splits) == 1 for splits in sources.values())


def test_rag_input_uses_raw_query_and_dynamic_uploaded_ids():
    row = next(row for row in dataset() if row["category"] == "abbreviation" and row["answerable"])
    reference = row["document_context"]["uploaded_documents"][0]["document_ref"]
    request = query_input(row, {reference: ["new-user-pdf-not-in-seed-corpus"]})
    assert request["query"] == row["query"] != row["normalized_query"]
    assert request["doc_ids"] == ["new-user-pdf-not-in-seed-corpus"]
    assert not {"normalized_query", "expected_answer", "gold_evidence", "intent", "expected_source"} & request.keys()
    with pytest.raises(ValueError, match="explicit uploaded"):
        query_input(row, {})


def test_followup_and_user_selection_are_explicit_inputs():
    rows = dataset()
    for row in rows:
        if row["category"] == "contextual_followup":
            assert row["context"] and row["context"][0]["role"] == "user" and not row["ambiguous"]
    selected = next(row for row in rows if row["intent"] == "selected_section_plain_language")
    reference = selected["document_context"]["uploaded_documents"][0]["document_ref"]
    assert query_input(selected, {reference: ["uploaded-by-user"]})["selected_text"]
    ambiguous = next(row for row in rows if row["intent"] == "uploaded_document_contextless_reference")
    assert ambiguous["expected_behavior"] == "ask_clarification"
    assert not ambiguous["answerable"] and not ambiguous["context"]


def test_absent_policy_is_not_confused_with_reward_rule():
    rows = dataset()
    scholarship = [row for row in rows if row["intent"] == "scholarship_gpa_requirement"]
    award = [row for row in rows if row["intent"] == "excellent_student_no_low_grade"]
    assert all(not row["answerable"] and row["expected_source"] is None for row in scholarship)
    assert all(row["answerable"] and row["expected_source"] for row in award)
    conditional = next(row for row in rows if row["query"] == "nếu GPA 2.1 mà có 1 môn F thì đăng kí 20 tín được không")
    assert "20" in conditional["normalized_query"] and "2,1" in conditional["normalized_query"]


def test_followup_without_history_is_rejected(tmp_path):
    from evaluation.build_student_natural_benchmark import compile_dataset
    lines = "@missing|none||hard|Clarify?|Missing context.\n" + "\n".join(
        f"contextual_followup|then what {i}?" for i in range(6))
    assert len(parse_spec(lines)) == 1
    (tmp_path / "manifest.json").write_text('{"documents": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="prior user turn"):
        compile_dataset(lines, {"documents": []}, tmp_path)
