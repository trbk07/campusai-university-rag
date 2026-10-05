from copy import deepcopy
import json

import pytest

from evaluation.benchmarks.difficulty_audit import audit_dev_difficulty, apply_dev_difficulty, revision_errors
from scripts.benchmarks.build_hybrid_benchmark import category_difficulty


def fixtures():
    table = {"headers": ["Mã học phần", "Tên học phần", "Số tín chỉ"],
             "rows": [["ABC123", "Giải tích cơ bản", "3"]]}
    content = "Table headers: source\n\n" + json.dumps(table, ensure_ascii=False)
    evidence = {("doc", "chunk"): {"doc_id": "doc", "chunk_id": "chunk", "page": 1, "content": content}}
    row = {"qid": "q1", "split": "dev", "source_record_id": "phase6-test-003", "difficulty": "hard",
           "answerable": True, "question": "môn ABC123 trong chương trình là môn gì và có bao nhiêu tín chỉ vậy?",
           "doc_ids": ["doc"], "gold_evidence": [{"doc_id": "doc", "chunk_id": "chunk", "page": 1}],
           "tags": ["exact_code", "hard", "natural"], "context": [], "selected_text": None}
    sources = {"phase6-test-003": {"qid": "phase6-test-003", "difficulty": "hard", "gold_evidence": row["gold_evidence"]}}
    return [row], sources, evidence


def test_source_checked_correction_changes_only_dev_difficulty_and_tags():
    rows, sources, evidence = fixtures()
    before = deepcopy(rows)
    audit = audit_dev_difficulty(rows, sources, evidence)
    assert len(audit["changes"]) == 1
    corrected = apply_dev_difficulty(rows, audit)
    assert rows == before
    assert corrected[0]["difficulty"] == "easy"
    assert corrected[0]["tags"] == ["easy", "exact_code", "natural"]
    assert {key for key in rows[0] if rows[0][key] != corrected[0][key]} == {"difficulty", "tags"}


@pytest.mark.parametrize("mutation", ["heldout", "conditional", "wrong_source_label", "different_gold", "ambiguity", "missing_code"])
def test_correction_requires_all_origin_and_source_conditions(mutation):
    rows, sources, evidence = fixtures()
    if mutation == "heldout":
        rows[0]["split"] = "test"
        with pytest.raises(ValueError, match="dev"):
            audit_dev_difficulty(rows, sources, evidence)
        return
    if mutation == "conditional": rows[0]["question"] += " nếu được thì cộng với ABC124"
    if mutation == "wrong_source_label": sources["phase6-test-003"]["difficulty"] = "easy"
    if mutation == "different_gold": sources["phase6-test-003"]["gold_evidence"] = []
    if mutation == "missing_code": evidence[("doc", "chunk")]["content"] = "source without that course code"
    if mutation == "ambiguity":
        evidence[("doc", "another")] = {**evidence[("doc", "chunk")], "chunk_id": "another",
            "content": evidence[("doc", "chunk")]["content"].replace('"3"', '"4"')}
    assert audit_dev_difficulty(rows, sources, evidence)["changes"] == []


def test_correction_rejects_tampered_input_after_audit():
    rows, sources, evidence = fixtures()
    audit = audit_dev_difficulty(rows, sources, evidence)
    rows[0]["question"] += " changed"
    with pytest.raises(ValueError, match="changed"):
        apply_dev_difficulty(rows, audit)


def test_generated_difficulty_depends_on_operation():
    assert category_difficulty("exact_code") == category_difficulty("fact") == "easy"
    assert category_difficulty("table_filter_calculation") == "medium"
    assert category_difficulty("multi_document") == category_difficulty("comparison_year") == "hard"
    with pytest.raises(ValueError): category_difficulty("arbitrary")


def test_revision_replay_does_not_allow_gold_scope_or_authorship_changes():
    rows, sources, evidence = fixtures()
    audit = audit_dev_difficulty(rows, sources, evidence)
    corrected = apply_dev_difficulty(rows, audit)
    confirmation = {"owner_identity": "owner", "dev_metadata_revision": {
        "schema_version": 1, "owner_identity": "owner", "index_sha256": "a" * 64,
        "approval_source": "project_owner_standing_chat_instruction",
        "approval_statement": "t duyệt hết nên bạn cứ nhập tên tác giải là t",
        "original_dev_records": rows, "source_regression_records": sources, "audit": audit}}
    assert revision_errors(confirmation, corrected, evidence, "a" * 64) == []
    corrupted = deepcopy(corrected)
    corrupted[0]["question"] += " modified"
    assert revision_errors(confirmation, corrupted, evidence, "a" * 64) == ["dev_metadata_revision_changed_unapproved_fields"]
    assert revision_errors(confirmation, corrected, evidence, "b" * 64) == ["dev_metadata_revision_authorization_or_index"]
    confirmation["dev_metadata_revision"]["audit"]["changes"][0]["to"] = "medium"
    assert revision_errors(confirmation, corrected, evidence, "a" * 64) == ["dev_metadata_revision_source_replay"]


def test_historical_split_metadata_is_preserved_when_parent_proves_effective_dev():
    rows, sources, evidence = fixtures()
    rows[0]["split"] = "holdout"
    with pytest.raises(ValueError): audit_dev_difficulty(rows, sources, evidence)
    audit = audit_dev_difficulty(rows, sources, evidence, allocated_dev_qids={"q1"})
    corrected = apply_dev_difficulty(rows, audit)
    assert corrected[0]["split"] == "holdout"  # historical source; canonical export remains dev
    assert corrected[0]["difficulty"] == "easy"


def test_revision_writer_matches_freeze_bytes_on_windows(tmp_path):
    from scripts.benchmarks.revise_dev_difficulty import write_rows
    rows, _, _ = fixtures()
    path = tmp_path / "rows.jsonl"
    write_rows(path, rows)
    expected = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in rows).encode("utf-8")
    assert path.read_bytes() == expected
