"""Independently audit metadata-only rebinding of the four-call S2 study."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from evaluation.common.release_artifacts import sha256, source_identity
from evaluation.benchmarks.retrieval_schema import load_jsonl
from evaluation.reranker.supplemental_gates import context_errors
from evaluation.common.release_artifacts import read_json
from campusai.retrieval.runtime_provenance import runtime_sha256

ALLOWED_DEV_METADATA = {"difficulty", "owner_confirmation_sha256", "reviewed_at", "tags"}
SOURCE_COMMIT = "b79543764fc7551729503129b650f66a3b77b4f6"
TARGET_COMMIT = "618a6ef0b62390574937dcd1a197208b8fe96b08"
ORIGINAL_RAW_SHA256 = "e6321d83ada3d6b9461e1be2033b1e28240f771d2a48e1cc49baa8188138d5e5"


def changed_paths(root: Path, before: str, after: str, paths: tuple[str, ...]) -> list[str]:
    output = subprocess.check_output(["git", "diff", "--name-only", before, after, "--", *paths],
                                     cwd=root, text=True)
    return sorted(line.replace("\\", "/") for line in output.splitlines() if line)


def uncommitted_source_paths(root: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=all", "--", "src", "evaluation", "scripts", "tests", "configs"],
        cwd=root, text=True)
    result = set()
    for line in output.splitlines():
        path = line[3:].replace("\\", "/")
        if path.endswith(".py") or (path.startswith("configs/") and Path(path).suffix.lower() in
                                     {".json", ".toml", ".yaml", ".yml"}
                                     and Path(path).name != "gemini.yaml"):
            result.add(path)
    return sorted(result)


def audit(original_path: Path, rebound_path: Path, original_benchmark: Path,
          target_benchmark: Path, results_dir: Path, index_dir: Path) -> dict:
    original = json.loads(original_path.read_text(encoding="utf-8"))
    rebound = json.loads(rebound_path.read_text(encoding="utf-8"))
    proof = rebound.get("binding_replay", {})
    checks: dict[str, bool] = {}
    errors = []

    def check(name: str, condition: bool) -> None:
        checks[name] = bool(condition)
        if not condition:
            errors.append(name)

    raw_digest = sha256(original_path)
    measured = proof.get("original_measurement", {})
    target = proof.get("target_binding", {})
    check("original_raw_bytes", raw_digest == ORIGINAL_RAW_SHA256 == measured.get("raw_sha256"))
    check("original_commit", original.get("commit") == SOURCE_COMMIT == measured.get("commit"))
    check("original_source", original.get("source_sha256") == measured.get("source_sha256"))
    check("original_runtime", original.get("runtime_sha256") == measured.get("runtime_sha256"))
    check("target_cycle_commit", target.get("commit") == TARGET_COMMIT)
    check("target_runtime_same", target.get("runtime_sha256") == original.get("runtime_sha256")
          == rebound.get("runtime_sha256") == runtime_sha256())
    check("target_index_same", original.get("index_sha256") == rebound.get("index_sha256")
          == sha256(index_dir / "manifest.json"))

    restored = dict(rebound)
    restored.pop("binding_replay", None)
    for field in ("commit", "source_sha256", "dev_sha256"):
        restored[field] = original[field]
    check("observations_unmodified", restored == original)
    check("live_response_count", len(original.get("context_cases", [])) == 7
          and len(original.get("llm_failures", [])) == 0)
    check("calls_added", proof.get("verification", {}).get("additional_gemini_calls") == 0)

    old_dev = load_jsonl(original_benchmark / "human_retrieval_dev.jsonl")
    target_dev = load_jsonl(target_benchmark / "human_retrieval_dev.jsonl")
    old_by_id = {row["qid"]: row for row in old_dev}
    new_by_id = {row["qid"]: row for row in target_dev}
    check("dev_qid_order", [row["qid"] for row in old_dev] == [row["qid"] for row in target_dev]
          and set(old_by_id) == set(new_by_id))
    changed_rows = 0
    actual_changed_fields: set[str] = set()
    for qid in old_by_id.keys() & new_by_id.keys():
        changed = {key for key in old_by_id[qid].keys() | new_by_id[qid].keys()
                   if old_by_id[qid].get(key) != new_by_id[qid].get(key)}
        if changed:
            changed_rows += 1
            actual_changed_fields.update(changed)
        if changed - ALLOWED_DEV_METADATA:
            errors.append("dev_question_or_evidence_changed:" + qid)
    check("only_allowed_dev_metadata", not any(item.startswith("dev_question_or_evidence_changed:") for item in errors)
          and actual_changed_fields == ALLOWED_DEV_METADATA)
    check("dev_change_counts", changed_rows == 180)
    check("dev_hashes", sha256(original_benchmark / "human_retrieval_dev.jsonl") == original.get("dev_sha256")
          and sha256(target_benchmark / "human_retrieval_dev.jsonl") == target.get("dev_sha256"))
    check("heldout_bytes_identical", all(sha256(original_benchmark / f"human_retrieval_{split}.jsonl")
          == sha256(target_benchmark / f"human_retrieval_{split}.jsonl")
          for split in ("test", "holdout")))

    old_answerable = [row for row in old_dev if row.get("answerable") is True]
    new_answerable = [row for row in target_dev if row.get("answerable") is True]
    expected_topics = [(old_answerable[i]["qid"], old_answerable[i]["question"])
                       for i in range(2)]
    actual_topics = []
    for case_name in ("different_history", "different_selection"):
        cases = [case for case in rebound["context_cases"] if case.get("case") == case_name]
        if len(cases) != 2:
            actual_topics.extend([("", "")] * 2)
            continue
        for case in cases:
            request = case["request"]
            question = (request.get("history", [{}])[0].get("content") if case_name == "different_history"
                        else request.get("selected_text"))
            matches = [row for row in new_answerable if row.get("question") == question]
            actual_topics.append((matches[0]["qid"], question) if len(matches) == 1 else ("", str(question)))
    check("four_prompt_topics", actual_topics == expected_topics + expected_topics)
    check("lifecycle_query_identity", rebound.get("lifecycle_proof", {}).get("qid")
          == old_answerable[next(i for i, row in enumerate(old_answerable)
                                 if row.get("difficulty") == "hard")]["qid"])
    docs = read_json(index_dir / "manifest.json")["documents"]
    check("all_scope_docs_stable", all(
        case.get("doc_ids") == ([] if case["case"] in {"empty_scope", "selection_not_evidence"} else docs)
        for case in rebound.get("context_cases", [])))

    commit_paths = changed_paths(Path.cwd(), SOURCE_COMMIT, TARGET_COMMIT,
                                 ("src", "evaluation", "scripts", "tests", "configs"))
    python_paths = [path for path in commit_paths if path.endswith(".py")]
    check("commit_path_audit_correct", proof.get("verification", {}).get("source_commit_changed_paths") != commit_paths
          and python_paths == ["scripts/benchmarks/revise_dev_difficulty.py"])
    current = source_identity(Path.cwd())
    current_paths = sorted(set(changed_paths(Path.cwd(), TARGET_COMMIT, current["commit"],
                                             ("src", "evaluation", "scripts", "tests", "configs")))
                           | set(uncommitted_source_paths(Path.cwd())))
    current_runtime_paths = [path for path in current_paths if path.startswith("src/campusai/")]
    check("serving_runtime_paths_unchanged", not current_runtime_paths
          and current["runtime_sha256"] == original["runtime_sha256"])

    supplemental = read_json(results_dir / "reranker_context_lifecycle.json")
    raw_relative = supplemental.get("raw", {}).get("path")
    raw_path = results_dir / raw_relative if isinstance(raw_relative, str) else Path()
    check("supplement_binds_replay", raw_path.is_file() and raw_path.resolve() == rebound_path.resolve()
          and supplemental.get("raw", {}).get("sha256") == sha256(rebound_path))
    s2_errors = context_errors(supplemental) if not errors else ["independent_rebind_audit_failed"]
    check("s2_gate_recomputed", not s2_errors)
    return {"schema_version": 1, "status": "pass" if not errors else "fail", "errors": errors,
            "checks": checks, "actual_changed_dev_rows": changed_rows,
            "actual_changed_dev_fields": sorted(actual_changed_fields),
            "source_paths_between_measurement_and_cycle": commit_paths,
            "source_paths_since_cycle": current_paths,
            "runtime_source_paths_since_cycle": current_runtime_paths,
            "supplemental_s2_status": supplemental.get("status"),
            "supplemental_s2_errors": s2_errors,
            "source_identity_current": current,
            "heldout_rows_parsed": False, "gemini_calls": 0,
            "statement": "Audits provenance of already recorded responses; makes no new measurement claim."}
