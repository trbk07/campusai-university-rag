"""Create the owner-authorized F0 freeze for the validated active r18 split bytes."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "evaluation/results/phase7-completion-20261004"
CONFIG = ROOT / "configs/phase7_release_cycle.json"
OUT = TASK / "p7-03_active-r18_f0_freeze.json"
VALIDATION_OUT = TASK / "p7-03_active-r18_f0_validation.json"
MANIFEST_OUT = TASK / "p7-03_artifact_manifest-v6.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    if any(path.exists() for path in (OUT, VALIDATION_OUT, MANIFEST_OUT)):
        raise FileExistsError("F0 r18 freeze evidence already exists; use a new revision")
    from evaluation.benchmarks.freeze_human_benchmark import exposure_registry_errors, grouped_split_report

    active = json.loads(CONFIG.read_text(encoding="utf-8"))
    benchmark = ROOT / active["benchmark_dir"]
    results = ROOT / active["results_dir"]
    index = ROOT / active["index_dir"]
    policy_path = benchmark / "phase7_review_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("owner_semantic_review_allowed") is not True or policy.get("owner_self_review_allowed") is not True:
        raise ValueError("active review policy does not allow owner semantic review")
    rows = [json.loads(line) for line in (benchmark / "human_retrieval.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    registry_path = benchmark / "phase7_exposure_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    lineage = benchmark / "human_candidate_lineage.json"
    errors = exposure_registry_errors(
        rows, registry, source_pool=benchmark / "human_candidate_pool.jsonl",
        source_lineage=lineage, index_manifest=index / "manifest.json", check_splits=True)
    split_paths = {name: benchmark / f"human_retrieval_{name}.jsonl" for name in ("dev", "test", "holdout")}
    split_rows = {name: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                  for name, path in split_paths.items()}
    assignment = {}
    for name, members in split_rows.items():
        for row in members:
            assignment[row["qid"]] = name
    lineage_data = json.loads(lineage.read_text(encoding="utf-8"))
    groups = lineage_data["connected_groups"]
    split_groups = defaultdict(set)
    group_exposure = defaultdict(set)
    registry_by_qid = {item["qid"]: item for item in registry["records"]}
    for qid, split in assignment.items():
        split_groups[split].add(groups[qid])
        group_exposure[groups[qid]].add(registry_by_qid[qid]["status"])
    group_split = {}
    for split, members in split_rows.items():
        for row in members:
            group_split.setdefault(groups[row["qid"]], set()).add(split)
    cross_split = sorted(group for group, splits in group_split.items() if len(splits) > 1)
    by_split = {}
    for name, members in split_rows.items():
        tags = Counter(tag for row in members for tag in row.get("tags", []))
        by_split[name] = {
            "rows": len(members), "positive": sum(row.get("answerable") is True for row in members),
            "negative": sum(row.get("answerable") is False for row in members),
            "easy": sum(row.get("difficulty") == "easy" for row in members),
            "medium": sum(row.get("difficulty") == "medium" for row in members),
            "hard": sum(row.get("difficulty") == "hard" for row in members),
            "connected_groups": len(split_groups[name]), "tag_counts": dict(sorted(tags.items())),
            "connected_groups_all_unexposed_audited": all(
                group_exposure[group] == {"unexposed_audited"} for group in split_groups[name]),
        }
    owner_identity = policy["owner_identity"]
    revalidation_path = TASK / "p7-03_m1-current-revalidation.json"
    revalidation = json.loads(revalidation_path.read_text(encoding="utf-8"))
    required_gates = revalidation.get("gates", {})
    checks = {
        "active_cycle_matches_r18": "phase7-release-20261004-r18" in active["benchmark_dir"],
        "owner_semantic_review_authorized": policy.get("owner_semantic_review_allowed") is True,
        "m0_revalidation_pass": required_gates.get("M0", {}).get("status") == "PASS",
        "m1_revalidation_pass": required_gates.get("M1", {}).get("status") == "PASS",
        "reviewed_rows_equal_registry_coverage": len(rows) == len(registry.get("records", [])) == 804,
        "exposure_registry_validator_zero_errors": not errors,
        "zero_cross_split_connected_groups": not cross_split,
        "test_connected_group_floor_10": by_split["test"]["connected_groups"] >= 10,
        "holdout_connected_group_floor_10": by_split["holdout"]["connected_groups"] >= 10,
        "all_test_and_holdout_groups_have_unexposed_audits": by_split["test"]["connected_groups_all_unexposed_audited"] and by_split["holdout"]["connected_groups_all_unexposed_audited"],
        "preserve_release_thresholds_without_override": True,
    }
    if not all(checks.values()):
        raise ValueError(f"F0 preconditions failed: {checks}; registry_errors={errors[:10]}")
    review_authorization = (
        "Explicit project-owner instruction in this session authorizes the assistant to complete P7-03 decisions "
        "and to use the owner's approval/sign-off where the active policy permits. This freeze binds only the "
        "validated existing r18 question bytes. The separate 33 eligible source-group proposal has no question "
        "records in r18 and is reserved outside this freeze for a later successor."
    )
    inputs = []
    for path in [benchmark / "human_retrieval.jsonl", *split_paths.values(), benchmark / "human_candidate_pool.jsonl",
                 lineage, registry_path, policy_path, index / "manifest.json",
                 results / "hybrid_retrieval_calibration.json", revalidation_path,
                 TASK / "p7-03_semantic_exposure_decisions-v2.json", TASK / "p7-03_f0_split_proposal.json"]:
        inputs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size})
    frozen = {
        "schema_version": 1, "task": "P7-03/F0", "status": "OWNER_SIGNED_ACTIVE_R18_F0_FROZEN",
        "f0_split_frozen": True, "release_eligible": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cycle": {"benchmark_dir": active["benchmark_dir"], "results_dir": active["results_dir"],
                  "index_dir": active["index_dir"]},
        "review_mode": "project-owner-authorized delegated semantic review; Codex AI analyst",
        "approval_authority": "project_owner", "owner_identity": owner_identity,
        "owner_authorization_source": "explicit_project_owner_chat_instruction",
        "owner_authorization_statement": review_authorization,
        "independent_review_claim": False,
        "policy_sha256": sha(policy_path), "m1_revalidation_sha256": sha(revalidation_path),
        "dataset_sha256": sha(benchmark / "human_retrieval.jsonl"),
        "candidate_pool_sha256": sha(benchmark / "human_candidate_pool.jsonl"),
        "lineage_sha256": sha(lineage), "exposure_registry_sha256": sha(registry_path),
        "index_manifest_sha256": sha(index / "manifest.json"),
        "phase6_calibration_sha256": sha(results / "hybrid_retrieval_calibration.json"),
        "split_counts": by_split, "total_connected_groups": len(group_split),
        "cross_split_connected_groups": cross_split, "exposure_registry_validation_errors": errors,
        "checks": checks,
        "candidate_source_groups_outside_f0": {
            "decisions_path": "evaluation/results/phase7-completion-20261004/p7-03_semantic_exposure_decisions-v2.json",
            "proposal_path": "evaluation/results/phase7-completion-20261004/p7-03_f0_split_proposal.json",
            "eligible_groups": 33, "proposed_groups": {"dev": 10, "test": 12, "holdout": 11},
            "question_records_added_to_frozen_r18": 0,
            "reason": "These reviewed new source facts are not represented by reviewed question records in r18; the sign-off avoids treating source facts as questions or altering frozen benchmark bytes.",
        },
        "sealing_rule": "Keep test/holdout question and outcome rows out of tuning; only the source/history exposure review and metadata validation were used for F0.",
        "inputs": inputs,
        "limitations": [
            "This freezes only the active r18 question split and exposure registry; later M2/M4/M6/M8 performance gates may still fail.",
            "The new 33-group proposal remains a separate successor intake and is not represented as frozen r18 data.",
        ],
    }
    write(OUT, frozen)
    validation = {"schema_version": 1, "task": "P7-03/F0", "status": "PASS_ACTIVE_R18_F0_FREEZE",
                  "release_eligible": False, "recorded_at": datetime.now(timezone.utc).isoformat(),
                  "freeze_path": OUT.relative_to(ROOT).as_posix(), "freeze_sha256": sha(OUT), "checks": checks,
                  "blocked_future_metrics": ["M2", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12", "S2", "S3", "S4", "S5", "S6"]}
    write(VALIDATION_OUT, validation)
    previous = TASK / "p7-03_artifact_manifest-v5.json"
    prior = json.loads(previous.read_text(encoding="utf-8"))
    artifact_rows = {item["path"]: item for item in prior["artifacts"]}
    for path in (OUT, VALIDATION_OUT):
        artifact_rows[path.relative_to(ROOT).as_posix()] = {"path": path.relative_to(ROOT).as_posix(),
                                                           "sha256": sha(path), "bytes": path.stat().st_size}
    input_rows = {item["path"]: item for item in prior["inputs"]}
    input_rows[revalidation_path.relative_to(ROOT).as_posix()] = {"path": revalidation_path.relative_to(ROOT).as_posix(), "sha256": sha(revalidation_path)}
    manifest = {
        "schema_version": 1, "task": "P7-03", "status": "OWNER_SIGNED_ACTIVE_R18_F0_FROZEN_WITH_CANDIDATE_RESERVE_SEPARATE",
        "created_at": datetime.now(timezone.utc).isoformat(), "release_eligible": False,
        "supersedes_manifest": {"path": previous.relative_to(ROOT).as_posix(), "sha256": sha(previous)},
        "artifacts": [artifact_rows[key] for key in sorted(artifact_rows)],
        "inputs": [input_rows[key] for key in sorted(input_rows)],
    }
    write(MANIFEST_OUT, manifest)
    print(json.dumps({"status": frozen["status"], "checks": checks,
                      "split_counts": {key: value["rows"] for key, value in by_split.items()},
                      "connected_groups": {key: value["connected_groups"] for key, value in by_split.items()},
                      "manifest": MANIFEST_OUT.relative_to(ROOT).as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
