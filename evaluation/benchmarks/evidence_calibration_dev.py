"""Source-audited auxiliary dev negatives, for exploratory M5 work only.

The owner commissions the AI records; no independent human review, new heldout
data, or release qualification is claimed. Validation reconstructs every row
and checks all bodies in its scoped document, including decoded table cells.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from campusai.retrieval.tokenizer_vi import source_body
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.benchmarks.owner_generation import course_facts, plain, load_generation
from evaluation.benchmarks.retrieval_schema import load_jsonl
from evaluation.common.release_artifacts import read_json, sha256, write_json

TEMPLATE_GROUP = "dev-absent-instructor-pair-v1"
INSTRUCTOR_PATTERN = r"\b(?:giang vien|giao vien|lecturers?|instructors?|teachers?)\b"
APPROVAL_STATEMENT = "t duyệt hết nên bạn cứ nhập tên tác giải là t"
GENERATION_STATEMENT = "nếu k có thì tự tạo đi, t cho phép"


def scoped_absence_proof(doc_id: str, evidence: dict) -> dict:
    scoped = {chunk: item for (doc, chunk), item in evidence.items() if doc == doc_id}
    if not scoped or any(item.get("metadata", {}).get("document_type") != "curriculum"
                         for item in scoped.values()):
        raise ValueError("absence proof requires a complete scoped curriculum")
    if any(re.search(INSTRUCTOR_PATTERN, plain(source_body(item)).replace("đ", "d"))
           for item in scoped.values()):
        raise ValueError("scoped document mentions instructor terms; absence is not established")
    return {"method": "scoped_curriculum_instructor_absence_v2",
            "checked_pattern": INSTRUCTOR_PATTERN, "doc_ids": [doc_id],
            "source_chunks": len(scoped),
            "body_sha256": {chunk: digest_record({"body": source_body(item)})
                            for chunk, item in sorted(scoped.items())},
            "meaning": "No instructor term appears in any supplied curriculum body; no institution-wide absence is inferred."}


def _inputs(benchmark: Path, index: Path) -> tuple[list[dict], dict, dict, dict]:
    policy = read_json(benchmark / "phase7_review_policy.json")
    confirmation = read_json(benchmark / "phase7_owner_confirmation.json")
    owner = policy.get("owner_identity")
    if (not isinstance(owner, str) or not owner.strip()
            or policy.get("owner_self_review_allowed") is not True
            or confirmation.get("owner_identity") != owner
            or confirmation.get("status") != "owner_confirmed"
            or confirmation.get("review_policy_sha256") != sha256(benchmark / "phase7_review_policy.json")):
        raise ValueError("configured owner review policy/confirmation binding required")
    rows = load_jsonl(benchmark / "human_retrieval_dev.jsonl")
    if (not rows or any(row.get("split") != "dev" for row in rows)
            or len({row["qid"] for row in rows}) != len(rows)):
        raise ValueError("unique, explicit primary dev rows required")
    _, generated = load_generation(benchmark, index)
    if any(row != generated.get(row["qid"]) for row in rows if "ownerfresh" in row["qid"]):
        raise ValueError("primary generated course anchors differ from owner-authorized source bank")
    return rows, frozen_evidence(index), policy, confirmation


def build_records(primary: list[dict], evidence: dict, owner: str,
                  confirmation_hash: str, recorded_at: str, count: int) -> tuple[list[dict], list[dict], list[dict]]:
    if type(count) is not int or count < 1:
        raise ValueError("positive record count required")
    stamp = datetime.fromisoformat(recorded_at)
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError("actual timezone-aware generation timestamp required")
    groups: dict[str, list[dict]] = {}
    for row in primary:
        if (row.get("answerable") is True and row.get("difficulty") == "easy"
                and "ownerfresh" in row.get("qid", "")):
            groups.setdefault(row["paraphrase_group"], []).append(row)
    facts = course_facts(evidence)
    generated, audits, excluded = [], [], []
    for group, family in sorted(groups.items()):
        family = sorted(family, key=lambda row: row["qid"])
        courses = []
        for row in family:
            match = re.search(r"Môn (.+?) \(([A-Z0-9]+)\)", row["question"])
            if not match or len(row.get("gold_evidence", [])) != 1:
                continue
            gold = row["gold_evidence"][0]
            matches = [fact for fact in facts if fact["doc_id"] == gold["doc_id"]
                       and fact["chunk_id"] == gold["chunk_id"] and fact["code"] == match.group(2)
                       and plain(fact["name"]) == plain(match.group(1))]
            if len(matches) != 1:
                raise ValueError("primary dev course fact does not match its frozen source")
            if (row.get("review_status") != "approved"
                    or row.get("reviewer") != owner
                    or not row.get("generation_authorization_sha256")):
                raise ValueError("primary dev family lacks bound owner review")
            courses.append(matches[0])
        if (len(family) != 2 or len(courses) != 2 or len({f["code"] for f in courses}) != 2
                or len({f["doc_id"] for f in courses}) != 1):
            continue
        doc = courses[0]["doc_id"]
        try:
            proof = scoped_absence_proof(doc, evidence)
        except ValueError as error:
            excluded.append({"paraphrase_group": group, "doc_id": doc, "reason": str(error)})
            continue
        if len(generated) == count:
            continue
        qid = f"phase7-evidence-negative-v2-{len(generated) + 1:03d}"
        question = ("Trong tài liệu có nêu những giảng viên phụ trách đồng thời cả học phần "
                    f"{courses[0]['name']} và {courses[1]['name']} không?")
        generated.append({
            "schema_version": 2, "qid": qid, "candidate_id": qid, "question": question,
            "language": "vi", "category": "negative", "query_type": "unanswerable",
            "negative_class": "not_in_corpus", "expected_retrieval": "abstain",
            "answerable": False, "ambiguous": False, "difficulty": "hard", "split": "dev",
            "paraphrase_group": group, "template_group": TEMPLATE_GROUP,
            "doc_ids": [doc], "filters": {}, "context": [], "selected_text": None,
            "gold_evidence": [], "expected_claims": [], "expected_behavior": "abstain",
            "question_source": "owner_directed_source_bounded_generation",
            "evidence_source": "frozen_pdf_reviewed_negative",
            "source_record_id": ",".join(row["qid"] for row in family),
            "author": owner, "author_type": "ai", "generator": "Codex",
            "author_disclosure": "owner_directed_ai_generation",
            "reviewer": owner, "reviewer_role": "project_owner", "review_status": "approved",
            "review_evidence_kind": "owner_directed_chat_authorization_and_self_review",
            "reviewed_at": recorded_at, "owner_confirmation_sha256": confirmation_hash,
            "tags": ["hard", "negative", "owner_directed_ai_generation", "evidence_calibration_only"],
            "supplemental_calibration_only": True,
        })
        audits.append({"qid": qid, "paraphrase_group": group,
                       "source_qids": [row["qid"] for row in family], "courses": courses,
                       "question_sha256": digest_record({"question": question}), "absence_proof": proof})
    if len(generated) != count:
        raise ValueError(f"requested {count} records but only {len(generated)} source-audited dev pairs qualify")
    return generated, audits, excluded


def _bindings(benchmark: Path, index: Path) -> dict:
    return {"primary_dev_sha256": sha256(benchmark / "human_retrieval_dev.jsonl"),
            "index_manifest_sha256": sha256(index / "manifest.json"),
            "review_policy_sha256": sha256(benchmark / "phase7_review_policy.json"),
            "owner_confirmation_sha256": sha256(benchmark / "phase7_owner_confirmation.json"),
            "parent_generation_authorization_sha256": sha256(benchmark / "phase7_generation_authorization.json"),
            "parent_source_bank_sha256": sha256(benchmark / "owner_generated_source_bank.json"),
            "parent_history_snapshot_sha256": sha256(benchmark / "owner_generation_history_snapshot.json")}


def create(benchmark: Path, index: Path, output: Path, manifest_path: Path, count: int = 8) -> dict:
    import json
    if output.exists() or manifest_path.exists():
        raise FileExistsError("refusing to overwrite existing exploratory artifacts")
    if manifest_path != output.with_suffix(".manifest.json"):
        raise ValueError("manifest must be a sibling of the records")
    primary, evidence, policy, _ = _inputs(benchmark, index)
    bindings = _bindings(benchmark, index)
    stamp = datetime.now(timezone.utc).isoformat()
    records, audit, excluded = build_records(primary, evidence, policy["owner_identity"],
                                            bindings["owner_confirmation_sha256"], stamp, count)
    from evaluation.benchmarks.connected_groups import connected_groups
    groups = connected_groups(primary + records)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    artifact = {"schema_version": 2, "evidence_type": "owner_directed_evidence_calibration_dev",
                "status": "exploratory_only", "split": "dev", "record_count": len(records),
                "records_sha256": sha256(output), **bindings,
                "owner": policy["owner_identity"], "approval_source": "project_owner_chat_instruction",
                "approval_statement": APPROVAL_STATEMENT, "generation_statement": GENERATION_STATEMENT,
                "review_mode": "owner_self_review_by_standing_chat_authorization",
                "ai_origin_disclosed": True, "independent_human_review_claim": False,
                "heldout_sources_used": False, "heldout_measurements_used_to_select_questions": False,
                "new_heldout_claim": False, "created_at": stamp, "source_audit": audit,
                "excluded_source_families": excluded,
                "auxiliary_connected_group_count": len({groups[row["qid"]] for row in records})}
    write_json(manifest_path, artifact)
    return artifact


def load_validated(path: Path, primary_path: Path, index: Path) -> tuple[list[dict], dict]:
    manifest = read_json(path.with_suffix(".manifest.json"))
    primary, evidence, policy, _ = _inputs(primary_path.parent, index)
    bindings = _bindings(primary_path.parent, index)
    if primary_path.name != "human_retrieval_dev.jsonl":
        raise ValueError("supplement requires the frozen primary dev path")
    expected_constants = {"schema_version": 2, "evidence_type": "owner_directed_evidence_calibration_dev",
                          "status": "exploratory_only", "split": "dev", **bindings,
                          "owner": policy["owner_identity"], "approval_source": "project_owner_chat_instruction",
                          "approval_statement": APPROVAL_STATEMENT, "generation_statement": GENERATION_STATEMENT,
                          "review_mode": "owner_self_review_by_standing_chat_authorization",
                          "ai_origin_disclosed": True, "independent_human_review_claim": False,
                          "heldout_sources_used": False, "heldout_measurements_used_to_select_questions": False,
                          "new_heldout_claim": False, "records_sha256": sha256(path)}
    if any(type(manifest.get(key)) is not type(value) or manifest[key] != value
           for key, value in expected_constants.items()):
        raise ValueError("supplement owner/source/exploratory binding changed")
    rows, audit, excluded = build_records(primary, evidence, policy["owner_identity"],
                                          bindings["owner_confirmation_sha256"],
                                          manifest["created_at"], manifest["record_count"])
    from evaluation.benchmarks.connected_groups import connected_groups
    groups = connected_groups(primary + rows)
    if (load_jsonl(path) != rows or manifest.get("source_audit") != audit
            or manifest.get("excluded_source_families") != excluded
            or manifest.get("auxiliary_connected_group_count") != len({groups[row["qid"]] for row in rows})
            or {r["qid"] for r in primary} & {r["qid"] for r in rows}):
        raise ValueError("supplement rows/source proof/family grouping differ from reconstruction")
    return rows, manifest
