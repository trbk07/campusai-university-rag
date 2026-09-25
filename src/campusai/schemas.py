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
    # Kept after the original fields for backwards-compatible positional
    # construction by older indexes and callers.
    page_range: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.page_range is None:
            self.page_range = (int(self.page), int(self.page))
        else:
            self.page_range = (int(self.page_range[0]), int(self.page_range[1]))
        self.metadata.setdefault("page_range", list(self.page_range))
        self.metadata.setdefault(
            "citation",
            {
                "doc_id": self.doc_id,
                "page": self.page,
                "page_range": list(self.page_range),
                "content_type": self.content_type,
            },
        )

    @property
    def citation(self) -> dict[str, Any]:
        """Return the stable citation payload inherited by downstream stages."""

        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "page": self.page,
            "page_range": list(self.page_range or (self.page, self.page)),
            "content_type": self.content_type,
        }

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
            page_range=tuple(value.get("page_range") or value.get("metadata", {}).get("page_range", [value["page"], value["page"]])),
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
    status: str = "succeeded"
    review_reason: str | None = None

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
            status=str(value.get("status", "succeeded")),
            review_reason=value.get("review_reason"),
        )
