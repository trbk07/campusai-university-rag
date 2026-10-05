"""Audit inherited ordinal difficulty labels against dev requests and source rows.

This audit does not read held-out questions, change a frozen bundle, or promote
an ambiguous source to a simple lookup. Original records remain hash-bound.
"""
from __future__ import annotations

import re

from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.benchmarks.owner_generation import course_facts, plain

VERSION = "source-checked-dev-difficulty-v1"


def simple_course_lookup(row: dict, facts: list[dict], evidence: dict) -> list[dict]:
    """Require one named code and one unambiguous name/credit fact in scope."""
    question = plain(row.get("question", ""))
    codes = re.findall(r"\b[A-Z]{2,5}\d{3,5}[A-Z]?\b", row.get("question", ""), re.I)
    gold, scope = row.get("gold_evidence", []), row.get("doc_ids", [])
    if (row.get("answerable") is not True or len(codes) != 1 or len(gold) != 1 or len(scope) != 1
            or gold[0].get("doc_id") != scope[0] or row.get("context") or row.get("selected_text")
            or "exact_code" not in row.get("tags", [])
            or not re.search(r"\bla mon gi\b", question)
            or not re.search(r"\b(?:bao nhieu|may) tin chi\b", question)
            or re.search(r"\b(?:neu|tong|so sanh|cong|tru|truoc|sau|compare|sum|if)\b", question)):
        return []
    code = codes[0].upper()
    matching = [fact for fact in facts if fact["code"] == code and fact["doc_id"] == scope[0]]
    if not matching or len({(plain(fact["name"]).replace("*", ""), fact["credits"]) for fact in matching}) != 1:
        return []
    item = evidence.get((gold[0]["doc_id"], gold[0]["chunk_id"]))
    pattern = re.compile(r"(?<!\w)" + r"\s*".join(re.escape(c) for c in code) + r"(?!\w)", re.I)
    if not item or item["page"] != gold[0].get("page") or not pattern.search(item["content"]):
        return []
    return matching


def audit_dev_difficulty(rows: list[dict], source_records: dict[str, dict], evidence: dict,
                         *, allocated_dev_qids: set[str] | None = None) -> dict:
    dev_qids = allocated_dev_qids if allocated_dev_qids is not None else {
        row["qid"] for row in rows if row.get("split") == "dev"}
    if not rows or not {row["qid"] for row in rows} <= dev_qids:
        raise ValueError("difficulty audit accepts dev rows only")
    if len({row["qid"] for row in rows}) != len(rows):
        raise ValueError("unique dev qids required")
    facts = course_facts(evidence)
    changes = []
    for row in rows:
        source_id = row.get("source_record_id", "")
        match = re.fullmatch(r"phase6-(?:dev|test|holdout)-(\d{3})", source_id)
        source = source_records.get(source_id)
        if not match or not source or source.get("qid") != source_id:
            continue
        ordinal_label = ("easy", "medium", "hard")[(int(match[1]) - 1) % 3]
        if (source.get("difficulty") != ordinal_label or row.get("difficulty") != ordinal_label
                or ordinal_label == "easy"):
            continue
        found = simple_course_lookup(row, facts, evidence)
        if not found:
            continue
        source_gold = {(g["doc_id"], g["chunk_id"]) for g in source.get("gold_evidence", [])}
        if {(g["doc_id"], g["chunk_id"]) for g in row["gold_evidence"]} != source_gold:
            continue
        changes.append({"qid": row["qid"], "from": ordinal_label, "to": "easy",
                        "basis": "single_scoped_code_lookup_with_unambiguous_source_name_and_credits",
                        "source_record_id": source_id, "source_record_sha256": digest_record(source),
                        "original_record_sha256": digest_record(row), "course_facts": found})
    return {"schema_version": 1, "version": VERSION, "scope": "dev_only",
            "method": "deterministic_source_audit", "original_difficulty_origin": "legacy_serial_modulo_3",
            "changed_fields": ["difficulty", "tags"], "allocated_dev_qids": sorted(dev_qids), "changes": changes}


def apply_dev_difficulty(rows: list[dict], audit: dict) -> list[dict]:
    if audit.get("version") != VERSION or audit.get("scope") != "dev_only":
        raise ValueError("unsupported difficulty audit")
    changes = {item["qid"]: item for item in audit["changes"]}
    if len(changes) != len(audit["changes"]) or not set(changes) <= {row["qid"] for row in rows}:
        raise ValueError("difficulty audit qids do not match input")
    result = []
    for row in rows:
        change = changes.get(row["qid"])
        if change is None:
            result.append(dict(row))
            continue
        if (row["qid"] not in audit["allocated_dev_qids"] or digest_record(row) != change["original_record_sha256"]
                or row.get("difficulty") != change["from"] or change["to"] != "easy"):
            raise ValueError("difficulty correction changed or references non-dev input")
        tags = [tag for tag in row["tags"] if tag not in {"easy", "medium", "hard"}]
        result.append({**row, "difficulty": "easy", "tags": sorted(set(tags + ["easy"]))})
    return result


def revision_errors(confirmation: dict, sources: list[dict], evidence: dict, index_sha256: str) -> list[str]:
    """Recompute an owner-authorized dev correction at M1/S1 against real evidence."""
    revision = confirmation.get("dev_metadata_revision")
    if revision is None:
        return []
    if (revision.get("schema_version") != 1 or revision.get("owner_identity") != confirmation["owner_identity"]
            or revision.get("approval_source") != "project_owner_standing_chat_instruction"
            or revision.get("approval_statement") != "t duyệt hết nên bạn cứ nhập tên tác giải là t"
            or revision.get("index_sha256") != index_sha256):
        return ["dev_metadata_revision_authorization_or_index"]
    original = revision["original_dev_records"]
    expected = audit_dev_difficulty(original, revision["source_regression_records"], evidence,
                                    allocated_dev_qids=set(revision.get("allocated_dev_qids", [])) or None)
    if expected != revision["audit"]:
        return ["dev_metadata_revision_source_replay"]
    if apply_dev_difficulty(original, expected) != sources:
        return ["dev_metadata_revision_changed_unapproved_fields"]
    return []
