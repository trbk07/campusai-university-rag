"""Owner review must flow through M1/S1; malformed inputs must not mutate freeze."""
from argparse import Namespace
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker import release_workflow
from evaluation.reranker.supplemental_gates import review_audit_errors
from scripts.benchmarks.check_phase7_review import inspect_inputs, main as inspect_main
from scripts.phase7_release_pipeline import main as pipeline_main
from tests.test_phase7_review_preparation import review_inputs
from tests.test_reranker_stage_gates import human_rows


def actual_audit(row, index, owner="Project Owner"):
    submitted = datetime.now(timezone.utc) - timedelta(minutes=2)
    question_record = {**row, "reviewer": "", "review_status": "pending",
                       "review_checks": {key: False for key in row["review_checks"]}}
    question_record.pop("reviewer_role", None)
    question_record.pop("reviewed_at", None)
    packet = {"record": question_record, "record_sha256": digest_record(question_record),
              "index_sha256": sha256(index / "manifest.json"), "submitted_at": submitted.isoformat()}
    review = {"qid": row["qid"], "reviewer": owner, "reviewer_role": "project_owner",
              "review_status": "approved", "review_checks": {key: True for key in row["review_checks"]},
              "record_sha256": packet["record_sha256"], "index_sha256": packet["index_sha256"],
              "reviewed_at": (submitted + timedelta(minutes=1)).isoformat()}
    final = {**question_record, **{key: review[key] for key in
                                  ("reviewer", "reviewer_role", "review_status", "review_checks", "reviewed_at")}}
    return final, {"qid": row["qid"], "question_packet": packet, "review_packet": review,
                   "exported_record_sha256": digest_record(final)}


def test_audit_accepts_actual_owner_packets_and_only_allows_split_changes(tmp_path):
    *_, index, _ = review_inputs(tmp_path)
    final, audit = actual_audit(human_rows()[0], index)
    assert review_audit_errors([final], [audit], index, owner_identity="Project Owner") == []
    assert review_audit_errors([{**final, "split": "holdout"}], [audit], index,
                               owner_identity="Project Owner") == []
    assert review_audit_errors([{**final, "doc_ids": ["changed"]}], [audit], index,
                               owner_identity="Project Owner") == ["reviewed_content_changed:" + final["qid"]]
    assert review_audit_errors([final], [audit], index, owner_identity="Someone Else") == [
        "invalid_review_packet:" + final["qid"]]


@pytest.mark.parametrize("change", ["missing_qid", "duplicate", "malformed_packet", "forged_export_hash", "rejected"])
def test_audit_rejects_invalid_or_unapproved_input(tmp_path, change):
    *_, index, _ = review_inputs(tmp_path)
    final, audit = actual_audit(human_rows()[0], index)
    entries = [deepcopy(audit)]
    if change == "missing_qid":
        entries[0]["qid"] = "another-qid"
    elif change == "duplicate":
        entries.append(entries[0])
    elif change == "malformed_packet":
        entries[0].pop("review_packet")
    elif change == "forged_export_hash":
        entries[0]["exported_record_sha256"] = "f" * 64
    else:
        entries[0]["review_packet"]["review_status"] = "rejected"
    assert review_audit_errors([final], entries, index, owner_identity="Project Owner")


def test_human_freeze_passes_owner_policy_and_builds_s1_after_freeze(tmp_path):
    args = Namespace(stage="human-freeze", benchmark_dir=tmp_path / "benchmark", results_dir=tmp_path / "results",
                     index_dir=tmp_path / "index", model_dir=None, model_name="unused", device="cpu",
                     owner_identity=None, assign_splits=True, review_audit=tmp_path / "actual_audit.jsonl")
    commands = release_workflow.commands(args)
    assert len(commands) == 2
    assert commands[0][2] == "evaluation.benchmarks.freeze_human_benchmark"
    assert "--assign-splits" in commands[0]
    assert commands[0][commands[0].index("--review-policy") + 1] == str(args.benchmark_dir / "phase7_review_policy.json")
    assert commands[1][2] == "evaluation.reranker.build_supplemental_report"
    assert commands[1][commands[1].index("--review-audit") + 1] == str(args.review_audit)


