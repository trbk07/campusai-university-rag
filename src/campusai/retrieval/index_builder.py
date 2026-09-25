"""Build and persist all retrieval indexes for one ingested document."""

from __future__ import annotations

from pathlib import Path
import shutil
import re

from ..schemas import Document
from .bm25_index import BM25Index
from .dense_index import DenseIndex


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
    dense.build(items)
    dense.save(target / "dense.json")
    return target


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
