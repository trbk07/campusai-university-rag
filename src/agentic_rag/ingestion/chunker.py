"""Structure-aware text chunking."""
from .metadata import ContentMetadata, TextChunk


def chunk_text(text: str, *, doc_id: str, page: int, section: str | None,
               source: str | None = None, max_chars: int = 1800,
               bbox: tuple[float, float, float, float] | None = None,
               page_width: float | None = None, page_height: float | None = None) -> list[TextChunk]:
    clean = " ".join(text.split())
    if not clean:
        return []
    parts = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            boundary = clean.rfind(" ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        parts.append(TextChunk(clean[start:end], ContentMetadata(
            doc_id, page, section, "text", source, bbox, page_width, page_height)))
        start = end
        while start < len(clean) and clean[start].isspace():
            start += 1
    return parts


