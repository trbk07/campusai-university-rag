"""Create a reproducibility fingerprint for a Phase 5 evaluation run."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(list(args), cwd=root, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/grounding_baseline.json"))
    parser.add_argument("--test-command", default=".venv\\Scripts\\python.exe -m pytest -q")
    parser.add_argument("--evaluation-command", default=".venv\\Scripts\\python.exe evaluation\\run_grounding_eval.py --mode runtime")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    benchmark = (root / args.benchmark).resolve()
    lock = root / "uv.lock"
    status = command(root, "git", "status", "--porcelain")
    report = {
        "commit": command(root, "git", "rev-parse", "HEAD") or "working-tree",
        "working_tree": bool(status),
        "benchmark": str(benchmark.relative_to(root)),
        "benchmark_sha256": sha256(benchmark),
        "python_version": platform.python_version(),
        "dependency_lock": {"path": str(lock.relative_to(root)), "sha256": sha256(lock)} if lock.is_file() else None,
        "test_command": args.test_command,
        "evaluation_command": args.evaluation_command,
        "metrics": {},
        "known_failures": [],
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
