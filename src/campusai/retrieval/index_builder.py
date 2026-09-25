"""Build and persist all retrieval indexes for one ingested document."""

from __future__ import annotations

from pathlib import Path
import shutil
import re
import json
import hashlib
import os
import tempfile
import time

from ..schemas import Document
from .bm25_index import BM25Index
from .dense_index import DenseIndex, SCHEMA_VERSION, corpus_hash


def chunk_records(document: Document) -> list[dict]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "page": chunk.page,
            "page_range": list(chunk.page_range or (chunk.page, chunk.page)),
            "content": chunk.content,
            "content_type": chunk.content_type,
            "heading_path": chunk.heading_path,
            "metadata": {
                **chunk.metadata,
                "heading_path": chunk.heading_path,
                "page_range": list(chunk.page_range or (chunk.page, chunk.page)),
            },
        }
        for chunk in document.chunks
    ]


def build_document_indexes(
    document: Document,
    index_dir: str | Path,
    dense_model: str = "fallback-hash-256",
    device: str = "cpu",
    batch_size: int = 8,
) -> Path:
    target = Path(index_dir) / document.doc_id
    target.mkdir(parents=True, exist_ok=True)
    items = chunk_records(document)
    BM25Index(items, document.language).save(target / "bm25.json")
    dense = DenseIndex(items, dense_model, device=device, batch_size=batch_size)
    dense.build(items, corpus_id=Path(index_dir).name, document_id=document.doc_id)
    dense.save(target / "dense.json")
    _write_corpus_manifest(Path(index_dir), document.doc_id, items, dense.manifest)
    return target


def _write_corpus_manifest(root: Path, doc_id: str, items: list[dict], dense_manifest: dict) -> None:
    """Atomically write a fingerprint for every complete document snapshot."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / "manifest.json"
    document_manifests = []
    for document_root in sorted(root.iterdir(), key=lambda candidate: candidate.name):
        dense_path = document_root / "dense.json"
        if not document_root.is_dir() or not dense_path.is_file():
            continue
        try:
            data = json.loads(dense_path.read_text(encoding="utf-8"))
            manifest = data.get("manifest", {})
        except (OSError, json.JSONDecodeError):
            continue
        document_manifests.append({
            "document_id": document_root.name,
            "corpus_hash": manifest.get("corpus_hash"),
            "item_count": manifest.get("item_count"),
        })
    corpus_fingerprint = hashlib.sha256(
        json.dumps(document_manifests, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "index_type": "corpus",
        "corpus_id": root.name,
        "model_name": dense_manifest.get("model_name"),
        "model_revision": dense_manifest.get("model_revision"),
        "embedding_dimension": dense_manifest.get("embedding_dimension"),
        "updated_at": time.time(),
        "documents": [entry["document_id"] for entry in document_manifests],
        "document_manifests": document_manifests,
        "corpus_hash": corpus_fingerprint,
    }
    fd, temporary = tempfile.mkstemp(prefix="manifest.", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def remove_document_from_index(doc_id: str, index_dir: str | Path) -> bool:
    """Remove all BM25/dense artifacts for one document."""
    if not re.fullmatch(r"[0-9a-f]{64}|[A-Za-z0-9_.-]+", str(doc_id)):
        raise ValueError("invalid document id")
    root = Path(index_dir).resolve()
    target = (root / doc_id).resolve()
    target.relative_to(root)
    if not target.exists():
        return True
    shutil.rmtree(target)
    return not target.exists()
