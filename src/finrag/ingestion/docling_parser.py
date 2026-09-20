"""Page-preserving PDF parser boundary.

The current implementation intentionally uses PyMuPDF because it is a small,
deterministic local dependency. The return contract is parser-agnostic, so a
Docling adapter can be added later without changing ingestion consumers.
"""

from __future__ import annotations

from pathlib import Path

import fitz


def parse_pdf(path: str | Path) -> list[dict[str, str | int]]:
    """Extract one text string for every page in the PDF."""

    document = fitz.open(str(path))
    pages: list[dict[str, str | int]] = []

    try:
        for page_number, page in enumerate(document, start=1):
            pages.append(
                {
                    "page": page_number,
                    "text": page.get_text("text"),
                }
            )
    finally:
        document.close()

    return pages
