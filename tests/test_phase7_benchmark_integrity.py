"""Evidence and author-byte integrity at the human benchmark intake boundary."""
from datetime import datetime, timezone
import json

import pytest

from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows
from evaluation.benchmarks.human_benchmark_intake import REVIEW_CHECKS, submit_question, submit_review
from evaluation.common.release_artifacts import sha256, write_json
from scripts.benchmarks import audit_phase7_inputs, prepare_human_candidates
from tests.test_reranker_stage_gates import human_rows


def frozen_index(root):
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "doc" / "bm25.json", {"items": [
        {"doc_id": "doc", "chunk_id": "c0", "page": 1, "content": "Original frozen source text"}]})
    write_json(root / "manifest.json", {"documents": ["doc"], "document_manifests": [
        {"document_id": "doc", "item_count": 1, "bm25_sha256": sha256(root / "doc" / "bm25.json")}]})
    return root


def test_review_rejects_changed_physical_evidence_under_unchanged_manifest(tmp_path):
    index = frozen_index(tmp_path / "index")
    record = {**human_rows()[0], "reviewer": "", "review_status": "pending"}
    intake = tmp_path / "intake"
    packet = submit_question(intake, record, index)
    manifest_before = (index / "manifest.json").read_bytes()
    write_json(index / "doc" / "bm25.json", {"items": [
        {"doc_id": "doc", "chunk_id": "c0", "page": 1, "content": "Changed after author submission"}]})
    review = {"qid": record["qid"], "reviewer": "reviewer", "reviewer_role": "independent_reviewer", "review_status": "approved",
              "review_checks": {key: True for key in REVIEW_CHECKS},
              "reviewed_at": datetime.now(timezone.utc).isoformat(),
              "record_sha256": packet["record_sha256"], "index_sha256": packet["index_sha256"]}
    with pytest.raises(ValueError, match="physical frozen evidence hash"):
        submit_review(intake, review, index)
    assert (index / "manifest.json").read_bytes() == manifest_before
    assert not (intake / "reviews").exists()


@pytest.mark.parametrize("mutation", ["duplicate_documents", "duplicate_bindings", "missing_binding",
                                       "wrong_count", "unsafe_doc_id", "invalid_page"])
def test_frozen_evidence_rejects_inconsistent_manifest_and_records(tmp_path, mutation):
    index = frozen_index(tmp_path / "index")
    manifest = json.loads((index / "manifest.json").read_text(encoding="utf-8"))
    if mutation == "duplicate_documents":
        manifest["documents"].append("doc")
    elif mutation == "duplicate_bindings":
        manifest["document_manifests"].append(dict(manifest["document_manifests"][0]))
    elif mutation == "missing_binding":
        manifest["document_manifests"] = []
    elif mutation == "wrong_count":
        manifest["document_manifests"][0]["item_count"] = 2
    elif mutation == "unsafe_doc_id":
        manifest["documents"] = ["..\\outside"]
    else:
        payload = {"items": [{"doc_id": "doc", "chunk_id": "c0", "page": True, "content": "source"}]}
        write_json(index / "doc" / "bm25.json", payload)
        manifest["document_manifests"][0]["bm25_sha256"] = sha256(index / "doc" / "bm25.json")
    write_json(index / "manifest.json", manifest)
    with pytest.raises(ValueError, match="frozen"):
        frozen_evidence(index)


def test_human_schema_reports_malformed_and_duplicate_gold_without_crashing():
    rows = human_rows()
    rows[0]["split"] = {"unexpected": "object"}
    rows[1]["gold_evidence"] = [{"doc_id": [], "chunk_id": "c0", "page": 1}]
    rows[2]["gold_evidence"].append(dict(rows[2]["gold_evidence"][0]))
    report = validate_rows(rows, {("doc", "c0"): {"page": 1}})
    assert report["status"] == "conditional"
    assert "row_1:invalid_split" in report["errors"]
    assert "row_2:evidence_provenance_mismatch" in report["errors"]
    assert "row_3:duplicate_gold_evidence" in report["errors"]


@pytest.mark.parametrize("name", ["human_candidate_staging.jsonl", "human_candidate_pool.summary.json",
                                 "human_candidate_lineage.json"])
def test_candidate_publication_cannot_alias_any_raw_input(tmp_path, name):
    index = frozen_index(tmp_path / "index")
    candidate = {**human_rows()[0], "candidate_id": "stable", "source_record_id": "original"}
    dataset = tmp_path / name
    original = (json.dumps(candidate, ensure_ascii=False) + "\n").encode("utf-8")
    dataset.write_bytes(original)
    with pytest.raises(ValueError, match="aliases raw input"):
        prepare_human_candidates.main(["--dataset", str(dataset), "--index-dir", str(index),
                                       "--output-dir", str(tmp_path)])
    assert dataset.read_bytes() == original
    for artifact in ("human_candidate_staging.jsonl", "human_candidate_pool.summary.json", "human_candidate_lineage.json"):
        if artifact != name:
            assert not (tmp_path / artifact).exists()


@pytest.mark.parametrize("duplicate_observation", [False, True])
def test_exposure_requires_bound_study_unique_ids_and_recorded_question(tmp_path, monkeypatch, duplicate_observation):
    index = frozen_index(tmp_path / "index")
    results, benchmark = tmp_path / "results", tmp_path / "data" / "benchmark"
    results.mkdir()
    benchmark.mkdir(parents=True)
    rows = [{"candidate_id": "a", "source_record_id": "old-a", "question": "Originally evaluated question"},
            {"candidate_id": "b", "source_record_id": "old-b", "question": "Different question reusing an old id"}]
    (benchmark / "human_candidate_pool.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    (benchmark / "student_natural_queries.jsonl").write_text("{}\n", encoding="utf-8")
    write_json(benchmark / "human_candidate_lineage.json", {"connected_groups": {
        "human-a": "family-a", "human-b": "family-b"}})
    observations = [{"qid": "old-a", "question": rows[0]["question"]},
                    {"qid": "old-b", "question": "Earlier unrelated question"}]
    if duplicate_observation:
        observations.append(dict(observations[0]))
    study = tmp_path / ".release/reranker/studies/loop3-fixed-policy-natural-dev-v1/student_natural_queries-quality.json"
    write_json(study, {"observations": observations, "dataset_sha256": sha256(benchmark / "student_natural_queries.jsonl"),
                       "evaluation_split": "dev"})
    monkeypatch.setattr(audit_phase7_inputs, "ROOT", tmp_path)
    monkeypatch.setattr(audit_phase7_inputs, "validate", lambda args: {
        "status": "pass", "gates": {"M0": {"status": "PASS"}}, "index_sha256": sha256(index / "manifest.json")})
    monkeypatch.setattr(audit_phase7_inputs, "source_identity", lambda root: {})
    monkeypatch.setattr(audit_phase7_inputs.subprocess, "check_output", lambda *args, **kwargs: "plan.md\n")
    _, registry = audit_phase7_inputs.audit(index, results, benchmark)
    expected = "unknown_pending_history_audit" if duplicate_observation else "known_exposed_dev"
    assert registry["records"][0]["status"] == expected
    assert registry["records"][1]["status"] == "unknown_pending_history_audit"
    assert all(row["heldout_eligible"] is False and row["authorship_inferred"] is False for row in registry["records"])
