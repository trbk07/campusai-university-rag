"""PDF text and table parser with page/section metadata."""
from pathlib import Path
import re
import pymupdf
import pdfplumber
from .chunker import chunk_text
from .metadata import ContentMetadata, ParsedDocument, TableRecord
from .table_extractor import normalize_rows, table_schema

_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*[.)]?\s+)?[A-ZÀ-Ỹ][^.!?]{2,100}$")


def _looks_like_heading(line: str) -> bool:
    line = " ".join(line.split())
    return bool(line and len(line) <= 120 and _HEADING.match(line) and (line.isupper() or len(line.split()) <= 12))


def parse_pdf(path: str | Path, *, doc_id: str | None = None, max_chars: int = 1800) -> ParsedDocument:
    source = str(Path(path))
    doc_id = doc_id or Path(path).stem
    document = ParsedDocument(doc_id=doc_id, source=source)
    with pymupdf.open(source) as pdf:
        document.pages = len(pdf)
        section = None
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text") or ""
            page_section = section
            lines = []
            for line in text.splitlines():
                clean = " ".join(line.split())
                if not clean:
                    continue
                if _looks_like_heading(clean):
                    section = clean
                    page_section = clean
                else:
                    lines.append(clean)
            document.chunks.extend(chunk_text(" ".join(lines), doc_id=doc_id, page=page_number,
                                               section=page_section, source=source, max_chars=max_chars))
    with pdfplumber.open(source) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for index, rows in enumerate(page.extract_tables() or []):
                if not rows:
                    continue
                frame = normalize_rows(rows)
                if frame is None:
                    continue
                metadata = ContentMetadata(doc_id, page_number, None, "table", source)
                document.tables.append(TableRecord(frame, table_schema(frame), metadata,
                                                   f"{doc_id}_p{page_number}_t{index}"))
    return document


