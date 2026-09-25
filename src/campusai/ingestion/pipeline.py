"""Orchestrate validation, parsing, metadata detection, and persistence."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Callable

from ..schemas import Document
from .chunker import make_chunks
from .docling_parser import parse_pdf
from .metadata_detector import detect_metadata
from .ocr import OCRLimitExceeded, OCRUnavailable, ocr_pdf
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
    max_pages: int = 218,
    progress: ProgressCallback | None = None,
    registry: DocumentRegistry | None = None,
    enable_ocr: bool = False,
    ocr_max_pages: int = 50,
    ocr_timeout_seconds: float = 120.0,
) -> Document:
    """Ingest one PDF and reuse its stored result on repeated uploads."""

    pdf_path = Path(path)
    registry = registry or DocumentRegistry(Path(store_dir) / "registry.json")
    # Parsing below already reads every page. Deferring validation's text probe
    # avoids a complete second pass over the PDF on first ingestion.
    validation = validate_pdf(
        pdf_path,
        max_mb=max_mb,
        max_pages=max_pages,
        check_text=False,
    )
    document_id = _sha256_file(pdf_path)

    output_dir = Path(store_dir) / document_id
    metadata_path = output_dir / "meta.json"

    if metadata_path.exists():
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        document = Document.from_dict(data)
        if enable_ocr and document.status == "review_required" and document.review_reason in {
            "ocr_required",
            "ocr_unavailable",
        }:
            # An earlier default ingestion may have persisted a fail-closed
            # scan review. Explicit OCR opt-in must be allowed to reprocess it.
            shutil.rmtree(output_dir, ignore_errors=True)
        else:
            document.cached = True
            registry.add(document)
            return document

    output_dir.mkdir(parents=True, exist_ok=True)
    report_progress = progress or _default_progress
    report_progress("validating", 1.0)
    report_progress("parsing", 0.0)

    pages = parse_pdf(
        pdf_path,
        progress=lambda value: report_progress("parsing", value),
    )
    report_progress("parsing", 1.0)
    ocr_info = None
    if not any(str(page.get("text", "")).strip() for page in pages) and enable_ocr:
        report_progress("ocr", 0.0)
        try:
            ocr_result = ocr_pdf(
                pdf_path,
                max_pages=ocr_max_pages,
                timeout_seconds=ocr_timeout_seconds,
            )
            pages = ocr_result.pages
            ocr_info = {
                "engine": ocr_result.engine,
                "average_confidence": ocr_result.average_confidence,
                "elapsed_seconds": ocr_result.elapsed_seconds,
                "pages": len(ocr_result.pages),
            }
            report_progress("ocr", 1.0)
        except (OCRLimitExceeded, OCRUnavailable) as error:
            metadata = detect_metadata("")
            metadata.update(
                {
                    "source_name": pdf_path.name,
                    "source_hash": document_id,
                    "parser_version": "pymupdf-text-v1",
                    "chunker_version": "structure-v2",
                    "schema_version": 1,
                    "status": "review_required",
                    "review_reason": "ocr_unavailable",
                    "warnings": ["no_extractable_text", "ocr_unavailable", str(error)],
                }
            )
            document = Document(
                doc_id=document_id,
                source_path=str(pdf_path.resolve()),
                page_count=validation.pages,
                language=None,
                metadata=metadata,
                chunks=[],
                tables=[],
                status="review_required",
                review_reason="ocr_unavailable",
            )
            metadata_path.write_text(
                json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            registry.add(document)
            report_progress("review_required", 1.0)
            return document
    if not any(str(page.get("text", "")).strip() for page in pages):
        report_progress("detecting_metadata", 0.0)
        metadata = detect_metadata("")
        metadata.update(
            {
                "source_name": pdf_path.name,
                "source_hash": document_id,
                "parser_version": "pymupdf-text-v1",
                "chunker_version": "structure-v2",
                "schema_version": 1,
                "status": "review_required",
                "review_reason": "ocr_required",
                "warnings": ["no_extractable_text", "ocr_required"],
            }
        )
        document = Document(
            doc_id=document_id,
            source_path=str(pdf_path.resolve()),
            page_count=validation.pages,
            language=None,
            metadata=metadata,
            chunks=[],
            tables=[],
            status="review_required",
            review_reason="ocr_required",
        )
        metadata_path.write_text(
            json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        registry.add(document)
        report_progress("review_required", 1.0)
        return document
    full_text = "\n\n".join(
        f"## Page {page['page']}\n{page['text']}" for page in pages
    )
    report_progress("detecting_metadata", 0.0)
    metadata = detect_metadata(full_text)
    metadata["source_name"] = pdf_path.name
    metadata["source_hash"] = document_id
    metadata["parser_version"] = "pymupdf-text-v1"
    metadata["chunker_version"] = "structure-v2"
    metadata["schema_version"] = 1
    if ocr_info is not None:
        metadata["ocr"] = ocr_info
        metadata["parser_version"] = "rapidocr-onnx-v1"
        metadata["warnings"] = ["ocr_used"]
    report_progress("detecting_metadata", 1.0)
    report_progress("extracting_tables", 0.0)
    tables = extract_tables(pages, document_id, pdf_path=pdf_path)
    for table in tables:
        table.schema.update(
            {
                "domain": metadata.get("domain", "general"),
                "document_type": metadata.get("document_type", "unknown"),
                "academic_years": metadata.get("academic_years", []),
                "years": metadata.get("years", []),
                "semesters": metadata.get("semesters", []),
                "language": metadata.get("language"),
                "units": metadata.get("units", []),
                "currency": metadata.get("currency"),
            }
        )
    report_progress("extracting_tables", 1.0)
    report_progress("chunking", 0.0)
    chunk_diagnostics: dict = {}
    chunks = make_chunks(pages, document_id, metadata, tables, diagnostics=chunk_diagnostics)
    metadata["chunk_diagnostics"] = chunk_diagnostics
    metadata["warnings"] = validation.warnings
    report_progress("chunking", 1.0)

    document = Document(
        doc_id=document_id,
        source_path=str(pdf_path.resolve()),
        page_count=validation.pages,
        language=metadata.get("language"),
        metadata=metadata,
        chunks=chunks,
        tables=tables,
        status="succeeded",
    )

    report_progress("persisting", 0.0)
    parsed_path = output_dir / "parsed.md"
    parsed_path.write_text(full_text, encoding="utf-8")

    metadata_path.write_text(
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for table in tables:
        _save_table(table, output_dir)
    report_progress("persisting", 1.0)

    registry.add(document)

    report_progress("done", 1.0)
    return document


def delete_document(
    doc_id: str,
    *,
    store_dir: str | Path = "data/store",
    registry: DocumentRegistry | None = None,
) -> bool:
    """Delete every persisted artifact for a document idempotently.

    ``doc_id`` is a SHA-256 identifier, so accepting any other shape would make
    path construction needlessly risky. Index/cache backends can additionally
    remove their own records before or after this storage-level operation.
    """

    if not re.fullmatch(r"[0-9a-f]{64}", str(doc_id)):
        raise ValueError("doc_id phải là SHA-256 hex")
    root = Path(store_dir).resolve()
    registry = registry or DocumentRegistry(root / "registry.json")
    removed = registry.remove(doc_id)
    artifact_dir = (root / doc_id).resolve()
    try:
        artifact_dir.relative_to(root)
    except ValueError as error:
        raise ValueError("artifact path nằm ngoài store root") from error
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    return removed is not None or not artifact_dir.exists()


def delete_document_full(
    doc_id: str,
    *,
    store_dir: str | Path = "data/store",
    index_dir: str | Path | None = None,
    llm_cache=None,
    registry: DocumentRegistry | None = None,
) -> dict[str, bool]:
    """Delete storage artifacts and any per-document retrieval artifacts."""
    result = {"store": delete_document(doc_id, store_dir=store_dir, registry=registry)}
    if index_dir is not None:
        from ..retrieval.index_builder import remove_document_from_index

        result["index"] = remove_document_from_index(doc_id, index_dir)
    if llm_cache is not None:
        # LLM cache keys are provider/query hashes and intentionally contain no
        # doc_id, so there is no safe document-scoped purge operation.
        result["cache"] = bool(getattr(llm_cache, "purge_by_doc_id", lambda _doc_id: False)(doc_id))
    return result