def test_workflow_rejects_invalid_audit_before_freeze_process(tmp_path, monkeypatch):
    benchmark = tmp_path / "benchmark"
    benchmark.mkdir()
    dataset = benchmark / "human_retrieval.jsonl"
    original = json.dumps(human_rows()[0]) + "\n"
    dataset.write_text(original, encoding="utf-8")
    audit = benchmark / "human_retrieval_review_audit.jsonl"
    audit.write_text("", encoding="utf-8")
    calls = []
    monkeypatch.setattr(release_workflow.subprocess, "run", lambda *args, **kwargs: calls.append(args))
    assert release_workflow.main(["human-freeze", "--benchmark-dir", str(benchmark),
                                  "--results-dir", str(tmp_path / "results")]) == 1
    assert calls == []
    assert dataset.read_text(encoding="utf-8") == original
    assert not (tmp_path / "results").exists()


def test_freezer_cli_uses_configured_owner_self_review_policy(tmp_path, monkeypatch):
    from evaluation.benchmarks.freeze_human_benchmark import main as freeze_main
    from evaluation.common import release_artifacts
    *_, index, _ = review_inputs(tmp_path)
    doc = read_json(index / "manifest.json")["documents"][0]
    benchmark, results = tmp_path / "benchmark", tmp_path / "results"
    benchmark.mkdir()
    rows = human_rows()
    for row in rows:
        row.update(author="Project Owner", reviewer="Project Owner", reviewer_role="project_owner", doc_ids=[doc])
        row["gold_evidence"] = [{"doc_id": doc, "chunk_id": "chunk1", "page": 1}] if row["answerable"] else []
    dataset = benchmark / "human_retrieval.jsonl"
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    pool = benchmark / "human_candidate_pool.jsonl"
    pool.write_text("bound fixture source\n", encoding="utf-8")
    lineage = benchmark / "human_candidate_lineage.json"
    groups = connected_groups(rows)
    write_json(lineage, {"connected_groups": groups})
    write_json(benchmark / "phase7_review_policy.json", {"owner_identity": "Project Owner", "owner_self_review_allowed": True})
    write_json(benchmark / "phase7_exposure_registry.json", {"status": "pass", "dataset_sha256": sha256(pool),
               "lineage_sha256": sha256(lineage), "index_sha256": sha256(index / "manifest.json"),
               "records": [{"qid": row["qid"], "connected_group": groups[row["qid"]], "status": "unexposed_audited",
                            "heldout_eligible": True, "history_audit": {"complete": True, "archive_reference": "test-fixture",
                            "archive_sha256": "a" * 64, "study_manifest_sha256": "b" * 64}} for row in rows]})
    monkeypatch.setattr(release_artifacts, "require_previous_gates", lambda *args, **kwargs: None)
    assert freeze_main(["--dataset", str(dataset), "--index-dir", str(index), "--output-dir", str(results),
                        "--regression-dir", str(benchmark)]) == 0
    review = read_json(results / "human_benchmark_review.json")
    assert review["review_mode"] == "owner_self_review"
    assert review["review_complete"] is True
    assert review["review_policy_sha256"] == sha256(benchmark / "phase7_review_policy.json")


def test_preflight_retains_unknown_history_and_does_not_fill_negative_scope(tmp_path):
    pool, staging, lineage, registry, index, _ = review_inputs(tmp_path)
    benchmark = tmp_path / "benchmark"
    benchmark.mkdir()
    for source, name in ((pool, "human_candidate_pool.jsonl"), (staging, "human_candidate_staging.jsonl"),
                          (lineage, "human_candidate_lineage.json"), (registry, "phase7_exposure_registry.json")):
        (benchmark / name).write_bytes(source.read_bytes())
    exposure = read_json(benchmark / "phase7_exposure_registry.json")
    exposure.update(status="pending_complete_history_audit", index_sha256=sha256(index / "manifest.json"))
    for row in exposure["records"]:
        row.update(status="unknown_pending_history_audit", heldout_eligible=False)
    write_json(benchmark / "phase7_exposure_registry.json", exposure)
    write_json(benchmark / "phase7_review_policy.json", {"owner_identity": "Owner", "owner_self_review_allowed": True})
    before = {p.name: p.read_bytes() for p in benchmark.iterdir()}
    report = inspect_inputs(benchmark, tmp_path / "missing_intake", index)
    assert report["status"] == "blocked" and report["release_eligible"] is False
    assert report["counts"]["review_pending_or_invalid"] == 2
    assert report["counts"]["negative_scope_pending"] == 1
    assert report["counts"]["unknown_history"] == 2
    assert report["safe_split_proposal"]["split_counts"] == {"dev": 2}
    assert before == {p.name: p.read_bytes() for p in benchmark.iterdir()}


