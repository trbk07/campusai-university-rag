"""PDF text and table parser with page/section metadata."""
from collections import Counter
from pathlib import Path
import re
import string
import statistics
import pandas as pd
import pymupdf
import pdfplumber
from .chunker import chunk_text
from .metadata import ContentMetadata, ParsedDocument, TableRecord
from .table_extractor import normalize_rows, table_schema


def _same_header(left: list[object], right: list[object]) -> bool:
    """Compare continuation headers after case/whitespace/unit punctuation cleanup."""
    def normalize(value: object) -> str:
        text = _clean(str(value)).casefold()
        return re.sub(r"[\W_]+", "", text)
    return [normalize(value) for value in left] == [normalize(value) for value in right]
from .ocr import ocr_page

_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?\s+)?[A-ZÀ-ỸĐ][^.!?]{2,100}$", re.UNICODE)


def _clean(value: str) -> str:
    return " ".join(value.split())


def _ocr_quality_warning(text: str, page_number: int) -> str | None:
    clean = _clean(text)
    if len(clean) < 10:
        return f"page {page_number}: OCR text is very short ({len(clean)} chars); manual review required"
    printable = sum(char.isprintable() and not char.isspace() for char in clean)
    suspicious = sum(not (char.isalnum() or char.isspace() or char in string.punctuation or '\u00c0' <= char <= '\u024f')
                    for char in clean)
    if printable and suspicious / printable > 0.12:
        return f"page {page_number}: OCR text contains suspicious characters; manual review required"
    return None


def _order_blocks(blocks: list[dict], page_width: float) -> list[dict]:
    """Order text blocks in reading order, including clearly separated columns.

    PyMuPDF returns blocks in a layout-dependent order.  For ordinary pages we
    retain the familiar top-to-bottom ordering.  When two non-overlapping
    columns are unambiguous, each column is read top-to-bottom before moving to
    the next one; this avoids interleaving left/right paragraphs.
    """
    if len(blocks) < 4 or not page_width:
        return sorted(blocks, key=lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1)))
    starts = sorted({round(item["bbox"][0], 1) for item in blocks})
    gaps = [(right - left, left, right) for left, right in zip(starts, starts[1:])]
    gap, boundary, _ = max(gaps, default=(0.0, 0.0, 0.0))
    if gap < page_width * 0.18:
        return sorted(blocks, key=lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1)))
    left = [item for item in blocks if item["bbox"][0] <= boundary]
    right = [item for item in blocks if item["bbox"][0] > boundary]
    if len(left) < 2 or len(right) < 2:
        return sorted(blocks, key=lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1)))
    left_max = max(item["bbox"][2] for item in left)
    right_min = min(item["bbox"][0] for item in right)
    if left_max > right_min:
        return sorted(blocks, key=lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1)))
    key = lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1))
    return sorted(left, key=key) + sorted(right, key=key)


def _looks_like_heading(line: str, *, font_size: float | None = None, body_size: float | None = None,
                        y: float | None = None, page_height: float | None = None) -> bool:
    line = _clean(line)
    if not line or len(line) > 120 or not _HEADING.match(line) or line.endswith((":", ";")):
        return False
    words = line.split()
    layout_signal = bool(font_size and body_size and font_size >= body_size * 1.12)
    numbered = bool(re.match(r"^\d+(?:\.\d+)*[.)]?\s+", line))
    upper = line.isupper()
    short_title = len(words) <= 10 and not line.endswith(".")
    margin_signal = bool(y is not None and page_height and (y < page_height * .18 or y > page_height * .82))
    if margin_signal and not (upper or numbered or layout_signal):
        return False
    return upper or numbered or layout_signal or short_title


def _repeated_margin_text(pages: list[list[dict]]) -> set[str]:
    """Find repeated margin text, including templates with changing page/date tokens."""
    page_candidates = []
    for blocks in pages:
        if not blocks:
            continue
        ordered = sorted(blocks, key=lambda item: item["bbox"][1])
        page_candidates.append({_clean(item["text"]) for item in (ordered[:2] + ordered[-2:]) if item["text"]})
    counts = Counter(text for candidates in page_candidates for text in candidates)
    result = {text for text, count in counts.items() if count >= 2 and len(text) > 2}
    templates: dict[str, dict[int, set[str]]] = {}
    for page_index, candidates in enumerate(page_candidates):
        for text in candidates:
            template = re.sub(r"\b(?:page|trang|p(?:age)?)[\s:#-]*\d+\b|\b\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b", "<token>", text, flags=re.I)
            if template != text and len(template.replace("<token>", "").strip()) > 2:
                templates.setdefault(template.casefold(), {}).setdefault(page_index, set()).add(text)
    for pages_for_template in templates.values():
        if len(pages_for_template) >= 2:
            result.update(text for values in pages_for_template.values() for text in values)
    return result


