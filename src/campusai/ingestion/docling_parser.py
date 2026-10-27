"""Optional Docling adapter used by the Task 2 feasibility benchmark.

The production ingestion path keeps the small deterministic PyMuPDF adapter.
Docling is imported lazily so the normal install does not download its parser
stack or model assets.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import statistics
from typing import Any, Callable

import fitz

TEXT_COVERAGE_VERSION = 3


def _visible_span(span):
    # Read the installed MuPDF constants: bit positions changed across releases.
    # https://pymupdf.readthedocs.io/en/latest/textpage.html
    flags = span.get('char_flags')
    painted = fitz.mupdf.FZ_STEXT_FILLED | fitz.mupdf.FZ_STEXT_STROKED
    return span.get('alpha', 255) > 0 and (flags is None or bool(flags & painted))


def _page_lines(page):
    lines, layout, ignored, sizes = [], [], 0, []
    flags = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES
    for block in page.get_text('dict', flags=flags).get('blocks', []):
        for line in block.get('lines', []):
            original = line.get('spans', [])
            ignored += sum(bool(str(s.get('text', '')).strip()) for s in original if not _visible_span(s))
            spans = [s for s in original if _visible_span(s)]
            text = ''.join(str(s.get('text', '')) for s in spans).strip()
            if not text or not spans:
                continue
            box = fitz.Rect()
            for span in spans:
                box |= fitz.Rect(span['bbox'])
            size = max(float(s.get('size', 0)) for s in spans)
            sizes.append(size)
            lines.append({'text': text, 'font_size': round(size, 1),
                          'bold': any('bold' in str(s.get('font', '')).lower() for s in spans)})
            layout.append({'text': text, 'bbox': list(line['bbox'] if len(spans) == len(original) else box)})
    return lines, layout, ignored, sizes


def visible_page_text(page):
    """Keep existing bytes for unaffected pages; never quote hidden OCR text."""
    lines, _layout, ignored, _sizes = _page_lines(page)
    return '\n'.join(row['text'] for row in lines) if ignored else page.get_text()


def _visible_characters(page):
    """Character proofs in the rotated MediaBox coordinates used by pdfplumber."""
    crop, media = page.cropbox, page.mediabox
    offsets = {0: (crop.x0, crop.y0), 90: (media.height-crop.y1, crop.x0),
               180: (media.width-crop.x1, media.height-crop.y1),
               270: (crop.y0, media.width-crop.x1)}
    dx, dy = offsets[page.rotation]
    flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
    result = []
    for block in page.get_text('rawdict', flags=flags).get('blocks', []):
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                if _visible_span(span):
                    for char in span.get('chars', []):
                        rect = fitz.Rect(char['bbox']) * page.rotation_matrix + (dx, dy, dx, dy)
                        result.append({'text': char['c'], 'bbox': list(rect)})
    return result


def _uncovered_images(page, native_boxes):
    """Find substantial raster regions without a distributed native text layer.

    A native heading/footer outside an image is not evidence that its body was
    extracted. Small decorative marks do not trigger document-wide OCR. Image
    metadata is inspected without loading compressed image payloads.
    """
    bounds = page.rect * page.derotation_matrix
    uncovered = []
    for image in page.get_image_info():
        region = fitz.Rect(image['bbox']) & bounds
        if region.is_empty or region.get_area() < bounds.get_area() * .02:
            continue
        inside = [box & region for box in native_boxes
                  if box.get_area() and (box & region).get_area() >= box.get_area() * .5]
        envelope = fitz.Rect()
        for box in inside:
            envelope |= box
        if (len(inside) >= 3 and envelope.width >= .8 * region.width
                and envelope.height >= .8 * region.height):
            continue
        if list(region) not in uncovered:
            uncovered.append(list(region))
    return uncovered


class DoclingUnavailable(RuntimeError):
    """Raised when the optional Docling benchmark dependency is absent."""


def parse_pdf(
    path: str | Path,
    progress: Callable[[float], None] | None = None,
) -> list[dict[str, Any]]:
    """Extract page text while preserving lightweight font/layout metadata."""

    document = fitz.open(str(path))
    raw_pages: list[dict[str, Any]] = []
    body_font_sizes: list[float] = []
    try:
        total_pages = max(1, len(document))
        for page_number, page in enumerate(document, start=1):
            lines, native_layout, ignored, sizes = _page_lines(page)
            body_font_sizes.extend(sizes)
            regions = _uncovered_images(page, [fitz.Rect(row['bbox']) for row in native_layout])
            requires_ocr = bool(regions) or not lines and bool(page.get_image_info() or page.get_drawings())
            raw_pages.append({"page": page_number, "lines": lines, "requires_ocr": requires_ocr,
                              'hybrid_layout': native_layout if lines and regions else None,
                              'ocr_regions': regions,
                              **({'ignored_invisible_spans': ignored,
                                  'visible_characters': _visible_characters(page)} if ignored else {})})
            if progress is not None:
                progress(page_number / total_pages)
    finally:
        document.close()
    body_median = statistics.median(body_font_sizes) if body_font_sizes else 0.0
    return [{
        "page": raw["page"],
        "requires_ocr": raw["requires_ocr"],
        "text": "\n".join(line["text"] for line in raw["lines"]),
        "lines_meta": [{**line, "is_larger_font": bool(body_median and line["font_size"] > body_median * 1.08)} for line in raw["lines"]],
        **({'hybrid_layout': raw['hybrid_layout'], 'ocr_regions': raw['ocr_regions']}
           if raw['hybrid_layout'] else {}),
        **({key:raw[key] for key in ('ignored_invisible_spans','visible_characters')}
           if raw.get('ignored_invisible_spans') else {}),
    } for raw in raw_pages]


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
