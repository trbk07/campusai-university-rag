"""Dev additions preserve source proofs, owner authorization and heldout scope."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from evaluation.benchmarks import dev_evidence_extension as extension
from evaluation.benchmarks import owner_review
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.benchmarks.owner_generation import course_facts, generated_audit
from evaluation.common.release_artifacts import sha256, write_json
from evaluation.reranker.supplemental_gates import review_audit_errors


def inputs(tmp_path, monkeypatch):
    table = {"headers": ["STT", "Mã học phần", "Học phần", "Số tín chỉ"],
             "rows": [["1", "ABC1001", "Đại số", "4"], ["2", "XYZ1002", "Vật lý", "3"]]}
    evidence = {("doc", "table"): {"content": json.dumps(table, ensure_ascii=False), "page": 1,
                                   "metadata": {"document_type": "curriculum"}}}
    facts = course_facts(evidence)
    policy = {"owner_identity": "Owner"}
    benchmark = tmp_path / "benchmark"
    benchmark.mkdir()
    index = tmp_path / "index"
    index.mkdir()
    write_json(index / "manifest.json", {"documents": ["doc"]})
    write_json(benchmark / "phase7_review_policy.json", policy)
    write_json(benchmark / "phase7_owner_confirmation.json", {"owner_identity": "Owner"})
    parent = [{"qid": "parent", "question": "ABC1001 cùng XYZ1002", "split": "dev"}]
    (benchmark / "dev_extension_parent_dev.jsonl").write_text(
        json.dumps(parent[0]) + "\n", encoding="utf-8")
    monkeypatch.setattr(owner_review, "load_confirmation", lambda _: ({"owner_identity": "Owner"}, parent))
    monkeypatch.setattr(owner_review, "confirmed_row", lambda row, _: row)
    spec = {"qid": "human-dev-evidence-001", "family": "already-dev-courses", "kind": "dev_absent_field",
            "split": "dev", "facts": facts, "facet": "exam_schedule",
            "absence_proof": extension.absence_proof(facts, "exam_schedule", evidence)}
    bank_path = benchmark / "owner_generated_dev_source_bank.json"
    write_json(bank_path, {"dev_only": True, "records": [spec]})
    auth = {"profile": "personal_owner_source_checked_ai", "owner_identity": "Owner",
            "approval_source": "project_owner_chat_instruction",
            "approval_statement": "t duyệt hết nên bạn cứ nhập tên tác giải là t",
            "generation_statement": "nếu k có thì tự tạo đi, t cho phép",
            "recorded_at": datetime.now(timezone.utc).isoformat(), "independent_human_review_claim": False,
            "dev_only": True, "new_heldout_claim": False,
            "review_policy_sha256": sha256(benchmark / "phase7_review_policy.json"),
            "index_sha256": sha256(index / "manifest.json"),
            "parent_confirmation_sha256": sha256(benchmark / "phase7_owner_confirmation.json"),
            "parent_dev_sha256": sha256(benchmark / "dev_extension_parent_dev.jsonl"),
            "source_bank_sha256": sha256(bank_path)}
    write_json(benchmark / "phase7_dev_generation_authorization.json", auth)
    return benchmark, index, policy, evidence, auth, spec


def test_dev_only_absence_rows_keep_ai_origin_and_their_own_authorization(tmp_path, monkeypatch):
    benchmark, index, policy, evidence, auth, spec = inputs(tmp_path, monkeypatch)
    actual_auth, rows = extension.load_dev_extension(benchmark, index, policy, evidence)
    row = rows[spec["qid"]]
    assert actual_auth == auth
    assert row["split"] == "dev" and row["author_type"] == "ai"
    assert row["answerable"] is False and row["gold_evidence"] == row["expected_claims"] == []
    assert row["difficulty"] == "hard" and row["expected_behavior"] == "abstain"
    assert row["generation_authorization_sha256"] == digest_record(auth)
    base = {**auth, "recorded_at": "2026-01-01T00:00:00+00:00", "_validated_dev_authorization": auth}
    audit = generated_audit(base, rows)
    assert audit[0]["generation_authorization_sha256"] == digest_record(auth)
    assert review_audit_errors(list(rows.values()), audit, index, owner_identity="Owner",
                              generation_authorization=base, generated_records=rows) == []
    audit[0]["generation_authorization_sha256"] = "a" * 64
    assert review_audit_errors(list(rows.values()), audit, index, owner_identity="Owner",
                              generation_authorization=base, generated_records=rows)


@pytest.mark.parametrize("facet,mention", [("fee_waiver", "Lệ phí đăng ký được miễn"),
                                         ("exam_schedule", "Lịch thi: tháng sáu"),
                                         ("teaching_room", "Phòng học 202")])
def test_absence_proof_covers_all_scoped_body_chunks(tmp_path, monkeypatch, facet, mention):
    _, _, _, evidence, _, spec = inputs(tmp_path, monkeypatch)
    proof = extension.absence_proof(spec["facts"], facet, evidence)
    assert proof["source_chunks"] == 1 and proof["doc_ids"] == ["doc"]
    evidence["doc", "other"] = {"content": mention, "metadata": {"document_type": "curriculum"}}
    with pytest.raises(ValueError, match="source mention"):
        extension.absence_proof(spec["facts"], facet, evidence)


@pytest.mark.parametrize("change", ["credits", "same_code", "non_curriculum", "unknown_facet"])
def test_absence_proof_rejects_unproved_facts(tmp_path, monkeypatch, change):
    _, _, _, evidence, _, spec = inputs(tmp_path, monkeypatch)
    facts = deepcopy(spec["facts"])
    facet = "exam_schedule"
    if change == "credits":
        facts[0]["credits"] = 99
    elif change == "same_code":
        facts[1] = facts[0]
    elif change == "non_curriculum":
        evidence["doc", "table"]["metadata"]["document_type"] = "regulation"
    else:
        facet = "invented"
    with pytest.raises(ValueError):
        extension.absence_proof(facts, facet, evidence)


@pytest.mark.parametrize("change", ["owner", "future", "naive", "independent", "heldout", "dev_only",
                                   "bank_hash", "parent_hash", "index_hash", "source_body", "bank_split",
                                   "unknown_code", "duplicate", "parent_changed", "proof"])
def test_annex_validation_rejects_tampering(tmp_path, monkeypatch, change):
    benchmark, index, policy, evidence, auth, spec = inputs(tmp_path, monkeypatch)
    if change == "owner":
        auth["owner_identity"] = "Another"
    elif change == "future":
        auth["recorded_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    elif change == "naive":
        auth["recorded_at"] = "2026-01-01T00:00:00"
    elif change == "independent":
        auth["independent_human_review_claim"] = True
    elif change == "heldout":
        auth["new_heldout_claim"] = True
    elif change == "dev_only":
        auth["dev_only"] = False
    elif change in {"bank_hash", "parent_hash", "index_hash"}:
        auth[{"bank_hash": "source_bank_sha256", "parent_hash": "parent_dev_sha256",
              "index_hash": "index_sha256"}[change]] = "a" * 64
    elif change == "source_body":
        evidence["doc", "extra"] = {"content": "Harmless new source body",
                                     "metadata": {"document_type": "curriculum"}}
    elif change == "parent_changed":
        parent_path = benchmark / "dev_extension_parent_dev.jsonl"
        parent_path.write_text(json.dumps({"qid": "parent", "question": "ABC1001", "split": "dev"}), encoding="utf-8")
        auth["parent_dev_sha256"] = sha256(parent_path)
    else:
        if change == "bank_split":
            spec["split"] = "holdout"
        elif change == "unknown_code":
            spec["facts"][0]["code"] = "ZZ99999"
        elif change == "proof":
            spec["absence_proof"]["source_chunks"] = 99
        bank_path = benchmark / "owner_generated_dev_source_bank.json"
        write_json(bank_path, {"dev_only": True, "records": [spec, spec] if change == "duplicate" else [spec]})
        auth["source_bank_sha256"] = sha256(bank_path)
    write_json(benchmark / "phase7_dev_generation_authorization.json", auth)
    with pytest.raises(ValueError):
        extension.load_dev_extension(benchmark, index, policy, evidence)


def test_absent_annex_keeps_legacy_behavior(tmp_path):
    assert extension.load_dev_extension(tmp_path, tmp_path, {}, {}) == (None, {})


@pytest.mark.parametrize("facet", list(extension.FACETS))
def test_each_question_family_requires_information_missing_from_source(tmp_path, monkeypatch, facet):
    _, _, _, _, auth, spec = inputs(tmp_path, monkeypatch)
    spec["facet"] = facet
    row = extension.extension_row(spec, auth)
    assert "ABC1001" in row["question"] and "XYZ1002" in row["question"]
    assert row["template_group"] == "dev-absent-curriculum-field-" + facet

