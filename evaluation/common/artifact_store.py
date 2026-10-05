"""Hash-verified local/offline evidence storage; summaries never replace raw data."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "evaluation/artifacts/manifest.json"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(value: str) -> Path:
    if (not isinstance(value, str) or not value or Path(value).is_absolute()
            or PureWindowsPath(value).drive or PureWindowsPath(value).root
            or ".." in PureWindowsPath(value).parts or ".." in Path(value).parts):
        raise ValueError("unsafe artifact path")
    return Path(value)


def entries() -> dict:
    if not MANIFEST.is_file():
        return {}
    record = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if record.get("schema_version") != 1 or not isinstance(record.get("artifacts"), dict):
        raise ValueError("invalid artifact catalog")
    return record["artifacts"]


def store_root() -> Path:
    """A downloaded artifact bundle can live outside the checkout."""
    return Path(os.environ.get("CAMPUSAI_ARTIFACT_ROOT", str(ROOT / ".local_artifacts"))).resolve()


def resolve_artifact(path: str | Path) -> Path:
    requested = Path(path)
    absolute = requested.resolve()
    # Ordinary files, including test fixtures and fresh measurements, keep
    # their existing semantics. Hash bindings are checked by their consumers.
    if requested.is_file():
        return requested
    if not absolute.is_relative_to(ROOT.resolve()):
        raise FileNotFoundError(requested)
    key = absolute.relative_to(ROOT.resolve()).as_posix()
    record = entries().get(key)
    if record is None:
        raise FileNotFoundError(requested)
    digest = record["sha256"]
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)):
        raise ValueError("invalid raw artifact SHA256")
    root = store_root()
    blob = (root / safe_relative(record["local_or_external_uri"])).resolve()
    if not blob.is_relative_to(root):
        raise ValueError("artifact escapes local store")
    # Even a previous materialization does not excuse missing/corrupt storage.
    if (file_sha256(blob) != record["storage_sha256"]
            or blob.stat().st_size != record["storage_bytes"]):
        raise ValueError("stored artifact hash/size mismatch: " + key)
    cache = root / "resolved" / digest / Path(key).name
    if cache.is_file():
        if cache.stat().st_size != record["bytes"] or file_sha256(cache) != digest:
            raise ValueError("materialized artifact hash/size mismatch: " + key)
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=cache.parent, prefix=".resolve-")
    os.close(descriptor)
    temporary = Path(name)
    try:
        if record.get("encoding") != "gzip":
            raise ValueError("unsupported artifact encoding")
        with gzip.open(blob, "rb") as source, temporary.open("wb") as target:
            shutil.copyfileobj(source, target)
        if temporary.stat().st_size != record["bytes"] or file_sha256(temporary) != digest:
            raise ValueError("raw artifact hash/size mismatch: " + key)
        os.replace(temporary, cache)
    finally:
        temporary.unlink(missing_ok=True)
    return cache


def artifact_paths(directory: Path, pattern: str) -> list[Path]:
    """Enumerate physical and catalogued receipts with their logical paths."""
    paths = set(directory.glob(pattern))
    absolute = directory.resolve()
    if absolute.is_relative_to(ROOT.resolve()):
        prefix = absolute.relative_to(ROOT.resolve())
        for key in entries():
            relative = safe_relative(key)
            if relative.parent == prefix and relative.match(pattern):
                paths.add(directory / relative.name)
    return sorted(paths)
