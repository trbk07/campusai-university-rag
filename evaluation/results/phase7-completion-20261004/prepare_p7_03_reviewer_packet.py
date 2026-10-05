"""Prepare a reviewer-attributed P7-03 queue without deciding freshness/splits."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "evaluation/results/phase7-completion-20261004"
AUDIT = OUT / "p7-03-expanded-history-audit.json"
DEV = OUT / "p7-02-dev-replay/human_retrieval_dev.jsonl"
INDEX_MANIFEST = ROOT / ".tmp/phase7-source-b-restored-p701/manifest.json"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    dev_rows = [json.loads(line) for line in DEV.read_text(encoding="utf-8").splitlines() if line.strip()]
    grouped = defaultdict(list)
    for fact in audit["proposals"]:
        grouped[fact["connected_group"]].append(fact)
    order = ("answerable", "difficulty", "exact_code", "ambiguous", "contextual",
             "table", "multi_hop", "multi_document", "scoped", "year", "semester")
    strata = defaultdict(Counter)
    for row in dev_rows:
        strata["split"][row.get("split", "missing")] += 1
        strata["answerability"]["answerable" if row.get("answerable") else "negative"] += 1
        strata["difficulty"][str(row.get("difficulty", "unknown"))] += 1
        for tag in row.get("tags", []):
            strata["tag"][str(tag)] += 1
        flags = {
            "exact_code": bool(row.get("exact_code")) or "exact_code" in row.get("tags", []),
            "ambiguous": bool(row.get("ambiguous")) or "ambiguous" in row.get("tags", []),
            "contextual": bool(row.get("context") or row.get("history") or row.get("selected_text")
                                or row.get("requires_context") or "contextual" in row.get("tags", [])),
            "table": "table" in row.get("tags", []) or any(x.get("table_id") for x in row.get("gold_evidence", [])),
            "multi_hop": len(row.get("gold_evidence", [])) > 1,
            "multi_document": len({x.get("doc_id") for x in row.get("gold_evidence", [])}) > 1,
            "scoped": row.get("doc_ids") is not None or bool(row.get("filters")),
            "year": any(str(y) in row.get("question", "") for y in range(2000, 2101)),
            "semester": any(x in row.get("question", "").casefold() for x in ("semester", "term", "học kỳ", "học kì", "hoc ky")),
        }
        for key, present in flags.items():
            if present:
                strata[key]["present"] += 1
    candidates = []
    for group_id, facts in sorted(grouped.items()):
        facts.sort(key=lambda x: (x["doc_id"], x["page"], x["table_row"], x["code"]))
        names = sorted({fact["name"] for fact in facts})
        codes = sorted({fact["code"] for fact in facts})
        manual_flags = []
        joined = " ".join(names).casefold()
        if any(token in joined for token in ("project", "thesis", "training", "practicum", "internship")):
            manual_flags.append("generic_project_thesis_or_practice_wording_needs_intent_review")
        candidates.append({
            "connected_group": group_id,
            "course_codes": codes,
            "course_names": names,
            "fact_row_count": len(facts),
            "facts": [{"doc_id": f["doc_id"], "chunk_id": f["chunk_id"], "page": f["page"],
                       "table_row": f["table_row"], "code": f["code"], "name": f["name"],
                       "credits": f["credits"], "prerequisite_codes": f["prerequisite_codes"],
                       "source_content_sha256": f["source_content_sha256"], "cells_sha256": f["cells_sha256"],
                       "columns": f["columns"], "headers": f["headers"]} for f in facts],
            "exposure_screen": "lexical/history proposal only; semantic independence unapproved",
            "review_status": "PENDING_ACTUAL_REVIEWER",
            "manual_review_flags": manual_flags,
            "split_assignment": None,
            "reviewer": None,
            "review_decision": None,
            "review_rationale": None,
        })
    packet = {
        "schema_version": 1,
        "task": "P7-03",
        "status": "REVIEW_QUEUE_ONLY",
        "release_eligible": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "history_audit_sha256": file_hash(AUDIT),
            "dev_packet_sha256": file_hash(DEV),
            "index_manifest_sha256": file_hash(INDEX_MANIFEST),
            "history_datasets": audit["history_datasets"],
            "history_question_occurrences": audit["history_question_occurrences"],
            "history_inventory_complete": audit["history_directory_inventory_complete"],
            "history_semantic_approval_complete": audit["history_semantic_approval_complete"],
        },
        "current_dev": {"records": len(dev_rows), "strata": {key: dict(sorted(value.items())) for key, value in strata.items()}},
        "proposal_summary": {
            "explicit_rows": audit["explicit_course_rows"],
            "proposal_rows": len(audit["proposals"]),
            "connected_groups": len(candidates),
            "candidate_group_count_is_not_proof_of_independence": True,
        },
        "review_instructions": [
            "Review every connected group against complete question/evidence history; record reviewer identity, decision, rationale, and supporting qid/history references.",
            "Treat generic project/thesis/practice wording and shared evidence/template dependencies as elevated review priority; lexical non-match is not freshness proof.",
            "Do not assign a test/holdout split until exposure decisions, strata quotas, and cross-split group checks are signed off.",
            "Keep all unresolved or previously consumed groups in dev/research. Preserve exact physical evidence coordinates and hashes.",
        ],
        "groups": candidates,
    }
    path = OUT / "p7-03_semantic_review_queue.json"
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": path.as_posix(), "groups": len(candidates), "proposal_rows": len(audit["proposals"]),
                      "dev_records": len(dev_rows), "status": packet["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
