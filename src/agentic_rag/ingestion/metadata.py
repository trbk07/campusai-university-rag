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
    start_page: int | None = None
    end_page: int | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.start_page is None:
            self.start_page = self.metadata.page
        if self.end_page is None:
            self.end_page = self.metadata.page


@dataclass
class ParsedDocument:
    doc_id: str
    source: str
    chunks: list[TextChunk] = field(default_factory=list)
    tables: list[TableRecord] = field(default_factory=list)
    pages: int = 0
    warnings: list[str] = field(default_factory=list)
    ocr_diagnostics: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_manifest(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "pages": self.pages,
            "num_chunks": len(self.chunks),
            "num_tables": len(self.tables),
            "tables": [{"table_id": table.table_id, "start_page": table.start_page,
                        "end_page": table.end_page, "columns": list(table.dataframe.columns),
                        "diagnostics": table.diagnostics}
                       for table in self.tables],
            "warnings": self.warnings,
            "ocr_diagnostics": self.ocr_diagnostics,
        }

