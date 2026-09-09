"""Metadata and records produced by document ingestion."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContentMetadata:
    doc_id: str
    page: int
    section: str | None
    content_type: str
    source: str | None = None


@dataclass
class TextChunk:
    text: str
    metadata: ContentMetadata


@dataclass
class TableRecord:
    dataframe: Any
    schema: dict[str, str]
    metadata: ContentMetadata
    table_id: str


@dataclass
class ParsedDocument:
    doc_id: str
    source: str
    chunks: list[TextChunk] = field(default_factory=list)
    tables: list[TableRecord] = field(default_factory=list)
    pages: int = 0

    def to_manifest(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "pages": self.pages,
            "num_chunks": len(self.chunks),
            "num_tables": len(self.tables),
        }


