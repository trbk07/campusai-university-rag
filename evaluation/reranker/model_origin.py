"""Verify a public snapshot receipt against metadata and physical model bytes."""
from __future__ import annotations

import hashlib
from pathlib import Path

from evaluation.common.release_artifacts import read_json, sha256
from campusai.retrieval.cross_encoder_provider import snapshot_sha256


def verified_model_origin(model_dir: Path, receipt_path: Path) -> dict:
    receipt = read_json(receipt_path)
    metadata_path = Path(receipt["metadata_path"])
    if (receipt.get("status") != "PASS_PINNED_PUBLIC_FILE_HASHES"
            or receipt.get("metadata_sha256") != sha256(metadata_path)):
        raise ValueError("unverified model origin receipt")
    metadata = read_json(metadata_path)
    name, revision = receipt["model_name"], receipt["revision"]
    if (metadata.get("id") != name or metadata.get("sha") != revision
            or model_dir.name != revision
            or receipt.get("metadata_url") != f"https://huggingface.co/api/models/{name}/revision/{revision}?blobs=true"):
        raise ValueError("model name/revision differs from upstream receipt")
    upstream = {item["rfilename"]: item for item in metadata["siblings"]}
    origins = {}
    for origin_key, origin in receipt.get("additional_origins", {}).items():
        origin_path = Path(origin["metadata_path"])
        if sha256(origin_path) != origin["metadata_sha256"]:
            raise ValueError("additional origin metadata hash mismatch")
        origin_metadata = read_json(origin_path)
        if (origin_metadata.get("id") != origin["model_name"]
                or origin_metadata.get("sha") != origin["revision"]
                or len(origin["revision"]) != 40
                or any(c not in "0123456789abcdef" for c in origin["revision"])
                or origin.get("metadata_url") != f"https://huggingface.co/api/models/{origin['model_name']}/revision/{origin['revision']}?blobs=true"):
            raise ValueError("additional origin name/revision differs from upstream receipt")
        origins[origin_key] = {item["rfilename"]: item for item in origin_metadata["siblings"]}
    physical = {path.relative_to(model_dir).as_posix(): path for path in model_dir.rglob("*") if path.is_file()}
    if not physical or set(physical) != set(receipt["files"]) or any(path.is_symlink() for path in model_dir.rglob("*")):
        raise ValueError("physical model files differ from verified receipt")
    for filename, path in physical.items():
        digest, size = sha256(path), path.stat().st_size
        recorded = receipt["files"][filename]
        origin_key = recorded.get("origin")
        if origin_key is not None and origin_key not in origins:
            raise ValueError("unknown additional file origin")
        file_upstream = origins[origin_key] if origin_key is not None else upstream
        if filename not in file_upstream:
            raise ValueError("model file missing from pinned upstream origin")
        pinned = file_upstream[filename]
        if (digest != recorded["sha256"] or size != recorded["bytes"] or size != pinned["size"]
                or recorded["upstream_blob"] != pinned["blobId"] or recorded["upstream_lfs"] != pinned.get("lfs")):
            raise ValueError("model file differs from receipt/upstream metadata")
        if pinned.get("lfs"):
            if digest != pinned["lfs"]["sha256"]:
                raise ValueError("model LFS hash mismatch")
        else:
            data = path.read_bytes()
            if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != pinned["blobId"]:
                raise ValueError("model Git blob hash mismatch")
    return {"model_name": name, "revision": revision, "snapshot_sha256": snapshot_sha256(model_dir),
            "receipt_path": receipt_path.as_posix(), "receipt_sha256": sha256(receipt_path),
            "upstream_metadata_sha256": sha256(metadata_path), "upstream_files_verified": True,
            "additional_origins": receipt.get("additional_origins", {})}
