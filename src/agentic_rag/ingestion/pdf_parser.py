"""PDF text and table parser with page/section metadata."""
from collections import Counter
from pathlib import Path
import re
import statistics
import pandas as pd
import pymupdf
import pdfplumber
from .chunker import chunk_text
from .metadata import ContentMetadata, ParsedDocument, TableRecord
from .table_extractor import normalize_rows, table_schema
from .ocr import ocr_page

_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?\s+)?[A-ZÀ-ỸĐ][^.!?]{2,100}$", re.UNICODE)


def _clean(value: str) -> str:
    return " ".join(value.split())


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
    """Find identical text blocks repeated at the top/bottom of several pages."""
    page_candidates = []
    for blocks in pages:
        if not blocks:
            continue
        ordered = sorted(blocks, key=lambda item: item["bbox"][1])
        page_candidates.append({_clean(item["text"]) for item in (ordered[:2] + ordered[-2:]) if item["text"]})
    counts = Counter(text for candidates in page_candidates for text in candidates)
    return {text for text, count in counts.items() if count >= 2 and len(text) > 2}


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
        page_objects = []
        for page in pdf:
            page_objects.append(page)
            page_heights.append(page.rect.height)
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
            ordered_blocks = sorted(blocks, key=lambda item: (round(item["bbox"][1], 1), round(item["bbox"][0], 1)))
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
            elif not blocks:
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
                        else:
                            document.warnings.append(f"page {page_number}: OCR returned no text")
                else:
                    document.warnings.append(f"page {page_number}: no text layer; OCR required")
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
            if not next_frame.empty and next_frame.iloc[0].astype(str).tolist() == previous.dataframe.columns.astype(str).tolist():
                next_frame = next_frame.iloc[1:].reset_index(drop=True)
            if not next_frame.empty:
                previous.dataframe = pd.concat([previous.dataframe, next_frame], ignore_index=True)
                previous.schema = table_schema(previous.dataframe)
        else:
            merged.append(record)
    document.tables = merged


