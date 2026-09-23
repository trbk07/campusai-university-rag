"""Optional Docling adapter used by the Task 2 feasibility benchmark.

The production ingestion path keeps the small deterministic PyMuPDF adapter.
Docling is imported lazily so the normal install does not download its parser
stack or model assets.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import fitz


class DoclingUnavailable(RuntimeError):
    """Raised when the optional Docling benchmark dependency is absent."""


def parse_pdf(path: str | Path) -> list[dict[str, str | int]]:
    """Extract one text string for every page using the local adapter."""

    document = fitz.open(str(path))
    pages: list[dict[str, str | int]] = []
    try:
        for page_number, page in enumerate(document, start=1):
            pages.append({"page": page_number, "text": page.get_text("text")})
    finally:
        document.close()
    return pages


def _docling_version() -> str | None:
    try:
        return version("docling")
    except PackageNotFoundError:
        return None


def parse_with_docling(path: str | Path) -> dict[str, Any]:
    """Convert one PDF and return auditable metrics without writing its text."""

    try:
        from docling.document_converter import DocumentConverter
    except ImportError as error:  # pragma: no cover - optional dependency
        raise DoclingUnavailable(
            "Docling is not installed; run `uv sync --extra feasibility`."
        ) from error

    result = DocumentConverter().convert(str(path))
    document = result.document
    pages = len(document.pages) if hasattr(document, "pages") else None
    tables = len(getattr(document, "tables", []) or [])
    pictures = len(getattr(document, "pictures", []) or [])
    markdown_chars = None
    if hasattr(document, "export_to_markdown"):
        markdown_chars = len(document.export_to_markdown())

    return {
        "implementation": "docling",
        "docling_version": _docling_version(),
        "pages": pages,
        "tables": tables,
        "pictures": pictures,
        "markdown_chars": markdown_chars,
    }