def test_preflight_refuses_to_overwrite_gate_or_input(tmp_path):
    with pytest.raises(SystemExit) as error:
        inspect_main(["--output", str(tmp_path / "human_benchmark_review.json")])
    assert error.value.code == 2
    assert not list(tmp_path.iterdir())


def test_pipeline_preflight_delegates_without_creating_approvals(tmp_path, monkeypatch):
    from scripts.benchmarks import check_phase7_review
    called = []
    monkeypatch.setattr(check_phase7_review, "main", lambda argv: called.append(argv) or 1)
    assert pipeline_main(["preflight", "--output", str(tmp_path / "diagnostic.json")]) == 1
    assert called == [["--output", str(tmp_path / "diagnostic.json")]]
    assert not list(tmp_path.iterdir())


def owner_confirmation_inputs(tmp_path):
    from evaluation.benchmarks.owner_review import confirm_existing
    *_, index, _ = review_inputs(tmp_path)
    dataset = tmp_path / "human_retrieval.jsonl"
    rows = human_rows()[:2]
    dataset.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    write_json(tmp_path / "phase7_review_policy.json", {"owner_identity": "Owner", "owner_self_review_allowed": True,
                                                       "owner_dataset_confirmation_allowed": True})
    confirmation = confirm_existing(dataset, tmp_path, owner_statement="I created and reviewed all the existing data.")
    return dataset, rows, confirmation, index


def test_owner_confirmation_accepts_one_real_dataset_statement_and_preserves_semantics(tmp_path):
    from evaluation.benchmarks.owner_review import confirmed_row, confirmation_audit, load_confirmation
    _, sources, confirmation, index = owner_confirmation_inputs(tmp_path)
    loaded, rows = load_confirmation(tmp_path)
    assert loaded == confirmation and rows == sources
    approved = [confirmed_row(row, confirmation) for row in rows]
    audit = confirmation_audit(confirmation, rows)
    assert review_audit_errors(approved, audit, index, owner_identity="Owner", owner_confirmation=loaded,
                               confirmed_sources=rows) == []
    for original, reviewed in zip(sources, approved):
        for field in ("qid", "question", "gold_evidence", "doc_ids", "filters", "split", "expected_behavior"):
            assert reviewed[field] == original[field]
        assert reviewed["author"] == reviewed["reviewer"] == "Owner"
        assert reviewed["reviewer_role"] == "project_owner"
    assert confirmation["exposure_history_confirmed"] is False
    changed = [{**approved[0], "question": "changed after owner confirmation"}, approved[1]]
    assert review_audit_errors(changed, audit, index, owner_identity="Owner", owner_confirmation=loaded,
                               confirmed_sources=rows) == ["reviewed_content_changed:" + approved[0]["qid"]]


