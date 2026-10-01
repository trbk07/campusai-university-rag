"""Hash installed runtime code without depending on evaluation tooling."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def runtime_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    files = sorted(root.rglob("*.py"))
    manifest = [(path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                for path in files if "__pycache__" not in path.parts]
    return hashlib.sha256(json.dumps(manifest, separators=(",", ":")).encode()).hexdigest()
