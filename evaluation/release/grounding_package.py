"""Build and validate the auditable Phase 5 release package.

External facts (human review, live provider and staging drills) are accepted
only through explicit evidence documents.  This module never manufactures a
PASS value for an action it did not observe.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from evaluation.grounding.validate_grounding_release import validate as validate_grounding_report


REQUIRED_ARTIFACTS = {
    "grounding_report": "grounding_release_report.json",
    "annotation_signoff": "annotation_signoff.json",
    "calibration_report": "calibration_report.json",
    "live_provider_report": "live_provider_report.json",
    "performance_report": "performance_report.json",
    "security_report": "security_report.json",
    "deployment_report": "deployment_smoke_report.json",
    "rollback_report": "rollback_report.json",
    "release_notes": "release_notes.md",
}

WEIGHTS = {
    "core_grounding": 25,
    "citation_abstention": 20,
    "benchmark": 15,
    "calibration": 10,
    "adversarial": 10,
    "performance": 10,
    "operations_security": 5,
    "documentation": 5,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_fingerprint(root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.strip())
    return commit, dirty


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def validate_annotation_signoff(value: dict[str, Any], benchmark_sha256: str) -> list[str]:
    errors: list[str] = []
    if value.get("status") != "approved":
        errors.append("annotation_not_approved")
    if value.get("benchmark_sha256") != benchmark_sha256:
        errors.append("annotation_benchmark_checksum_mismatch")
    for field, expected in (("records_total", 400), ("records_reviewed", 400), ("records_approved", 400)):
        if value.get(field) != expected:
            errors.append(f"annotation_{field}_must_equal_{expected}")
    for field in ("split_leakage", "missing_gold_evidence", "missing_abstention_reason"):
        if value.get(field) != 0:
            errors.append(f"annotation_{field}_nonzero")
    creators = {str(item).strip() for item in value.get("creator_ids", []) if str(item).strip()}
    reviewers = value.get("reviewers")
    if not creators:
        errors.append("annotation_creator_ids_missing")
    if not isinstance(reviewers, list) or not reviewers:
        errors.append("annotation_reviewers_missing")
        reviewers = []
    reviewed = 0
    reviewer_ids: set[str] = set()
    for index, reviewer in enumerate(reviewers):
        if not isinstance(reviewer, dict):
            errors.append(f"annotation_reviewer_{index}_invalid")
            continue
        reviewer_id = str(reviewer.get("id", "")).strip()
        reviewer_ids.add(reviewer_id)
        reviewed += int(reviewer.get("records_reviewed", 0) or 0)
        if not reviewer_id or not reviewer.get("independent"):
            errors.append(f"annotation_reviewer_{index}_not_independent")
        if not str(reviewer.get("attestation", "")).strip() or not str(reviewer.get("signed_at", "")).strip():
            errors.append(f"annotation_reviewer_{index}_attestation_missing")
    if creators & reviewer_ids:
        errors.append("annotation_creator_reviewer_overlap")
    if reviewed < 400:
        errors.append("annotation_reviewed_count_below_400")
    return errors


def _require_pass(report: dict[str, Any], name: str, fields: tuple[str, ...]) -> list[str]:
    errors = []
    if report.get("status") != "pass":
        errors.append(f"{name}_status_not_pass")
    for field in fields:
        if report.get(field) is not True:
            errors.append(f"{name}_{field}_not_pass")
    return errors


def validate_package(package_dir: Path, *, root: Path | None = None,
                     check_repository: bool = True) -> dict[str, Any]:
    root = (root or package_dir.parents[1]).resolve()
    errors: list[str] = []
    manifest_path = package_dir / "release_manifest.json"
    if not manifest_path.is_file():
        return {"status": "fail", "score": 0.0, "errors": ["release_manifest_missing"], "gates": {}}
    manifest = _json(manifest_path)
    if manifest.get("phase") != "5":
        errors.append("manifest_phase_invalid")
    if not str(manifest.get("release_candidate", "")).startswith("phase5-rc"):
        errors.append("release_candidate_invalid")
    if manifest.get("thresholds_frozen") is not True:
        errors.append("thresholds_not_frozen")
    if manifest.get("schema_version") != "grounding-public-v2":
        errors.append("manifest_schema_version_invalid")
    if manifest.get("policy_version") != "grounding-v1":
        errors.append("manifest_policy_version_invalid")
    runtime = manifest.get("runtime", {})
    if runtime.get("implementation") != platform.python_implementation():
        errors.append("runtime_implementation_mismatch")
    if runtime.get("python") != platform.python_version():
        errors.append("runtime_python_version_mismatch")
    lock = manifest.get("dependency_lock", {})
    lock_path = root / str(lock.get("path", "uv.lock"))
    if not lock_path.is_file() or lock.get("sha256") != sha256_file(lock_path):
        errors.append("dependency_lock_checksum_mismatch")
    threshold_path = root / "configs/grounding_release.json"
    if not threshold_path.is_file() or manifest.get("thresholds_sha256") != sha256_file(threshold_path):
        errors.append("thresholds_checksum_mismatch")
    benchmark_path = root / "data/benchmark/grounding_reviewed.jsonl"
    if not benchmark_path.is_file() or manifest.get("benchmark_sha256") != sha256_file(benchmark_path):
        errors.append("benchmark_source_checksum_mismatch")
    if check_repository:
        commit, dirty = git_fingerprint(root)
        if manifest.get("commit") != commit:
            errors.append("manifest_commit_mismatch")
        if dirty:
            errors.append("working_tree_dirty")

    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    loaded: dict[str, Any] = {}
    for name, default_name in REQUIRED_ARTIFACTS.items():
        entry = artifacts.get(name)
        if not isinstance(entry, dict):
            errors.append(f"artifact_{name}_missing")
            continue
        relative = entry.get("path", default_name)
        path = package_dir / str(relative)
        if not path.is_file():
            errors.append(f"artifact_{name}_file_missing")
            continue
        actual = sha256_file(path)
        if entry.get("sha256") != actual:
            errors.append(f"artifact_{name}_checksum_mismatch")
        if path.suffix == ".json":
            try:
                loaded[name] = _json(path)
            except (OSError, ValueError, json.JSONDecodeError):
                errors.append(f"artifact_{name}_json_invalid")

    benchmark_sha = str(manifest.get("benchmark_sha256", ""))
    calibration_sha = str(manifest.get("calibration_sha256", ""))
    grounding = loaded.get("grounding_report", {})
    grounding_errors = validate_grounding_report(grounding) if grounding else ["grounding_report_unreadable"]
    errors.extend(f"grounding_{item}" for item in grounding_errors)
    if grounding.get("benchmark_sha256") != benchmark_sha:
        errors.append("grounding_benchmark_checksum_mismatch")
    if grounding.get("calibration_artifact_sha256") != calibration_sha:
        errors.append("grounding_calibration_checksum_mismatch")
    if grounding.get("metadata", {}).get("commit") != manifest.get("commit"):
        errors.append("grounding_commit_mismatch")

    signoff_errors = validate_annotation_signoff(loaded.get("annotation_signoff", {}), benchmark_sha)
    errors.extend(signoff_errors)
    calibration = loaded.get("calibration_report", {})
    if calibration.get("fit_split") != "dev":
        errors.append("calibration_fit_split_not_dev")
    if calibration.get("benchmark_sha256") != benchmark_sha:
        errors.append("calibration_benchmark_checksum_mismatch")
    if calibration.get("artifact_sha256") != calibration_sha:
        errors.append("calibration_artifact_checksum_mismatch")

    live_errors = _require_pass(loaded.get("live_provider_report", {}), "live_provider", (
        "schema_valid", "citations_valid", "unsupported_claims_zero", "secret_leakage_zero"))
    performance_errors = _require_pass(loaded.get("performance_report", {}), "performance", (
        "p95_gate", "memory_leak_zero", "request_loss_zero", "single_flight"))
    security_errors = _require_pass(loaded.get("security_report", {}), "security", (
        "secret_scan", "upload_security", "log_redaction", "prompt_injection"))
    deployment_errors = _require_pass(loaded.get("deployment_report", {}), "deployment", (
        "deployment_smoke", "readiness", "liveness", "recovery"))
    if loaded.get("deployment_report", {}).get("environment") not in {"staging", "production"}:
        deployment_errors.append("deployment_environment_not_staging_or_production")
    rollback_errors = _require_pass(loaded.get("rollback_report", {}), "rollback", (
        "rollback", "old_index_load", "metadata_preserved", "citation_valid_after_rollback"))
    if loaded.get("rollback_report", {}).get("environment") not in {"staging", "production"}:
        rollback_errors.append("rollback_environment_not_staging_or_production")
    errors.extend(live_errors + performance_errors + security_errors + deployment_errors + rollback_errors)

    adversarial = manifest.get("verification", {}).get("adversarial") if isinstance(manifest.get("verification"), dict) else None
    if not isinstance(adversarial, dict) or adversarial.get("cases", 0) < 50 or adversarial.get("pass_rate") != 1.0:
        errors.append("adversarial_gate_not_proven")
    docs_ok = bool(loaded.get("release_notes") is not None or (package_dir / "release_notes.md").is_file())
    gates = {
        "core_grounding": not grounding_errors,
        "citation_abstention": not grounding_errors,
        "benchmark": not signoff_errors,
        "calibration": not any(item.startswith("calibration_") for item in errors),
        "adversarial": "adversarial_gate_not_proven" not in errors,
        "performance": not performance_errors,
        "operations_security": not (live_errors or security_errors or deployment_errors or rollback_errors),
        "documentation": docs_ok,
    }
    score = round(sum(WEIGHTS[name] for name, passed in gates.items() if passed) / 10, 1)
    unique_errors = list(dict.fromkeys(errors))
    if unique_errors and score >= 10.0:
        score = 9.9
    return {"status": "pass" if not unique_errors else "fail", "score": score,
            "errors": unique_errors, "gates": gates}


def build_manifest(package_dir: Path, *, root: Path, release_candidate: str,
                   benchmark: Path, calibration: Path, config: Path,
                   verification: dict[str, Any] | None = None) -> dict[str, Any]:
    commit, dirty = git_fingerprint(root)
    if dirty:
        raise ValueError("working tree must be clean before release evidence is generated")
    settings = _json(config)
    calibration_value = _json(calibration)
    artifacts = {}
    for name, filename in REQUIRED_ARTIFACTS.items():
        path = package_dir / filename
        if not path.is_file():
            raise ValueError(f"required artifact missing: {filename}")
        artifacts[name] = {"path": filename, "sha256": sha256_file(path)}
    return {
        "phase": "5", "release_candidate": release_candidate, "commit": commit,
        "benchmark_sha256": sha256_file(benchmark),
        "calibration_sha256": calibration_value.get("artifact_sha256"),
        "calibration_file_sha256": sha256_file(calibration),
        "policy_version": settings["policy_version"],
        "schema_version": settings["schema_version"],
        "thresholds_frozen": settings.get("thresholds_frozen") is True,
        "thresholds_sha256": sha256_file(config), "artifacts": artifacts,
        "runtime": {"implementation": platform.python_implementation(),
                    "python": platform.python_version(), "executable": Path(sys.executable).name},
        "dependency_lock": {"path": "uv.lock", "sha256": sha256_file(root / "uv.lock")},
        "verification": verification or {},
    }