@pytest.mark.parametrize("change", ["snapshot", "owner_policy", "record_binding", "future_time", "exposure_claim"])
def test_owner_confirmation_cannot_authorize_changed_data_policy_or_exposure(tmp_path, change):
    from evaluation.benchmarks.owner_review import load_confirmation
    _, _, confirmation, _ = owner_confirmation_inputs(tmp_path)
    if change == "snapshot":
        (tmp_path / confirmation["source_snapshot"]["path"]).write_text("changed", encoding="utf-8")
    elif change == "owner_policy":
        write_json(tmp_path / "phase7_review_policy.json", {"owner_identity": "Someone Else", "owner_self_review_allowed": True,
                                                           "owner_dataset_confirmation_allowed": True})
    else:
        if change == "record_binding":
            confirmation["source_record_sha256"]["hn-0"] = "a" * 64
        elif change == "future_time":
            confirmation["recorded_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        else:
            confirmation["exposure_history_confirmed"] = True
        write_json(tmp_path / "phase7_owner_confirmation.json", confirmation)
    with pytest.raises(ValueError):
        load_confirmation(tmp_path)


def test_owner_confirmation_export_keeps_source_bytes_and_changes_only_review_metadata(tmp_path):
    from scripts.benchmarks.record_owner_confirmation import record
    rows = human_rows()[:2]
    dataset = tmp_path / "human_retrieval.jsonl"
    original = "".join(json.dumps(row) + "\n" for row in rows).encode()
    dataset.write_bytes(original)
    write_json(tmp_path / "phase7_review_policy.json", {"owner_identity": "Owner", "owner_self_review_allowed": True,
                                                       "owner_dataset_confirmation_allowed": True})
    result = record(dataset, tmp_path, "I confirm my existing data.")
    assert result["records"] == 2 and result["benchmark_frozen"] is False
    confirmation = read_json(tmp_path / "phase7_owner_confirmation.json")
    assert (tmp_path / confirmation["source_snapshot"]["path"]).read_bytes() == original
    exported = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    assert [r["question"] for r in exported] == [r["question"] for r in rows]
    assert all(r["reviewer_role"] == "project_owner" for r in exported)
    assert (tmp_path / "human_retrieval_review_audit.jsonl").is_file()
    with pytest.raises(ValueError, match="audit exists"):
        record(dataset, tmp_path, "another statement")


def test_legacy_abstain_schema_migration_preserves_confirmed_source(tmp_path):
    from evaluation.benchmarks.owner_review import confirmed_row
    _, sources, confirmation, _ = owner_confirmation_inputs(tmp_path)
    original = {**sources[0], "answerable": False, "expected_behavior": "abstain_no_evidence", "gold_evidence": []}
    reviewed = confirmed_row(original, confirmation)
    assert original["expected_behavior"] == "abstain_no_evidence"
    assert reviewed["expected_behavior"] == "abstain"
    assert reviewed["review_schema_normalization"] == {"expected_behavior": {"from": "abstain_no_evidence", "to": "abstain"}}


@pytest.mark.parametrize("tamper", [None, "dataset_hash", "qid", "duplicate", "index"])
def test_prior_exposure_requires_exact_archived_dataset_and_unique_observations(tmp_path, tamper):
    from scripts.benchmarks.record_prior_candidate_exposure import record_exposure
    _, sources, _, index = owner_confirmation_inputs(tmp_path)
    pool = tmp_path / "human_candidate_pool.jsonl"
    pool.write_text("physical source pool fixture", encoding="utf-8")
    groups = connected_groups(sources)
    lineage = tmp_path / "human_candidate_lineage.json"
    write_json(lineage, {"connected_groups": groups})
    registry_path = tmp_path / "phase7_exposure_registry.json"
    write_json(registry_path, {"status": "pending_complete_history_audit", "dataset_sha256": sha256(pool),
                              "lineage_sha256": sha256(lineage), "index_sha256": sha256(index / "manifest.json"),
                              "records": [{"qid": r["qid"], "connected_group": groups[r["qid"]],
                                           "status": "unknown_pending_history_audit", "heldout_eligible": False} for r in sources]})
    original_registry = registry_path.read_bytes()
    report = {"index_sha256": sha256(index / "manifest.json"), "splits": {}}
    import hashlib
    for split in ("dev", "test", "holdout"):
        rows = [r for r in sources if r["split"] == split]
        payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in rows).encode()
        report["splits"]["human_" + split] = {"benchmark_sha256": hashlib.sha256(payload).hexdigest(),
                                                  "caps": {"40": {"per_query": [{"qid": r["qid"], "candidates": []} for r in rows]}}}
    part = report["splits"]["human_dev"]
    if tamper == "dataset_hash":
        part["benchmark_sha256"] = "a" * 64
    elif tamper == "qid":
        part["caps"]["40"]["per_query"][0]["qid"] = "reused-in-another-dataset"
    elif tamper == "duplicate":
        part["caps"]["40"]["per_query"].append(part["caps"]["40"]["per_query"][0])
    elif tamper == "index":
        report["index_sha256"] = "a" * 64
    report_path = tmp_path / "coverage.json"
    write_json(report_path, report)
    if tamper:
        with pytest.raises(ValueError):
            record_exposure(tmp_path, report_path, tmp_path / "archive", index)
        assert registry_path.read_bytes() == original_registry
    else:
        result = record_exposure(tmp_path, report_path, tmp_path / "archive", index)
        assert result["status"] == "pass" and result["heldout_eligible_records"] == 0
        registry = read_json(registry_path)
        assert all(r["status"].startswith("known_exposed") and r["heldout_eligible"] is False for r in registry["records"])
        assert (tmp_path / "archive" / (sha256(report_path) + ".json")).read_bytes() == report_path.read_bytes()


