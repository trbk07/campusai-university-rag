"""Shared provenance and hashing helpers for ingestion artifacts."""
from hashlib import sha256
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a file without loading it all in memory."""
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_artifacts(root: str | Path, manifest: dict) -> list[str]:
    """Validate manifest-referenced artifacts and reject orphan files.

    Returns explicit errors; callers must not publish a run with any error.
    """
    base = Path(root)
    errors: list[str] = []
    referenced: set[str] = set()
    for artifact in manifest.get("artifacts", []):
        name = str(artifact.get("path", ""))
        relative = Path(name)
        if not name or relative.is_absolute() or ".." in relative.parts:
            errors.append(f"invalid artifact path: {name}")
            continue
        referenced.add(name)
        path = base / name
        if not path.is_file():
            errors.append(f"missing artifact: {name}")
            continue
        if int(artifact.get("bytes", -1)) != path.stat().st_size:
            errors.append(f"size mismatch: {name}")
        if artifact.get("sha256") != sha256_file(path):
            errors.append(f"hash mismatch: {name}")
    actual = {path.relative_to(base).as_posix() for path in base.rglob("*")
              if path.is_file() and path.name not in {"run_manifest.json"}}
    errors.extend(f"orphan artifact: {name}" for name in sorted(actual - referenced))
    return errors
