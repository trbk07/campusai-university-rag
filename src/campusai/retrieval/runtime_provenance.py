"""Bind runtime code and installed inference dependencies without evaluation IO."""
from __future__ import annotations
import hashlib
import json
from importlib import metadata
from pathlib import Path
import platform

DEPENDENCIES = ("torch", "sentence-transformers", "transformers", "tokenizers", "numpy",
                "safetensors", "huggingface-hub", "fastembed", "onnxruntime", "psutil")


def runtime_description() -> dict:
    versions = {}
    for name in DEPENDENCIES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "system": platform.system(), "machine": platform.machine(), "dependencies": versions}


def runtime_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    files = sorted(root.rglob("*.py"), key=lambda path: path.relative_to(root).as_posix())
    manifest = [(path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                for path in files if "__pycache__" not in path.parts]
    return hashlib.sha256(json.dumps({"code": manifest, "environment": runtime_description()},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
