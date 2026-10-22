"""Fictional unit attestations only; never official human review evidence."""
from copy import deepcopy
import hashlib
import json
import sys

import pytest

from evaluation.benchmarks.benchmark_schema import CATEGORIES
from evaluation.grounding.repair_benchmark import stable_hash
from evaluation.grounding.review_evidence import annotation_sha256
from scripts.release.annotation_signoff import main


def invoke(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["annotation_signoff", *map(str, args)])
    code = main()
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def fictional_review(tmp_path):
    rows = []
    categories = sorted(CATEGORIES)
    for split, count in (("dev", 120), ("test", 130), ("holdout", 150)):
        for index in range(count):
            answerable = index % 2 == 0
            rows.append({"id": f"unit-only-{split}-{index}", "split": split,
                "question": f"Which fictional item belongs to unit case {split}-{index}?",
                "language": "en", "category": categories[index % len(categories)],
                "answerable": answerable, "expected_status": "found" if answerable else "no_evidence_found",
                "gold_claims": [{"text": "Fictional unit evidence", "evidence": [{"doc_id": f"unit-{split}",
                    "page": 1, "page_range": [1, 1], "quote": "Fictional unit evidence"}]}] if answerable else [],
                "gold_abstention_reason": None if answerable else "no_evidence_found",
                "source_group": f"unit-{split}", "template_group": f"unit-{split}-{index}",
                "semantic_topic": f"unit-{split}", "adversarial_pattern": f"unit-{split}",
                "review_status": "reviewed", "annotator_id": "fictional-unit-reviewer"})
    benchmark = tmp_path / "unit-benchmark.jsonl"
    benchmark.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    signoff = {"status": "approved", "review_type": "independent_human",
        "benchmark_sha256": hashlib.sha256(benchmark.read_bytes()).hexdigest(),
        "records_total": 400, "records_reviewed": 400, "records_approved": 400,
        "split_leakage": 0, "missing_gold_evidence": 0, "missing_abstention_reason": 0,
        "creator_ids": ["fictional-unit-creator"],
        "reviewers": [{"id": "fictional-unit-reviewer", "reviewer_type": "human", "independent": True,
            "records_reviewed": 400, "attestation": "Fictional unit fixture; no actual approval.",
            "signed_at": "2026-10-16T00:00:00Z"}],
        "exposure_review": {"status": "approved", "holdout_fresh": True,
            "holdout_ids_sha256": stable_hash(sorted(row["id"] for row in rows if row["split"] == "holdout")),
            "reviewer_id": "fictional-unit-reviewer", "signed_at": "2026-10-16T00:00:00Z",
            "evidence_reference": "fictional-unit-fixture-only"},
        "row_decisions": [{"id": row["id"], "status": "approved", "reviewer_id": "fictional-unit-reviewer",
            "signed_at": "2026-10-16T00:00:00Z", "annotation_sha256": annotation_sha256(row)} for row in rows]}
    return benchmark, tmp_path / "unit-signoff.json", signoff


def test_signoff_cli_accepts_complete_contract_in_fictional_unit_fixture(fictional_review, monkeypatch, capsys):
    benchmark, path, payload = fictional_review
    path.write_text(json.dumps(payload), encoding="utf-8")
    code, report = invoke(monkeypatch, capsys, "validate", benchmark, path)
    assert code == 0 and report == {"status": "pass", "errors": []}


@pytest.mark.parametrize("mutation,expected", [
    ("blanket", "independent_row_decisions_missing"),
    ("exposed", "independent_holdout_exposure_review_missing_or_stale"),
    ("changed-row", "independent_row_decision_unapproved_or_stale"),
    ("population", "annotation_records_approved_population_mismatch"),
])
def test_signoff_cli_rejects_incomplete_or_stale_review(fictional_review, monkeypatch, capsys, mutation, expected):
    benchmark, path, payload = fictional_review
    payload = deepcopy(payload)
    if mutation == "blanket":
        del payload["row_decisions"]
    elif mutation == "exposed":
        payload["exposure_review"]["holdout_fresh"] = False
    elif mutation == "changed-row":
        payload["row_decisions"][0]["annotation_sha256"] = "stale"
    else:
        payload["records_approved"] = 399
    path.write_text(json.dumps(payload), encoding="utf-8")
    code, report = invoke(monkeypatch, capsys, "validate", benchmark, path)
    assert code == 1 and report["status"] == "fail" and expected in report["errors"]


def test_signoff_template_uses_actual_population_and_does_not_invent_review(tmp_path, monkeypatch, capsys):
    benchmark = tmp_path / "unit-population.jsonl"
    benchmark.write_text("".join(json.dumps({"id": f"unit-{index}"}) + "\n" for index in range(680)), encoding="utf-8")
    output = tmp_path / "pending-unit-template.json"
    code, report = invoke(monkeypatch, capsys, "template", benchmark, output, "--creator-id", "unit-creator")
    payload = json.loads(output.read_text())
    assert code == 0 and report["status"] == "created_pending_template"
    assert payload["status"] == "pending" and payload["records_total"] == 680
    assert payload["records_reviewed"] == payload["records_approved"] == 0
    assert payload["row_decisions"] == payload["reviewers"] == []
    assert payload["exposure_review"] is None and payload["split_leakage"] is None
    original = output.read_bytes()
    code, report = invoke(monkeypatch, capsys, "template", benchmark, output, "--creator-id", "different-unit-creator")
    assert code == 1 and report["status"] == "fail" and output.read_bytes() == original


def test_signoff_cli_fails_closed_on_malformed_payload(fictional_review, monkeypatch, capsys):
    benchmark, path, _payload = fictional_review
    path.write_text('[]', encoding="utf-8")
    code, report = invoke(monkeypatch, capsys, "validate", benchmark, path)
    assert code == 1 and report["errors"] == ["signoff_or_benchmark_invalid"]


def test_ai_template_records_pending_policy_and_never_invents_owner_approval(tmp_path, monkeypatch, capsys):
    benchmark = tmp_path / "fictional-ai-benchmark.jsonl"
    benchmark.write_text('{"id":"fictional-unit"}\n', encoding="utf-8")
    output = tmp_path / "fictional-ai-template.json"
    code, _report = invoke(monkeypatch, capsys, "template", benchmark, output,
        "--creator-id", "fictional-author", "--review-type", "independent_ai_owner")
    payload = json.loads(output.read_text())
    assert code == 0 and payload["review_type"] == "independent_ai_owner"
    assert payload["review_policy"] == "phase5-ai-owner-v1"
    assert payload["status"] == "pending" and payload["review_artifacts"] == []
    assert payload["owner_authorization"] is None and payload["owner_approval"] is None


def test_signoff_cli_keeps_machine_readable_json_on_windows_codepage(fictional_review):
    import os
    import subprocess
    benchmark, path, payload = fictional_review
    rows = [json.loads(line) for line in benchmark.read_text().splitlines()]
    rows[0]["question"] = rows[120]["question"] = "Câu hỏi tiếng Việt cần review?"
    benchmark.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "scripts.release.annotation_signoff", "validate",
        str(benchmark), str(path)], env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True, text=True, encoding="ascii")
    report = json.loads(result.stdout)
    assert result.returncode == 1 and report["status"] == "fail"
    assert any("câu hỏi" in error for error in report["errors"])
