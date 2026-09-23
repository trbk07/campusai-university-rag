"""Orchestrate validation, parsing, metadata detection, and persistence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

from ..schemas import Document
from .chunker import make_chunks
from .docling_parser import parse_pdf
from .metadata_detector import detect_metadata
from .table_extractor import extract_tables
from .validate import ValidationError, validate_pdf
from ..documents.registry import DocumentRegistry


ProgressCallback = Callable[[str, float], None]


def _sha256_file(path: Path) -> str:
    """Return the content hash used as the stable document identifier."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _default_progress(_stage: str, _value: float) -> None:
    """Default callback used when the caller does not need progress updates."""


def _save_table(table, output_dir: Path) -> None:
    """Save a table when possible and always save its schema."""

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd
    except ImportError:
        pd = None

    if pd is not None:
        dataframe = pd.DataFrame(table.rows, columns=table.headers)
        parquet_path = tables_dir / f"{table.table_id}.parquet"
        try:
            dataframe.to_parquet(parquet_path, index=False)
        except (ImportError, ValueError):
            # Parquet is optional; the JSON schema remains the durable output.
            pass

    schema_path = tables_dir / f"{table.table_id}.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(
        json.dumps(table.schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ingest_document(
    path: str | Path,
    store_dir: str | Path = "data/store",
    max_mb: int = 50,
    max_pages: int = 250,
    progress: ProgressCallback | None = None,
    registry: DocumentRegistry | None = None,
) -> Document:
    """Ingest one PDF and reuse its stored result on repeated uploads."""

    pdf_path = Path(path)
    registry = registry or DocumentRegistry(Path(store_dir) / "registry.json")
    validation = validate_pdf(pdf_path, max_mb=max_mb, max_pages=max_pages)
    if not validation.has_text:
        raise ValidationError(
            "PDF không có lớp text có thể đọc; đây có thể là PDF scan. "
            "Hãy chạy OCR trước khi ingest (hoặc cung cấp bản PDF có text)."
        )
    document_id = _sha256_file(pdf_path)

    output_dir = Path(store_dir) / document_id
    metadata_path = output_dir / "meta.json"

    if metadata_path.exists():
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        document = Document.from_dict(data)
        document.cached = True
        registry.add(document)
        return document

    output_dir.mkdir(parents=True, exist_ok=True)
    report_progress = progress or _default_progress
    report_progress("parse", 0.0)

    pages = parse_pdf(pdf_path)
    report_progress("parse", 1.0)
    full_text = "\n\n".join(
        f"## Page {page['page']}\n{page['text']}" for page in pages
    )
    metadata = detect_metadata(full_text)
    tables = extract_tables(pages, document_id)
    for table in tables:
        table.schema.update(
            {
                "units": metadata.get("units", []),
                "currency": metadata.get("currency"),
                "fiscal_years": metadata.get("fiscal_years", []),
                "consolidation": metadata.get("consolidation"),
            }
        )
    chunks = make_chunks(pages, document_id, metadata, tables)
    report_progress("extract", 1.0)

    document = Document(
        doc_id=document_id,
        source_path=str(pdf_path.resolve()),
        page_count=validation.pages,
        language=metadata.get("language"),
        metadata=metadata,
        chunks=chunks,
        tables=tables,
    )

    parsed_path = output_dir / "parsed.md"
    parsed_path.write_text(full_text, encoding="utf-8")

    metadata_path.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for table in tables:
        _save_table(table, output_dir)
    report_progress("persist", 1.0)

    registry.add(document)

    report_progress("done", 1.0)
    return document
