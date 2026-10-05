"""Review preparation must preserve questions and never invent approval."""
from copy import deepcopy
import hashlib
import json

import pytest

from evaluation.common.release_artifacts import sha256, write_json
from evaluation.benchmarks.freeze_human_benchmark import validate_rows
from scripts.phase7_create_intake_lineage import main as legacy_lineage_main
from scripts.phase7_release_pipeline import main as legacy_release_main
from scripts.benchmarks.prepare_phase7_review import build_draft, publish
from tests.test_reranker_stage_gates import human_rows


def review_inputs(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    pdf = corpus / "source.pdf"
    pdf.write_bytes(b"%PDF-review-fixture")
    doc_id = hashlib.sha256(pdf.read_bytes()).hexdigest()
    corpus_manifest = corpus / "manifest.json"
    write_json(corpus_manifest, {"documents": [{"filename": "source.pdf", "sha256": doc_id, "page_count": 1, "academic_year": "2022"}]})
    index = tmp_path / "index"
    (index / doc_id).mkdir(parents=True)
    item = {"doc_id": doc_id, "chunk_id": "chunk1", "page": 1, "content": "Credits: 3", "metadata": {}}
    write_json(index / doc_id / "bm25.json", {"items": [item]})
    write_json(index / "manifest.json", {"documents": [doc_id], "document_manifests": [{"document_id": doc_id, "bm25_sha256": sha256(index / doc_id / "bm25.json"), "item_count": 1}]})
    dataset, staging = tmp_path / "pool.jsonl", tmp_path / "staging.jsonl"
    raw = [{"candidate_id": "candidate-1", "question": "MATH101 có mấy tín?", "author": "member-one"},
           {"candidate_id": "candidate-2", "question": "bao nhiêu tín thì được", "author": "member-two"}]
    rows = [{**row, "qid": "human-" + row["candidate_id"], "answerable": n == 0, "doc_ids": [doc_id] if n == 0 else [],
             "filters": {}, "gold_evidence": [{"doc_id": doc_id, "chunk_id": "chunk1", "page": 1}] if n == 0 else [],
             "difficulty": "hard", "expected_behavior": "answer_grounded" if n == 0 else "ask_clarification"} for n, row in enumerate(raw)]
    dataset.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in raw), encoding="utf-8")
    staging.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    lineage, exposure = tmp_path / "lineage.json", tmp_path / "exposure.json"
    groups = {row["qid"]: "family-" + row["candidate_id"] for row in rows}
    write_json(lineage, {"dataset_sha256": sha256(dataset), "index_sha256": sha256(index / "manifest.json"), "connected_groups": groups})
    write_json(exposure, {"dataset_sha256": sha256(dataset), "lineage_sha256": sha256(lineage), "records": [
        {"qid": row["qid"], "status": "unknown_pending_history_audit", "connected_group": groups[row["qid"]], "group_known_exposed": False}
        for row in rows]})
    return dataset, staging, lineage, exposure, index, corpus_manifest


def test_draft_binds_evidence_but_preserves_empty_scope_pending_decisions_and_bytes(tmp_path):
    inputs = review_inputs(tmp_path)
    before = [path.read_bytes() for path in inputs[:4]]
    draft = build_draft(*inputs)
    assert [path.read_bytes() for path in inputs[:4]] == before
    assert draft["release_eligible"] is False and draft["split_assignment"] is None
    negative = draft["records"][1]
    assert negative["record"]["doc_ids"] == []
    assert negative["scope_proposal"]["doc_ids"] == [draft["documents"][0]["doc_id"]]
    assert all(value is None for value in negative["decision"]["review_checks"].values())
    assert negative["decision"]["status"] == "pending" and negative["decision"]["reviewer_id"] == ""
    assert draft["evidence_catalog"][draft["records"][0]["gold_evidence_keys"][0]]["content"] == "Credits: 3"
    manifest = publish(draft, tmp_path / "out", tmp_path / "docs")
    assert (tmp_path / "docs" / "phase7_review_questions.draft.md").read_bytes().endswith(b"\n")
    assert not (tmp_path / "docs" / "phase7_review_questions.draft.md").read_bytes().endswith(b"\n\n")
    assert publish(draft, tmp_path / "out", tmp_path / "docs", verify=True) == manifest
    with pytest.raises(ValueError, match="already exists"):
        publish(draft, tmp_path / "out", tmp_path / "docs")
    changed = deepcopy(draft)
    changed["records"][0]["decision"]["status"] = "approved"
    with pytest.raises(ValueError, match="changed"):
        publish(changed, tmp_path / "out", tmp_path / "docs", verify=True)


@pytest.mark.parametrize("tamper", ["pdf", "bm25", "staging_question", "exposure_group", "qid_coverage"])
def test_draft_rejects_changed_source_evidence_or_lineage(tmp_path, tamper):
    dataset, staging, lineage, exposure, index, corpus_manifest = review_inputs(tmp_path)
    if tamper == "pdf":
        (corpus_manifest.parent / "source.pdf").write_bytes(b"different source")
    elif tamper == "bm25":
        doc = json.loads((index / "manifest.json").read_text())["documents"][0]
        (index / doc / "bm25.json").write_text('{}', encoding="utf-8")
    elif tamper == "staging_question":
        staging.write_text(staging.read_text(encoding="utf-8").replace("MATH101", "MATH999"), encoding="utf-8")
    else:
        content = json.loads(exposure.read_text(encoding="utf-8"))
        if tamper == "exposure_group":
            content["records"][0]["connected_group"] = "different-family"
        else:
            content["records"].pop()
        write_json(exposure, content)
    with pytest.raises(ValueError):
        build_draft(dataset, staging, lineage, exposure, index, corpus_manifest)


def test_legacy_lineage_generator_refuses_to_synthesize_review_or_exposure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as error:
        legacy_lineage_main([])
    assert error.value.code == 2
    assert not (tmp_path / "data").exists()


def test_legacy_release_pipeline_refuses_to_synthesize_approvals_scopes_or_splits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as error:
        legacy_release_main([])
    assert error.value.code == 2
    assert not list(tmp_path.rglob("*"))


@pytest.mark.parametrize("answerable,behavior,error", [
    (True, "abstain", "answerable_requires_answer_grounded"),
    (False, "answer_grounded", "unanswerable_requires_abstain_or_clarification"),
    (False, "phase6_fallback", "phase6_fallback_only_for_provider_failure"),
    (False, "abstain_no_evidence", "invalid_expected_behavior"),
])
def test_expected_behavior_enum_is_shared_and_answerability_bound(answerable, behavior, error):
    rows = human_rows()
    rows[0]["answerable"] = answerable
    rows[0]["expected_behavior"] = behavior
    report = validate_rows(rows, {("doc", "c0"): {"page": 1}})
    assert "row_1:" + error in report["errors"]