def parse_pdf(path: str | Path, *, doc_id: str | None = None, max_chars: int = 1800,
              use_ocr: bool = False, ocr_language: str = "eng", ocr_dpi: int = 200,
              tesseract_cmd: str | None = None) -> ParsedDocument:
    source = str(Path(path))
    doc_id = doc_id or Path(path).stem
    document = ParsedDocument(doc_id=doc_id, source=source)
    with pymupdf.open(source) as pdf:
        document.pages = len(pdf)
        page_blocks = []
        page_heights = []
        page_widths = []
        page_objects = []
        for page in pdf:
            page_objects.append(page)
            page_heights.append(page.rect.height)
            page_widths.append(page.rect.width)
            blocks = []
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                raw_lines = [_clean(" ".join(span["text"] for span in line.get("spans", [])))
                             for line in block.get("lines", [])]
                sizes = [span["size"] for line in block.get("lines", []) for span in line.get("spans", [])]
                for text in raw_lines:
                    if text:
                        blocks.append({"text": text, "bbox": block["bbox"], "size": max(sizes, default=0.0)})
            page_blocks.append(blocks)
        repeated = _repeated_margin_text(page_blocks)
        section = None
        sizes = [block["size"] for blocks in page_blocks for block in blocks if block["size"]]
        body_size = statistics.median(sizes) if sizes else None
        for page_number, blocks in enumerate(page_blocks, start=1):
            page_section = section
            page_height = page_heights[page_number - 1]
            lines = []
            ordered_blocks = _order_blocks(blocks, page_widths[page_number - 1])
            for block in ordered_blocks:
                clean = block["text"]
                if clean in repeated:
                    continue
                if _looks_like_heading(clean, font_size=block["size"], body_size=body_size,
                                        y=block["bbox"][1], page_height=page_height):
                    section = clean
                    page_section = clean
                else:
                    lines.append(clean)
            if lines:
                document.chunks.extend(chunk_text(" ".join(lines), doc_id=doc_id, page=page_number,
                                                   section=page_section, source=source, max_chars=max_chars))
            if not blocks or not lines:
                if use_ocr:
                    try:
                        ocr_text = ocr_page(page_objects[page_number - 1], language=ocr_language,
                                            dpi=ocr_dpi, tesseract_cmd=tesseract_cmd)
                    except RuntimeError as exc:
                        document.warnings.append(f"page {page_number}: OCR failed: {exc}")
                    else:
                        if ocr_text:
                            document.chunks.extend(chunk_text(ocr_text, doc_id=doc_id, page=page_number,
                                                               section=section, source=source, max_chars=max_chars))
                            quality_warning = _ocr_quality_warning(ocr_text, page_number)
                            if quality_warning:
                                document.warnings.append(quality_warning)
                        else:
                            document.warnings.append(f"page {page_number}: OCR returned no text")
                else:
                    document.warnings.append(f"page {page_number}: no usable text layer; OCR required")
    with pdfplumber.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for index, rows in enumerate(page.extract_tables() or []):
                frame = normalize_rows(rows or [])
                if frame is None:
                    continue
                metadata = ContentMetadata(doc_id, page_number, None, "table", source)
                document.tables.append(TableRecord(frame, table_schema(frame), metadata,
                                                   f"{doc_id}_p{page_number}_t{index}"))
    _stitch_tables(document)
    return document


def _stitch_tables(document: ParsedDocument) -> None:
    """Merge adjacent page tables when the normalized schemas match."""
    merged: list[TableRecord] = []
    for record in document.tables:
        if (merged
                and record.metadata.page == merged[-1].metadata.page + 1
                and merged[-1].dataframe.columns.tolist() == record.dataframe.columns.tolist()):
            previous = merged[-1]
            next_frame = record.dataframe
            if (not next_frame.empty
                    and _same_header(next_frame.iloc[0].tolist(), previous.dataframe.columns.tolist())):
                next_frame = next_frame.iloc[1:].reset_index(drop=True)
            if not next_frame.empty:
                previous.dataframe = pd.concat([previous.dataframe, next_frame], ignore_index=True)
                previous.schema = table_schema(previous.dataframe)
                previous.end_page = record.end_page
        else:
            merged.append(record)
    document.tables = merged