@pytest.mark.parametrize("tamper", [None, "original", "parent", "allocation", "allocation_binding", "regression", "regression_record"])
def test_dev_revision_retains_physical_parent_and_effective_dev_allocation(tmp_path, tamper):
    import shutil
    from evaluation.benchmarks.owner_review import confirm_existing, confirmed_row, load_confirmation
    from scripts.benchmarks.create_owner_source_benchmark import write_rows
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    dataset, sources, parent, _ = owner_confirmation_inputs(parent_dir)
    cycle = tmp_path / "revision"
    cycle.mkdir()
    shutil.copyfile(parent_dir / "phase7_review_policy.json", cycle / "phase7_review_policy.json")
    shutil.copytree(parent_dir / "owner_confirmed_inputs", cycle / "owner_confirmed_inputs")
    shutil.copyfile(parent_dir / "phase7_owner_confirmation.json", cycle / "parent_owner_confirmation.json")
    write_rows(cycle / "parent_human_retrieval_dev.jsonl", [{**confirmed_row(row, parent), "split": "dev"} for row in sources])
    regression = {"origin": {"qid": "origin", "difficulty": "hard"}}
    write_rows(cycle / "hybrid_retrieval_dev.jsonl", list(regression.values()))
    confirmation = confirm_existing(dataset, cycle, owner_statement=parent["statement"])
    revision = {"original_source_snapshot": parent["source_snapshot"], "original_dev_records": sources,
                "parent_confirmation_sha256": sha256(cycle / "parent_owner_confirmation.json"),
                "original_dev_allocation": {"path": "parent_human_retrieval_dev.jsonl",
                                            "sha256": sha256(cycle / "parent_human_retrieval_dev.jsonl")},
                "allocated_dev_qids": sorted(row["qid"] for row in sources),
                "source_regression_sha256": {"dev": sha256(cycle / "hybrid_retrieval_dev.jsonl")},
                "source_regression_records": regression}
    confirmation["dev_metadata_revision"] = revision
    if tamper == "original": revision["original_dev_records"] = [{**sources[0], "question": "changed"}, sources[1]]
    if tamper == "parent": (cycle / "parent_owner_confirmation.json").write_text("{}", encoding="utf-8")
    if tamper == "allocation":
        write_rows(cycle / "parent_human_retrieval_dev.jsonl", [{**confirmed_row(row, parent), "split": "holdout"} for row in sources])
        revision["original_dev_allocation"]["sha256"] = sha256(cycle / "parent_human_retrieval_dev.jsonl")
    if tamper == "allocation_binding": revision["allocated_dev_qids"] = []
    if tamper == "regression": (cycle / "hybrid_retrieval_dev.jsonl").write_text("{}\n", encoding="utf-8")
    if tamper == "regression_record": revision["source_regression_records"]["origin"]["difficulty"] = "easy"
    write_json(cycle / "phase7_owner_confirmation.json", confirmation)
    if tamper:
        with pytest.raises(ValueError): load_confirmation(cycle)
    else:
        assert load_confirmation(cycle) == (confirmation, sources)
