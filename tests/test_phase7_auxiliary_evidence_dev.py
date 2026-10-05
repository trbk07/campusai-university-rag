"""Auxiliary experiments cannot change source proofs or release criteria."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from evaluation.benchmarks import evidence_calibration_dev as aux
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.common.release_artifacts import read_json, sha256, write_json


def inputs(tmp_path, monkeypatch):
    benchmark, index = tmp_path / "benchmark", tmp_path / "index"
    benchmark.mkdir()
    table = {"headers": ["STT", "Mã học phần", "Học phần", "Số tín chỉ"],
             "rows": [["1", "ABC1001", "Đại số", "4"], ["2", "XYZ1002", "Vật lý", "3"]]}
    evidence = {("doc", "table"): {"content": json.dumps(table, ensure_ascii=False), "page": 1,
                                    "metadata": {"document_type": "curriculum"}}}
    policy = {"owner_identity": "Owner", "owner_self_review_allowed": True}
    write_json(benchmark / "phase7_review_policy.json", policy)
    write_json(benchmark / "phase7_owner_confirmation.json", {
        "status": "owner_confirmed", "owner_identity": "Owner",
        "review_policy_sha256": sha256(benchmark / "phase7_review_policy.json")})
    for name in ("phase7_generation_authorization.json", "owner_generated_source_bank.json",
                 "owner_generation_history_snapshot.json"):
        write_json(benchmark / name, {})
    write_json(index / "manifest.json", {"documents": ["doc"]})
    primary = [{"qid": f"human-ownerfresh-{i}", "split": "dev", "answerable": True,
                "question": f"Môn {name} ({code}) trong bảng này có mấy tín chỉ?",
                "gold_evidence": [{"doc_id": "doc", "chunk_id": "table", "page": 1}],
                "difficulty": "easy", "paraphrase_group": "pair", "reviewer": "Owner",
                "review_status": "approved", "generation_authorization_sha256": "a" * 64}
               for i, (name, code) in enumerate((("Đại số", "ABC1001"), ("Vật lý", "XYZ1002")))]
    (benchmark / "human_retrieval_dev.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in primary), encoding="utf-8")
    monkeypatch.setattr(aux, "frozen_evidence", lambda _: evidence)
    monkeypatch.setattr(aux, "load_generation", lambda *_: ({}, {r["qid"]: r for r in primary}))
    path = tmp_path / "aux.jsonl"
    manifest_path = path.with_suffix(".manifest.json")
    aux.create(benchmark, index, path, manifest_path, count=1)
    return benchmark, index, path, manifest_path, evidence, primary


def test_roundtrip_discloses_origin_and_single_connected_template(tmp_path, monkeypatch):
    benchmark, index, path, _, _, primary = inputs(tmp_path, monkeypatch)
    rows, manifest = aux.load_validated(path, benchmark / "human_retrieval_dev.jsonl", index)
    assert rows[0]["author"] == rows[0]["reviewer"] == "Owner"
    assert rows[0]["author_type"] == "ai" and rows[0]["expected_behavior"] == "abstain"
    assert rows[0]["template_group"] == aux.TEMPLATE_GROUP
    assert manifest["status"] == "exploratory_only"
    assert manifest["independent_human_review_claim"] is False
    assert manifest["auxiliary_connected_group_count"] == 1
    second = {**rows[0], "qid": "other", "paraphrase_group": "different-courses"}
    groups = connected_groups(primary + rows + [second])
    assert groups[rows[0]["qid"]] == groups[second["qid"]]


@pytest.mark.parametrize("content", ["Giảng viên không ghi ở bảng môn", "INSTRUCTOR: An",
                                     json.dumps({"headers": ["Giảng\nviên"], "rows": [["An"]]}, ensure_ascii=False)])
def test_absence_covers_other_chunks_and_decoded_cells(tmp_path, monkeypatch, content):
    _, _, _, _, evidence, _ = inputs(tmp_path, monkeypatch)
    evidence["doc", "unrelated"] = {"content": content, "metadata": {"document_type": "curriculum"}}
    with pytest.raises(ValueError, match="mentions instructor"):
        aux.scoped_absence_proof("doc", evidence)


@pytest.mark.parametrize("change", ["owner", "independent", "heldout", "primary_hash", "proof",
                                   "records", "template", "source_body", "naive", "future", "count_bool"])
def test_load_reconstructs_and_rejects_tampering(tmp_path, monkeypatch, change):
    benchmark, index, path, manifest_path, evidence, _ = inputs(tmp_path, monkeypatch)
    manifest = read_json(manifest_path)
    if change == "owner":
        manifest["owner"] = "Another"
    elif change == "independent":
        manifest["independent_human_review_claim"] = True
    elif change == "heldout":
        manifest["heldout_sources_used"] = True
    elif change == "primary_hash":
        manifest["primary_dev_sha256"] = "a" * 64
    elif change == "proof":
        manifest["source_audit"][0]["absence_proof"]["source_chunks"] = 99
    elif change in ("records", "template"):
        row = json.loads(path.read_text(encoding="utf-8"))
        row["question" if change == "records" else "template_group"] = "changed"
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        manifest["records_sha256"] = sha256(path)
    elif change == "source_body":
        evidence["doc", "new"] = {"content": "Additional source paragraph", "metadata": {"document_type": "curriculum"}}
    elif change == "naive":
        manifest["created_at"] = "2026-01-01T00:00:00"
    elif change == "future":
        manifest["created_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    else:
        manifest["record_count"] = True
    write_json(manifest_path, manifest)
    with pytest.raises(ValueError):
        aux.load_validated(path, benchmark / "human_retrieval_dev.jsonl", index)


def test_count_failure_and_overwrite_preserve_existing_artifacts(tmp_path, monkeypatch):
    benchmark, index, path, manifest_path, _, _ = inputs(tmp_path, monkeypatch)
    old = path.read_bytes(), manifest_path.read_bytes()
    with pytest.raises(FileExistsError):
        aux.create(benchmark, index, path, manifest_path, count=1)
    assert (path.read_bytes(), manifest_path.read_bytes()) == old
    fresh = tmp_path / "fresh.jsonl"
    with pytest.raises(ValueError, match="only 1"):
        aux.create(benchmark, index, fresh, fresh.with_suffix(".manifest.json"), count=2)
    assert not fresh.exists() and not fresh.with_suffix(".manifest.json").exists()


def test_owner_course_anchor_tampering_is_rejected(tmp_path, monkeypatch):
    benchmark, index, path, _, _, _ = inputs(tmp_path, monkeypatch)
    parent = benchmark / "human_retrieval_dev.jsonl"
    rows = [json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()]
    rows[0]["reviewer"] = "Other"
    parent.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="anchors differ"):
        aux.load_validated(path, parent, index)


def test_auxiliary_cannot_be_used_by_official_calibration(tmp_path, monkeypatch, capsys):
    from evaluation.reranker import calibrate_reranker_scores as calibration
    monkeypatch.setattr("sys.argv", ["calibration", "--model-dir", str(tmp_path), "--evidence-dev", "aux.jsonl"])
    with pytest.raises(SystemExit) as result:
        calibration.main()
    assert result.value.code == 2
    assert "exploratory only" in capsys.readouterr().err
