"""Data contracts shared by ingestion and downstream pipeline stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Chunk:
    """A searchable piece of document content with provenance."""

    chunk_id: str
    doc_id: str
    page: int
    content: str
    content_type: str = "text"
    heading_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Chunk":
        """Restore a chunk persisted by :meth:`Document.to_dict`."""
        return cls(
            chunk_id=str(value["chunk_id"]),
            doc_id=str(value["doc_id"]),
            page=int(value["page"]),
            content=str(value.get("content", "")),
            content_type=str(value.get("content_type", "text")),
            heading_path=list(value.get("heading_path", [])),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass
class Table:
    """A detected table and its basic schema description."""

    table_id: str
    doc_id: str
    pages: list[int]
    headers: list[str]
    rows: list[list[str]]
    schema: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Table":
        """Restore a table persisted by :meth:`Document.to_dict`."""
        return cls(
            table_id=str(value["table_id"]),
            doc_id=str(value["doc_id"]),
            pages=[int(page) for page in value.get("pages", [])],
            headers=[str(header) for header in value.get("headers", [])],
            rows=[[str(cell) for cell in row] for row in value.get("rows", [])],
            schema=dict(value.get("schema", {})),
        )


@dataclass
class Document:
    """Complete persisted result of ingesting one source PDF."""

    doc_id: str
    source_path: str
    page_count: int
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    chunks: list[Chunk] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert the document and nested dataclasses to JSON-ready data."""

        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Document":
        """Restore a complete document and its nested dataclasses."""
        return cls(
            doc_id=str(value["doc_id"]),
            source_path=str(value["source_path"]),
            page_count=int(value["page_count"]),
            language=value.get("language"),
            metadata=dict(value.get("metadata", {})),
            chunks=[Chunk.from_dict(item) for item in value.get("chunks", [])],
            tables=[Table.from_dict(item) for item in value.get("tables", [])],
            cached=bool(value.get("cached", False)),
        )
