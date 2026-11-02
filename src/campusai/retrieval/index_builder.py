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
from collections import OrderedDict
from threading import RLock

from ..schemas import Document
from .bm25_index import BM25Index
from .dense_index import DenseIndex, SCHEMA_VERSION, corpus_hash

_DOCUMENT_MANIFESTS = OrderedDict()
_DOCUMENT_MANIFEST_LOCK = RLock()
_DOCUMENT_MANIFEST_LIMIT = 128


def _file_identity(path):
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _document_manifest(document_root):
    """Cache small manifest facts, never vectors, against both live index files."""
    dense, bm25 = document_root/'dense.json', document_root/'bm25.json'
    identity = (_file_identity(dense), _file_identity(bm25))
    key = str(document_root.resolve())
    with _DOCUMENT_MANIFEST_LOCK:
        cached = _DOCUMENT_MANIFESTS.get(key)
        if cached is not None and cached[0] == identity:
            _DOCUMENT_MANIFESTS.move_to_end(key)
            return dict(cached[1])
    manifest = json.loads(dense.read_text(encoding='utf-8')).get('manifest', {})
    record = {'document_id':document_root.name, 'corpus_hash':manifest.get('corpus_hash'),
        'item_count':manifest.get('item_count'),
        'bm25_sha256':hashlib.sha256(bm25.read_bytes()).hexdigest() if identity[1] is not None else None}
    if identity != (_file_identity(dense), _file_identity(bm25)):
        raise OSError('index changed while reading its corpus manifest')
    with _DOCUMENT_MANIFEST_LOCK:
        _DOCUMENT_MANIFESTS[key] = (identity, dict(record))
        _DOCUMENT_MANIFESTS.move_to_end(key)
        while len(_DOCUMENT_MANIFESTS) > _DOCUMENT_MANIFEST_LIMIT:
            _DOCUMENT_MANIFESTS.popitem(last=False)
    return record


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
                **document.metadata,
                **chunk.metadata,
                "source_name": Path(document.source_path).name,
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
    model_revision: str = "1",
    corpus_id: str | None = None,
    previous_dense: DenseIndex | None = None,
) -> Path:
    target = Path(index_dir) / document.doc_id
    target.mkdir(parents=True, exist_ok=True)
    items = chunk_records(document)
    BM25Index(items, document.language).save(target / "bm25.json")
    dense = DenseIndex(items, dense_model, device=device, batch_size=batch_size,model_revision=model_revision)
    dense.build(items, corpus_id=corpus_id or Path(index_dir).name, document_id=document.doc_id, previous=previous_dense)
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
            record = _document_manifest(document_root)
        except (OSError, json.JSONDecodeError):
            continue
        document_manifests.append(record)
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
