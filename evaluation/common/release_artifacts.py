"""Shared artifact IO and immutable Phase 7 evidence bindings."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess

from evaluation.common.artifact_store import resolve_artifact


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with resolve_artifact(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    value = json.loads(resolve_artifact(path).read_text(encoding="utf-8"), parse_constant=_reject_constant, parse_float=_finite_float)
    if not isinstance(value, dict):
        raise ValueError("artifact must be an object")
    return value


def _reject_constant(value: str):
    raise ValueError(f"non-finite JSON constant: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number")
    return parsed


def assert_tuning_allowed(results_dir: Path, *, route: bool = False) -> None:
    """A held-out run consumes a study, even if inference or a gate fails."""
    locks = [results_dir / "reranker_policy_freeze.json"]
    if route:
        locks.append(results_dir / "reranker_route_freeze.json")
    if any(path.exists() for path in locks):
        raise ValueError("held-out evaluation already started; use a new study/results directory and new reviewed data")


def freeze_before_evaluation(results_dir: Path, paths: dict[str, Path], *, route: bool = False) -> dict:
    """Persist bindings before opening held-out rows; permit identical reruns only."""
    target = results_dir / ("reranker_route_freeze.json" if route else "reranker_policy_freeze.json")
    bindings = {name: sha256(path) for name, path in paths.items()}
    if target.exists():
        if read_json(target).get("artifact_sha256") != bindings:
            raise ValueError("frozen study inputs changed after held-out evaluation")
        return read_json(target)
    from datetime import datetime, timezone
    record = {"schema_version": 1, "phase": 7, "status": "pass",
              "heldout_started_at": datetime.now(timezone.utc).isoformat(), "artifact_sha256": bindings}
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents a second process from silently replacing the lock.
    with target.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return record


def policy_bindings(results_dir: Path) -> dict:
    """Shared post-calibration lineage, independent of the measurement type."""
    calibration = read_json(results_dir / "reranker_score_calibration.json")
    return {"route_calibration_sha256": sha256(results_dir / "hard_query_route_calibration.json"),
            "training_split_sha256": calibration["training_split_sha256"],
            "human_benchmark_sha256": read_json(results_dir / "human_benchmark_manifest.json")["dataset_sha256"]}


def source_identity(root: Path) -> dict:
    """Identify the physical source tree and runtime used for an evaluation.

    Hash inputs directly instead of trusting an older report to supply the
    identity for the code that produced it. Generated results and datasets are
    bound by their own artifact hashes and are excluded here.
    """
    root = Path(root).resolve()
    files = set()
    for directory in ("src", "evaluation", "scripts", "tests"):
        base = root / directory
        if base.is_dir():
            files.update(path for path in base.rglob("*.py")
                         if path.is_file() and "__pycache__" not in path.parts)
    config_dir = root / "configs"
    if config_dir.is_dir():
        files.update(path for path in config_dir.rglob("*")
                     if path.is_file() and path.suffix.lower() in {".json", ".toml", ".yaml", ".yml"}
                     and path.name != "gemini.yaml")
    manifests = {"pyproject.toml", "requirements.txt", "requirements-dev.txt", "uv.lock", "poetry.lock"}
    files.update(root / name for name in manifests if (root / name).is_file())
    source_digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        source_digest.update(len(relative).to_bytes(4, "big"))
        source_digest.update(relative)
        content_digest = hashlib.sha256(path.read_bytes()).digest()
        source_digest.update(content_digest)
    from campusai.retrieval.runtime_provenance import runtime_sha256
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "source_sha256": source_digest.hexdigest(), "runtime_sha256": runtime_sha256()}


def require_previous_gates(gate: str, results_dir: Path = Path("evaluation/results"), *,
                           index_dir: Path = Path(".tmp/hybrid-index"),
                           benchmark_dir: Path = Path("data/benchmark")) -> None:
    """Enforce stage order before executing an expensive release measurement."""
    from evaluation.reranker.validate_reranker_release import default_args, validate
    args = default_args(results_dir)
    args.index_dir, args.benchmark_dir = index_dir, benchmark_dir
    args.through = f"M{max(0, int(gate[1:]) - 1)}"
    report = validate(args)
    previous = [f"M{index}" for index in range(int(gate[1:]))]
    blocked = [name for name in previous if report["gates"][name]["status"] != "PASS"]
    if blocked:
        raise ValueError("previous gates have not passed: " + ", ".join(blocked))


def verify_index_files(index_dir: Path) -> bool:
    """Validate physical BM25 artifacts against the frozen corpus manifest."""
    try:
        manifest = read_json(index_dir / "manifest.json")
        entries = manifest["document_manifests"]
        docs = manifest["documents"]
        if {entry["document_id"] for entry in entries} != set(docs):
            return False
        return all(isinstance(entry["document_id"], str)
                   and Path(entry["document_id"]).name == entry["document_id"]
                   and entry["document_id"] not in {".", ".."}
                   and sha256(index_dir / entry["document_id"] / "bm25.json") == entry["bm25_sha256"]
                   for entry in entries)
    except (OSError, KeyError, TypeError, ValueError):
        return False
