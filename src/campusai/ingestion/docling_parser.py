"""Optional Docling adapter used by the Task 2 feasibility benchmark.

The production ingestion path keeps the small deterministic PyMuPDF adapter.
Docling is imported lazily so the normal install does not download its parser
stack or model assets.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable

import fitz


class DoclingUnavailable(RuntimeError):
    """Raised when the optional Docling benchmark dependency is absent."""


def parse_pdf(
    path: str | Path,
    progress: Callable[[float], None] | None = None,
) -> list[dict[str, str | int]]:
    """Extract one text string for every page using the local adapter."""

    document = fitz.open(str(path))
    pages: list[dict[str, str | int]] = []
    try:
        total_pages = max(1, len(document))
        for page_number, page in enumerate(document, start=1):
            pages.append({"page": page_number, "text": page.get_text("text")})
            if progress is not None:
                progress(page_number / total_pages)
    finally:
        document.close()
    return pages


def _docling_version() -> str | None:
    try:
        return version("docling")
    except PackageNotFoundError:
        return None


def parse_with_docling(path: str | Path, *, fast: bool = False) -> dict[str, Any]:
    """Convert one PDF and return auditable metrics without writing its text.

    ``fast=True`` disables Docling's table-structure model. It is suitable for
    a quick layout/text preview; the full mode remains available for an
    explicit table-review job.
    """

    try:
        from docling.document_converter import DocumentConverter
    except ImportError as error:  # pragma: no cover - optional dependency
        raise DoclingUnavailable(
            "Docling is not installed; run `uv sync --extra feasibility`."
        ) from error

    # The benchmark corpus includes text-layer PDFs.  Disable OCR for those
    # inputs so the Docling comparison measures layout/table conversion rather
    # than repeatedly rasterizing every page; scan-only PDFs remain represented
    # by the parser's explicit OCR-required status.
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TableFormerMode,
        TableStructureOptions,
    )
    from docling.document_converter import PdfFormatOption

    pipeline_options = PdfPipelineOptions(
        do_ocr=False,
        force_backend_text=True,
        do_picture_classification=False,
        do_picture_description=False,
        do_table_structure=not fast,
        table_structure_options=TableStructureOptions(
            mode=TableFormerMode.FAST,
            do_cell_matching=True,
        ),
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(str(path))
    document = result.document
    pages = len(document.pages) if hasattr(document, "pages") else None
    tables = len(getattr(document, "tables", []) or [])
    pictures = len(getattr(document, "pictures", []) or [])
    markdown_chars = None
    if hasattr(document, "export_to_markdown"):
        markdown_chars = len(document.export_to_markdown())

    return {
        "implementation": "docling",
        "mode": "fast" if fast else "layout_tables",
        "docling_version": _docling_version(),
        "pages": pages,
        "tables": tables,
        "pictures": pictures,
        "markdown_chars": markdown_chars,
    }
