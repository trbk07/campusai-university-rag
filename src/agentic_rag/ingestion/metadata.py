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
    bbox: tuple[float, float, float, float] | None = None
    page_width: float | None = None
    page_height: float | None = None


@dataclass(frozen=True)
class FigureRecord:
    figure_id: str
    page: int
    bbox: tuple[float, float, float, float] | None
    kind: str = "figure"
    image_index: int | None = None
    text: str | None = None
    metadata: ContentMetadata | None = None
    artifact_name: str | None = None
    artifact_sha256: str | None = None
    ocr_diagnostics: dict[str, Any] = field(default_factory=dict)
    status: str = "detected"

    def to_manifest_record(self) -> dict[str, Any]:
        return {"figure_id": self.figure_id, "page": self.page, "bbox": self.bbox,
                "kind": self.kind, "image_index": self.image_index, "text": self.text,
                "artifact_name": self.artifact_name, "artifact_sha256": self.artifact_sha256,
                "ocr_diagnostics": self.ocr_diagnostics, "status": self.status}


@dataclass
class ChartRecord:
    """Structured chart output; values are never inferred without evidence."""
    figure_id: str
    title: str | None = None
    legend: list[str] = field(default_factory=list)
    axes: dict[str, Any] = field(default_factory=dict)
    series: list[dict[str, Any]] = field(default_factory=list)
    status: str = "review_required"
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_manifest_record(self) -> dict[str, Any]:
        return self.__dict__.copy()


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
    # Original extractor rows are retained separately from the normalized frame.
    # This is essential for reconstructing merged headers and auditing numeric cells.
    raw_rows: list[list[Any]] | None = None

    @property
    def content_type(self) -> str:
        return "table"

    def to_raw_record(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "source": self.metadata.source,
            "doc_id": self.metadata.doc_id,
            "bbox": self.metadata.bbox,
            "page_width": self.metadata.page_width,
            "page_height": self.metadata.page_height,
            "rows": self.raw_rows if self.raw_rows is not None else self.dataframe.astype(object).where(self.dataframe.notna(), None).values.tolist(),
            "normalized_columns": [str(column) for column in self.dataframe.columns],
            "diagnostics": self.diagnostics,
        }


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
    figures: list[FigureRecord] = field(default_factory=list)
    charts: list[ChartRecord] = field(default_factory=list)
    page_dimensions: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_manifest(self) -> dict[str, Any]:
        failed_warning = next((warning for warning in self.warnings if warning.startswith("document failed:")), None)
        status = "failed" if failed_warning else (
            "review_required" if (any(table.diagnostics.get("status") == "review_required" for table in self.tables)
                                   or any(item.status == "review_required" for item in self.figures)
                                   or any(item.status == "review_required" for item in self.charts))
            else ("warning" if self.warnings else "ok")
        )
        manifest = {
            "doc_id": self.doc_id,
            "source": self.source,
            "pages": self.pages,
            "pages_processed": self.pages,
            "num_chunks": len(self.chunks),
            "num_tables": len(self.tables),
            "status": status,
            "figures_review_required": sum(item.status == "review_required" for item in self.figures),
            "charts_review_required": sum(item.status == "review_required" for item in self.charts),
            "tables_review_required": sum(table.diagnostics.get("status") == "review_required" for table in self.tables),
            "tables": [{"table_id": table.table_id, "start_page": table.start_page,
                        "end_page": table.end_page, "columns": list(table.dataframe.columns),
                        "bbox": table.metadata.bbox,
                        "diagnostics": table.diagnostics}
                       for table in self.tables],
            "warnings": self.warnings,
            "ocr_diagnostics": self.ocr_diagnostics,
            "page_dimensions": self.page_dimensions,
            "num_figures": len(self.figures),
            "num_charts": len(self.charts),
            "figures": [item.to_manifest_record() for item in self.figures],
            "charts": [item.to_manifest_record() for item in self.charts],
        }
        return manifest

