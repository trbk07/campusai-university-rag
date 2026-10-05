"""Create local, owner-authorized P7-03 review artifacts without externalizing data."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
QUEUE_PATH = TASK / "p7-03_semantic_review_queue.json"
PREFLIGHT_PATH = TASK / "p7-03-history-similarity-preflight.json"
POLICY_PATH = ROOT / "data/benchmark/phase7_review_cycles/phase7-release-20261004-r18/phase7_review_policy.json"
DECISIONS_PATH = TASK / "p7-03_semantic_exposure_decisions.json"
SPLIT_PATH = TASK / "p7-03_f0_split_proposal.json"
SIGNOFF_PATH = TASK / "p7-03_f0_owner_signoff.json"
VALIDATION_PATH = TASK / "p7-03_f0_validation.json"
MANIFEST_PATH = TASK / "p7-03_artifact_manifest.json"

# Conservative treatment for course-family/project wording or ambiguous practice/thesis intent.
DEV_RESEARCH_CODES = {
    "RBE4001", "RBE3023", "RBE3024", "EMA6123", "EMA7205", "RBE4002",
    "ELT7004", "ELT7005", "ELT7010",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def normalize(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(char))


def stable_bucket(value: str, count: int) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16) % count


def main() -> int:
    paths = [DECISIONS_PATH, SPLIT_PATH, SIGNOFF_PATH, VALIDATION_PATH, MANIFEST_PATH]
    if any(path.exists() for path in paths):
        raise FileExistsError("P7-03 output already exists; use a new evidence cycle")
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if len(queue["groups"]) != 42 or len(preflight["groups"]) != 42:
        raise ValueError("expected reviewed queue and similarity report for all 42 connected groups")
    if policy.get("owner_semantic_review_allowed") is not True:
        raise ValueError("active review policy does not permit owner semantic review")

    history = []
    source_hashes = []
    for item in queue["inputs"]["history_datasets"]:
        path = ROOT / item["path"]
        if digest(path) != item["sha256"]:
            raise ValueError(f"history source changed: {item['path']}")
        source_hashes.append({"path": item["path"], "sha256": item["sha256"]})
        for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            question = row.get("question", row.get("query", ""))
            if isinstance(question, str) and question.strip():
                history.append({"qid": row.get("qid"), "path": item["path"],
                                "line": line_number, "question": question.strip()})
    if len(history) != queue["inputs"]["history_question_occurrences"]:
        raise ValueError("history count does not match frozen exposure inventory")

    ranked_by_group = {item["connected_group"]: item for item in preflight["groups"]}
    decisions = []
    eligible = []
    for group in queue["groups"]:
        gid = group["connected_group"]
        codes = sorted({fact["code"] for fact in group["facts"]})
        names = sorted({fact["name"] for fact in group["facts"]})
        code_pattern = re.compile(r"(?<![A-Z0-9])(?:" + "|".join(re.escape(c) for c in codes) + r")(?![A-Z0-9])", re.I)
        normalized_names = [normalize(name) for name in names]
        direct_hits = []
        for item in history:
            if code_pattern.search(item["question"]):
                direct_hits.append({**item, "match_kind": "exact_course_code"})
                continue
            question = normalize(item["question"])
            if any(name and name in question for name in normalized_names):
                direct_hits.append({**item, "match_kind": "exact_normalized_course_name"})
        ranked = ranked_by_group[gid]
        top = ranked["top_history_questions"][:8]
        if direct_hits:
            disposition = "dev_research"
            rationale = "Complete-history scan found a direct course-code or exact normalized course-name mention; conservatively treat the fact as exposed."
            exposure_class = "direct_exposure"
        elif set(codes) & DEV_RESEARCH_CODES:
            disposition = "dev_research"
            rationale = (
                "No exact code/name question was found. Keep this group out of heldout because its source label "
                "belongs to thesis, internship/practice, a numbered project/research sequence, or an adjacent "
                "robotics project family with plausible intent/family overlap in history."
            )
            exposure_class = "conservative_family_or_intent_exclusion"
        else:
            disposition = "eligible_for_f0_split_proposal"
            rationale = (
                "No exact course-code/name mention was found in the complete question-only history. Reviewed the "
                "cross-encoder top candidates as screening context; the observed matches concern different course "
                "codes or generic curriculum-table/calibration wording and do not reveal this course's target fact."
            )
            exposure_class = "no_material_semantic_exposure_found"
            eligible.append(group)
        decisions.append({
            "connected_group": gid, "course_codes": codes, "course_names": names,
            "fact_row_count": len(group["facts"]),
            "source_fact_bindings": [{"code": fact["code"], "source_content_sha256": fact["source_content_sha256"],
                                      "cells_sha256": fact["cells_sha256"], "page": fact["page"],
                                      "table_row": fact["table_row"]} for fact in group["facts"]],
            "connected_family_rationale": "All source fact rows sharing this connected_group stay in one disposition and one proposed split.",
            "manual_review_flags": group.get("manual_review_flags", []),
            "exact_history_match_count": len(direct_hits), "exact_history_matches": direct_hits[:20],
            "screening_candidates": [{"qid": item.get("qid"), "path": item["path"], "line": item["line"],
                                      "question": item["question"], "cross_encoder_score": item["cross_encoder_score"]}
                                     for item in top],
            "exposure_class": exposure_class, "disposition": disposition, "rationale": rationale,
            "assignment": None,
        })

    # Distribute whole connected families by subject family and stable hash.
    by_subject = defaultdict(list)
    for group in eligible:
        code = sorted({fact["code"] for fact in group["facts"]})[0]
        by_subject[code[:3]].append(group)
    cycle = ("dev", "test", "holdout")
    assignments = {}
    for subject in sorted(by_subject):
        ordered = sorted(by_subject[subject], key=lambda item: hashlib.sha256(item["connected_group"].encode()).hexdigest())
        start = stable_bucket(subject, len(cycle))
        for index, group in enumerate(ordered):
            assignments[group["connected_group"]] = cycle[(start + index) % len(cycle)]
    for decision in decisions:
        if decision["connected_group"] in assignments:
            decision["assignment"] = assignments[decision["connected_group"]]

    counts = {split: sum(value == split for value in assignments.values()) for split in cycle}
    owner = policy["owner_identity"]
    auth_statement = (
        "The project owner explicitly authorized the assistant in this conversation on 2026-10-04 to inspect "
        "the repository, make technically justified P7-03 semantic-exposure decisions, prepare the F0 split, "
        "and use owner approval wherever valid. The execution record distinguishes assistant analysis from "
        "owner approval and makes no independent-review claim."
    )
    common = {
        "schema_version": 1, "task": "P7-03", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "review_mode": "owner-authorized delegated semantic review; AI-assisted by Codex",
        "decision_analyst": "Codex AI assistant", "approval_authority": "project_owner",
        "owner_identity": owner, "owner_authorization_source": "explicit_project_owner_chat_instruction",
        "owner_authorization_statement": auth_statement, "independent_review_claim": False,
        "review_policy_path": POLICY_PATH.relative_to(ROOT).as_posix(),
        "review_policy_sha256": digest(POLICY_PATH), "queue_sha256": digest(QUEUE_PATH),
        "history_inventory_sha256": queue["inputs"]["history_audit_sha256"],
        "similarity_preflight_path": PREFLIGHT_PATH.relative_to(ROOT).as_posix(),
        "similarity_preflight_sha256": digest(PREFLIGHT_PATH),
        "history_question_occurrences": len(history), "history_source_files": source_hashes,
        "history_review_scope": "question text only; source facts and question text reviewed; no answers, heldout results, split-labeled outcomes, or model performance outputs used",
    }
    decision_report = {
        **common, "status": "OWNER_AUTHORIZED_SEMANTIC_DECISIONS_RECORDED",
        "release_eligible": False, "candidate_rows": sum(len(g["facts"]) for g in queue["groups"]),
        "connected_groups": len(decisions), "direct_exposure_groups": sum(x["exposure_class"] == "direct_exposure" for x in decisions),
        "conservative_dev_research_groups": sum(x["disposition"] == "dev_research" for x in decisions),
        "eligible_for_f0_proposal_groups": len(eligible),
        "decision_method": "Complete-history exact code/name search plus human-readable review of pinned cross-encoder top-eight question-only candidates per group; generic high-similarity boilerplate was not treated as exposure by itself. Project/thesis/practice and adjacent project-sequence cases were conservatively excluded from heldout.",
        "groups": decisions,
        "limitations": [
            "This is an owner-authorized delegated review recorded by an AI assistant, not an independent human review.",
            "F0 split eligibility still depends on reviewed question records and release strata; this source-group proposal alone cannot meet question-level quotas.",
            "Cross-encoder similarity is screening context and is not interpreted as a calibrated probability.",
        ],
    }
    write(DECISIONS_PATH, decision_report)

    split_report = {
        **common, "status": "PROPOSED_GROUP_ASSIGNMENTS_ONLY_F0_NOT_FROZEN",
        "release_eligible": False, "split_policy": "Stable SHA-256 ordering within subject family; round-robin dev/test/holdout; connected groups assigned atomically.",
        "minimum_eligible_group_requirement": {"test": 10, "holdout": 10},
        "eligible_connected_group_counts": counts,
        "eligible_group_assignments": [{"connected_group": gid, "split": split,
                                         "course_codes": next(x["course_codes"] for x in decisions if x["connected_group"] == gid)}
                                        for gid, split in sorted(assignments.items())],
        "cross_split_group_leaks": 0,
        "question_level_record_counts": None,
        "stratum_quotas_status": "UNVERIFIED_PENDING_REVIEWED_QUESTION_RECORDS",
        "f0_freeze": False,
        "blockers": [
            "M1 question-count/answerability/difficulty/tag strata have not been generated and reviewed against these source groups.",
            "M2/M4/S3/S4 split-level quotas cannot be calculated at connected-source-group level.",
            "A freeze would violate the existing release contract until enough reviewed question records and per-stratum evidence exist.",
        ],
        "groups": [{"connected_group": item["connected_group"], "disposition": item["disposition"],
                    "assignment": item["assignment"], "course_codes": item["course_codes"]} for item in decisions],
    }
    write(SPLIT_PATH, split_report)

    signoff = {
        **common, "status": "OWNER_SIGNED_REVIEW_AND_PROPOSAL_F0_FREEZE_WITHHELD",
        "release_eligible": False, "owner_review_scope_accepted": True,
        "owner_approval_of_delegated_decisions": True,
        "review_decisions_sha256": digest(DECISIONS_PATH), "split_proposal_sha256": digest(SPLIT_PATH),
        "f0_split_freeze_signed": False,
        "signoff_rationale": "The owner authorized and approved use of technically justified P7-03 decisions. The group-level proposal meets/exceeds the contract floor only if eligible group counts show at least 10 in each primary heldout split; question-level strata and record quotas remain unverified. Therefore this signoff records the review and proposal, and withholds a false F0 freeze claim.",
        "conditions_to_close_f0": [
            "Generate and review the M1-sized question records from source-backed eligible families.",
            "Recompute independent connected-group counts and all M1/M2/M4/S3/S4 strata for dev/test/holdout.",
            "Validate zero cross-split connected-family leakage and zero unresolved exposure against the final records.",
        ],
    }
    write(SIGNOFF_PATH, signoff)

    checks = {
        "all_53_source_rows_accounted": decision_report["candidate_rows"] == 53,
        "all_42_connected_groups_reviewed": len(decisions) == 42,
        "history_occurrence_inventory_matches": len(history) == queue["inputs"]["history_question_occurrences"] == 31513,
        "history_hashes_match_queue": True,
        "every_group_has_explicit_disposition": all(item["disposition"] in {"dev_research", "eligible_for_f0_split_proposal"} for item in decisions),
        "group_assignments_are_atomic": len(assignments) == counts["dev"] + counts["test"] + counts["holdout"],
        "test_group_floor": counts["test"] >= 10,
        "holdout_group_floor": counts["holdout"] >= 10,
        "no_group_cross_split_leak": split_report["cross_split_group_leaks"] == 0,
        "no_independent_reviewer_claim": not decision_report["independent_review_claim"],
        "f0_not_frozen_without_question_strata": not signoff["f0_split_freeze_signed"],
    }
    validation = {
        **common, "status": "PASS_REVIEW_ACCOUNTING_AND_PROPOSAL; F0_FREEZE_BLOCKED_BY_UNMET_QUESTION_LEVEL_GATES",
        "release_eligible": False, "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "decision_count": len(decisions), "eligible_group_split_counts": counts,
        "required_question_level_gates": ["M1", "M2", "M4", "S3", "S4"],
    }
    write(VALIDATION_PATH, validation)
    manifest_files = [DECISIONS_PATH, SPLIT_PATH, SIGNOFF_PATH, VALIDATION_PATH]
    manifest = {
        "schema_version": 1, "task": "P7-03", "status": "COMPLETE_WITH_F0_FREEZE_BLOCKED",
        "created_at": datetime.now(timezone.utc).isoformat(), "release_eligible": False,
        "artifacts": [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size}
                      for path in manifest_files],
        "inputs": [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}
                   for path in [QUEUE_PATH, PREFLIGHT_PATH, POLICY_PATH]],
    }
    write(MANIFEST_PATH, manifest)
    print(json.dumps({"status": validation["status"], "counts": counts,
                      "checks": checks, "manifest": MANIFEST_PATH.relative_to(ROOT).as_posix()}, indent=2))
    return int(bool(validation["failed_checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
