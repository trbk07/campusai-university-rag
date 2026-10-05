"""Personal generation is explicit, source checked and separate from human origin."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json

import pytest

from evaluation.benchmarks.freeze_human_benchmark import validate_rows
from evaluation.benchmarks.owner_generation import (course_facts, curriculum_facts, corpus_absence_proof,
                                                     generated_row, validate_generation, generated_audit)
from evaluation.reranker.supplemental_gates import review_audit_errors


def inputs():
    table = {"headers": ["STT", "Mã học phần", "Học phần", "Số tín chỉ", "Số giờ tín chỉ"],
             "rows": [["1", "ABC1001", "Đại số", "4", "60"], ["2", "XYZ1002", "Vật lý", "3", "45"]]}
    evidence = {("doc", "chunk"): {"doc_id": "doc", "chunk_id": "chunk", "page": 1,
                                   "content": json.dumps(table, ensure_ascii=False), "metadata": {}}}
    auth = {"profile": "personal_owner_source_checked_ai", "owner_identity": "Owner",
            "approval_source": "project_owner_chat_instruction",
            "approval_statement": "t duyệt hết nên bạn cứ nhập tên tác giải là t",
            "generation_statement": "nếu k có thì tự tạo đi, t cho phép",
            "independent_human_review_claim": False, "recorded_at": datetime.now(timezone.utc).isoformat()}
    facts = course_facts(evidence)
    spec = {"qid": "human-fresh", "family": "disjoint-course-facts", "kind": "sum", "facts": facts}
    return evidence, auth, spec


def test_course_extraction_requires_credit_header_and_preserves_source_row():
    evidence, _, _ = inputs()
    facts = course_facts(evidence)
    assert [f["credits"] for f in facts] == [4, 3]
    assert [f["table_row"] for f in facts] == [0, 1]
    table = json.loads(evidence["doc", "chunk"]["content"])
    table["headers"][3] = "Số giờ tín chỉ"
    evidence["doc", "chunk"]["content"] = json.dumps(table)
    assert course_facts(evidence) == []


def test_owner_generation_is_rejected_by_default_and_disclosed_when_authorized(tmp_path):
    evidence, auth, spec = inputs()
    expected = validate_generation(auth, [spec], evidence, "Owner")
    row = generated_row(spec, auth)
    strict = validate_rows([row], evidence, owner_identity="Owner")
    assert "row_1:human_authorship_and_approval_required" in strict["errors"]
    personal = validate_rows([row], evidence, owner_identity="Owner", generated_records=expected)
    assert "row_1:fake_or_example_record" not in personal["errors"]
    assert not any(e.startswith("row_1:") for e in personal["errors"])
    assert personal["authorship_counts"] == {"ai": 1}
    assert personal["benchmark_profile"] == "personal_owner_source_checked_ai"
    assert personal["independent_review_complete"] is False
    audit = generated_audit(auth, expected)
    assert review_audit_errors([row], audit, tmp_path, owner_identity="Owner",
                              generation_authorization=auth, generated_records=expected) == []
    row["split"] = "holdout"
    assert review_audit_errors([row], audit, tmp_path, owner_identity="Owner",
                              generation_authorization=auth, generated_records=expected) == []
    row["question"] += " changed"
    assert review_audit_errors([row], audit, tmp_path, owner_identity="Owner",
                              generation_authorization=auth, generated_records=expected)


@pytest.mark.parametrize("change", ["credits", "page", "row", "cells", "owner", "claim", "approval", "future", "duplicate"])
def test_owner_generation_rejects_forged_facts_or_authorization(change):
    evidence, auth, spec = inputs()
    bank = [deepcopy(spec)]
    if change == "credits":
        bank[0]["facts"][0]["credits"] = 99
    elif change == "page":
        bank[0]["facts"][0]["page"] = 2
    elif change == "row":
        bank[0]["facts"][0]["table_row"] = 7
    elif change == "cells":
        bank[0]["facts"][0]["cells_sha256"] = "a" * 64
    elif change == "owner":
        auth["owner_identity"] = "Another Owner"
    elif change == "claim":
        auth["independent_human_review_claim"] = True
    elif change == "approval":
        auth["approval_statement"] = "invented"
    elif change == "future":
        auth["recorded_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    else:
        bank.append(bank[0])
    with pytest.raises(ValueError):
        validate_generation(auth, bank, evidence, "Owner")


def test_negative_claim_is_proved_absent_and_not_a_fabricated_gold_answer():
    evidence, auth, spec = inputs()
    spec.update(kind="absent_course", missing_code="ZZ90001")
    row = validate_generation(auth, [spec], evidence, "Owner")[spec["qid"]]
    assert row["gold_evidence"] == [] and row["answerable"] is False
    assert row["expected_behavior"] == "abstain" and row["expected_claims"] == []
    evidence["doc", "chunk"]["content"] += " ZZ90001"
    # An extra non-table chunk is sufficient to invalidate the absence proof.
    evidence["other", "text"] = {"content": "ZZ90001", "page": 1}
    evidence["doc", "chunk"]["content"] = evidence["doc", "chunk"]["content"].removesuffix(" ZZ90001")
    with pytest.raises(ValueError, match="not absent"):
        validate_generation(auth, [spec], evidence, "Owner")


def test_curriculum_fact_is_extracted_with_semester_and_row_provenance():
    table = {"headers": ["№", "Discipline", "Credits", "Resources"],
             "rows": [["Semester 1", "", "", ""], ["1", "Aerospace Engineering", "3", "VNU-UET"]]}
    evidence = {("curriculum", "table-1"): {"doc_id": "curriculum", "chunk_id": "table-1", "page": 1,
                                             "content_type": "table",
                                             "content": json.dumps(table, ensure_ascii=False), "metadata": {}}}
    facts = curriculum_facts(evidence, document_id="curriculum")
    assert len(facts) == 1
    assert {key: facts[0][key] for key in ("name", "credits", "semester", "table_row")} == {
        "name": "Aerospace Engineering", "credits": 3, "semester": 1, "table_row": 1}


def test_full_corpus_absence_claim_binds_every_indexed_chunk():
    evidence, auth, _ = inputs()
    auth = {**auth, "curriculum_document_id": "curriculum"}
    index_hash = "a" * 64
    spec = {"qid": "human-fresh-negative", "family": "absent-code-91000",
            "kind": "corpus_absent_code", "facts": [], "missing_code": "ZZ91000",
            "document_ids": ["doc"], "absence_proof": corpus_absence_proof("ZZ91000", evidence, index_hash)}
    expected = validate_generation(auth, [spec], evidence, "Owner", index_sha256=index_hash)
    row = expected[spec["qid"]]
    assert row["answerable"] is False
    assert row["gold_evidence"] == []
    assert row["doc_ids"] == ["doc"]
    assert row["source_validation"]["absence_proof"]["chunk_count"] == len(evidence)
    evidence[("other", "chunk")] = {"content": "ZZ91000", "page": 1}
    with pytest.raises(ValueError, match="present in the frozen corpus"):
        validate_generation(auth, [spec], evidence, "Owner", index_sha256=index_hash)
