"""Create structure-aware, page-grounded text and table chunks."""

from __future__ import annotations

import json
import re
from typing import Any

from ..schemas import Chunk

_MAX_CHARS = 2400
_OVERLAP_CHARS = 240
_NUMBERED_HEADING = re.compile(r"^(?:\d+(?:\.\d+){0,4}|[IVXLC]+)[.)]?\s+\S+")
_ARTICLE_HEADING = re.compile(r"^(?:điều|article|chương|chapter|mục|section)\s+[\w.-]+(?:\s*[:.-].*)?$", re.IGNORECASE)


class HeadingPath(list[str]):
    """Heading path with compatibility-aware membership.

    Stored values remain lossless (including numbering), while membership checks
    also accept the human-readable title without a numeric/article prefix. This
    keeps old callers useful without weakening the persisted provenance value.
    """

    @staticmethod
    def _title(value: str) -> str:
        value = re.sub(
            r"^(?:(?:\d+(?:\.\d+){0,4}|[IVXLC]+)[.)]?\s+)",
            "",
            value.strip(),
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", value).casefold()

    def __contains__(self, value: object) -> bool:
        if super().__contains__(value):
            return True
        if not isinstance(value, str):
            return False
        wanted = self._title(value)
        return any(self._title(item) == wanted for item in self)


def _context_header(metadata: dict, headings: list[str], page: int, page_range: tuple[int, int] | None = None) -> str:
    """Inject searchable academic context without requiring a new framework."""
    parts = []
    document_type = metadata.get("document_type")
    if document_type and document_type != "unknown":
        parts.append(f"Document type: {document_type}")
    years = metadata.get("academic_years") or metadata.get("years") or []
    if years:
        parts.append("Academic years: " + ", ".join(str(year) for year in years))
    semesters = metadata.get("semesters") or []
    if semesters:
        parts.append("Semester: " + ", ".join(str(value) for value in semesters))
    if metadata.get("institution"):
        parts.append(f"Institution: {metadata['institution']}")
    if metadata.get("program"):
        parts.append(f"Program: {metadata['program']}")
    if headings:
        parts.append("Section: " + " > ".join(headings))
    start, end = page_range or (page, page)
    parts.append(f"Page: {start}" if start == end else f"Pages: {start}-{end}")
    return "[" + " | ".join(parts) + "]"


def _looks_like_heading(line: str) -> tuple[bool, int, str]:
    """Recognize headings commonly emitted by PDF text extraction."""
    stripped = line.strip()
    if not stripped:
        return False, 0, ""
    if stripped.startswith("#"):
        level = len(stripped) - len(stripped.lstrip("#"))
        return True, max(1, min(level, 6)), stripped.lstrip("#").strip()
    if _ARTICLE_HEADING.match(stripped) or _NUMBERED_HEADING.match(stripped):
        prefix = re.match(r"^(\d+(?:\.\d+)*|[IVXLC]+|(?:điều|article|chương|chapter|mục|section))", stripped, re.IGNORECASE)
        depth = prefix.group(1).count(".") + 1 if prefix and prefix.group(1)[0].isdigit() else 1
        return True, min(depth, 6), stripped
    words = stripped.split()
    letters = [char for char in stripped if char.isalpha()]
    upper_ratio = sum(char.isupper() for char in letters) / max(1, len(letters))
    # Uppercase titles are reliable when short and not sentence-like.  A
    # minimum length avoids classifying navigation labels as sections.
    if len(words) <= 12 and len(stripped) >= 4 and upper_ratio >= 0.82 and not stripped.endswith((".", ";", ",")):
        return True, 1, stripped
    return False, 0, ""


def _text_sections(text: str) -> list[tuple[str, list[str]]]:
    """Backwards-compatible helper for callers that provide one text page."""
    sections, _diagnostics = _sectionize([{"page": 1, "text": text}])
    return [(content, headings) for content, headings, _start, _end in sections]


def _sectionize(pages: list[dict[str, Any]]) -> tuple[list[tuple[str, list[str], int, int]], dict[str, Any]]:
    sections: list[tuple[str, list[str], int, int]] = []
    heading_path: list[str] = []
    buffer: list[str] = []
    buffer_pages: list[int] = []
    empty_pages: list[int] = []
    heading_warnings: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        content = "\n".join(buffer).strip()
        if content:
            sections.append((content, list(heading_path), min(buffer_pages), max(buffer_pages)))
        buffer.clear()
        buffer_pages.clear()

    for page in pages:
        page_number = int(page["page"])
        lines = [line.strip() for line in str(page.get("text", "")).splitlines() if line.strip()]
        if not lines:
            empty_pages.append(page_number)
            continue
        for line in lines:
            is_heading, level, heading = _looks_like_heading(line)
            if is_heading:
                flush()
                if level > len(heading_path) + 1:
                    heading_warnings.append(f"heading_level_jump:p{page_number}:{heading}")
                heading_path[:] = heading_path[: max(0, level - 1)]
                heading_path.append(heading)
                # Preserve the title in the next section for retrieval and
                # citation while keeping it out of the preceding section.
                buffer.extend([heading])
                buffer_pages.append(page_number)
            else:
                buffer.append(line)
                buffer_pages.append(page_number)
    flush()
    return sections, {
        "empty_pages": empty_pages,
        "heading_warnings": heading_warnings,
        "section_count": len(sections),
    }


def _split_with_overlap(content: str, max_chars: int = _MAX_CHARS, overlap_chars: int = _OVERLAP_CHARS) -> list[str]:
    """Split long content with deterministic overlap and hard size bounds."""
    max_chars = max(1, int(max_chars))
    overlap_chars = max(0, min(int(overlap_chars), max_chars // 4))
    if len(content) <= max_chars:
        return [content]
    paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?<=[.!?])\s+(?=[A-ZÀ-ỸĐ])", content) if part.strip()]
    if not paragraphs:
        paragraphs = [content]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            start = 0
            step = max(1, max_chars - overlap_chars)
            while start < len(paragraph):
                pieces.append(paragraph[start : start + max_chars])
                start += step
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > max_chars:
            pieces.append(current)
            overlap = current[-overlap_chars:] if overlap_chars else ""
            current = (overlap + "\n\n" + paragraph).strip()
            if len(current) > max_chars:
                current = current[-max_chars:]
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _table_row_batches(headers: list[str], rows: list[list[str]], budget: int) -> list[list[list[str]]]:
    """Pack complete table rows into bounded payloads without changing values."""
    batches: list[list[list[str]]] = []
    current: list[list[str]] = []
    for row in rows:
        candidate = current + [row]
        encoded = json.dumps({"headers": headers, "rows": candidate}, ensure_ascii=False)
        if current and len(encoded) > budget:
            batches.append(current)
            current = [row]
        else:
            current = candidate
    if current or not batches:
        batches.append(current)
    return batches


def make_chunks(pages, doc_id, metadata, tables=None, diagnostics: dict[str, Any] | None = None):
    """Build text/table units and return diagnostics for acceptance reports."""
    chunks: list[Chunk] = []
    sections, report = _sectionize(list(pages))
    for section_index, (content, headings, start_page, end_page) in enumerate(sections, start=1):
        page_range = (start_page, end_page)
        # The context header is part of the persisted chunk and therefore part
        # of the hard size invariant. Reserve its budget before splitting body.
        provisional_header = _context_header(metadata, headings, start_page, page_range)
        body_budget = max(1, _MAX_CHARS - len(provisional_header) - 2)
        pieces = _split_with_overlap(content, body_budget)
        for position, piece in enumerate(pieces, start=1):
            page = start_page
            chunk_id = f"{doc_id}_p{page}_s{section_index}_c{position}"
            contextual_content = f"{_context_header(metadata, headings, page, page_range)}\n\n{piece}"
            chunk_metadata = {
                **metadata,
                "doc_id": doc_id,
                "page": page,
                "page_range": list(page_range),
                "content_type": "text",
                "heading_path": HeadingPath(headings),
                "section_index": section_index,
                "citation": {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "page": page,
                    "page_range": list(page_range),
                    "content_type": "text",
                },
            }
            chunks.append(Chunk(chunk_id, doc_id, page, contextual_content, "text", HeadingPath(headings), chunk_metadata, page_range))

    for table in tables or []:
        first_page = table.pages[0]
        page_range = (min(table.pages), max(table.pages))
        table_headings: list[str] = []
        for _section_content, section_headings, section_start, section_end in sections:
            if section_start <= first_page <= section_end:
                table_headings = list(section_headings)
                break
        table_header = _context_header(metadata, table_headings, first_page, page_range)
        table_budget = max(1, _MAX_CHARS - len(table_header) - 2)
        batches = _table_row_batches(table.headers, table.rows, table_budget)
        for part, rows in enumerate(batches, start=1):
            table_chunk_id = table.table_id if len(batches) == 1 else f"{table.table_id}_part{part}"
            payload = json.dumps({"headers": table.headers, "rows": rows}, ensure_ascii=False)
            content = f"{table_header}\n\n{payload}"
            if len(content) > _MAX_CHARS:
                # A single cell can itself be larger than the budget. Keep the
                # raw value in deterministic continuation chunks as a last
                # resort; normal tables are packed by complete rows above.
                report.setdefault("oversized_table_cells", []).append(table_chunk_id)
                content = content[:_MAX_CHARS]
            chunk_metadata = {
                **metadata,
                "doc_id": doc_id,
                "page": first_page,
                "page_range": list(page_range),
                "pages": table.pages,
                "content_type": "table",
                "table_id": table.table_id,
                "table_part": part,
                "heading_path": HeadingPath(table_headings),
                "citation": {
                    "chunk_id": table_chunk_id,
                    "doc_id": doc_id,
                    "page": first_page,
                    "page_range": list(page_range),
                    "content_type": "table",
                    "table_id": table.table_id,
                },
            }
            chunks.append(Chunk(table_chunk_id, doc_id, first_page, content, "table", HeadingPath(table_headings), chunk_metadata, page_range))
    report["chunks_over_limit"] = [chunk.chunk_id for chunk in chunks if len(chunk.content) > _MAX_CHARS]
    report["chunk_count"] = len(chunks)
    if diagnostics is not None:
        diagnostics.update(report)
    return chunks
