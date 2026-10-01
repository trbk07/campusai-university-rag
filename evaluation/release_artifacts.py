"""Shared artifact IO and immutable Phase 7 evidence bindings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact must be an object")
    return value


def source_identity(root: Path) -> dict:
    # Uncommitted implementation changes cannot be represented by HEAD alone.
    files = sorted(path for directory in ("src", "evaluation", "scripts", "configs")
                   for path in (root / directory).rglob("*")
                   if path.is_file() and "__pycache__" not in path.parts
                   and "results" not in path.relative_to(root).parts)
    digest = hashlib.sha256(json.dumps([(p.relative_to(root).as_posix(), sha256(p)) for p in files],
                                       separators=(",", ":")).encode()).hexdigest()
    from campusai.retrieval.runtime_provenance import runtime_sha256
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "source_sha256": digest, "runtime_sha256": runtime_sha256()}


def require_previous_gates(gate: str, results_dir: Path = Path("evaluation/results"), *,
                           index_dir: Path = Path(".tmp/phase6-index"),
                           benchmark_dir: Path = Path("data/benchmark")) -> None:
    """Enforce stage order before executing an expensive release measurement."""
    from evaluation.validate_reranker_release import default_args, validate
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
