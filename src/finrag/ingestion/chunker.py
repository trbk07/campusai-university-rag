"""Create page-grounded text and table chunks."""

from __future__ import annotations

import json

from ..schemas import Chunk

_MAX_CHARS = 2400


def _text_sections(text: str) -> list[tuple[str, list[str]]]:
    """Split page text on markdown-like headings and paragraph boundaries."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections: list[tuple[str, list[str]]] = []
    heading_path: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        content = "\n".join(buffer)
        if len(content) <= _MAX_CHARS:
            sections.append((content, list(heading_path)))
        else:
            paragraphs = content.split("\n\n")
            current = ""
            for paragraph in paragraphs:
                if current and len(current) + len(paragraph) + 2 > _MAX_CHARS:
                    sections.append((current, list(heading_path)))
                    current = ""
                current = f"{current}\n\n{paragraph}".strip()
            if current:
                sections.append((current, list(heading_path)))
        buffer.clear()

    for line in lines:
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
            level = len(line) - len(line.lstrip("#"))
            heading_path[:] = heading_path[: max(0, level - 1)]
            heading_path.append(heading)
            buffer.append(line)
        else:
            buffer.append(line)
    flush()
    return sections


def make_chunks(pages, doc_id, metadata, tables=None):
    chunks: list[Chunk] = []
    for page in pages:
        page_number = int(page["page"])
        text = str(page.get("text", "")).strip()
        if not text:
            continue
        for position, (content, headings) in enumerate(_text_sections(text), start=1):
            chunks.append(
                Chunk(
                    f"{doc_id}_p{page_number}_c{position}",
                    doc_id,
                    page_number,
                    content,
                    "text",
                    headings,
                    {
                        **metadata,
                        "doc_id": doc_id,
                        "page": page_number,
                        "content_type": "text",
                    },
                )
            )

    for table in tables or []:
        first_page = table.pages[0]
        content = json.dumps(
            {"headers": table.headers, "rows": table.rows}, ensure_ascii=False
        )
        chunks.append(
            Chunk(
                table.table_id,
                doc_id,
                first_page,
                content,
                "table",
                [],
                {
                    **metadata,
                    "doc_id": doc_id,
                    "page": first_page,
                    "pages": table.pages,
                    "content_type": "table",
                    "table_id": table.table_id,
                },
            )
        )
    return chunks
