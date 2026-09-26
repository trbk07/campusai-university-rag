"""Request-scoped evidence registry used for fail-closed citation resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..retrieval.hybrid import RetrievalResult


@dataclass(frozen=True)
class EvidenceRecord:
    chunk_id: str
    doc_id: str
    page: int
    page_range: tuple[int, int]
    content: str
    content_type: str
    table_id: str | None = None
    source_hash: str | None = None
    source_name: str = ""
    heading_path: tuple[str, ...] = ()
    document_version: str | None = None
    metadata_tokens: tuple[str, ...] = ()
    effective_date: str | None = None

    @classmethod
    def from_result(cls, result: RetrievalResult) -> "EvidenceRecord":
        metadata = result.metadata or {}
        page_range = tuple(metadata.get("page_range", [result.page, result.page]))
        metadata_values = tuple(str(metadata[key]) for key in ("document_type", "program", "institution", "version") if metadata.get(key) is not None)
        return cls(result.chunk_id, result.doc_id, int(result.page), (int(page_range[0]), int(page_range[1])),
                   result.content, result.content_type, metadata.get("table_id"), metadata.get("source_hash"),
                   str(metadata.get("source_name", "")), tuple(metadata.get("heading_path", [])),
                   metadata.get("version"), metadata_values, metadata.get("effective_date"))


class EvidenceRegistry:
    def __init__(self, results: Iterable[RetrievalResult] = ()) -> None:
        self._records = {record.chunk_id: record for record in map(EvidenceRecord.from_result, results)}

    def get(self, chunk_id: str) -> EvidenceRecord | None:
        return self._records.get(str(chunk_id))

    def __contains__(self, chunk_id: str) -> bool:
        return str(chunk_id) in self._records

    def values(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records.values())

    def resolve(self, chunk_id: str, *, doc_id: str | None = None) -> EvidenceRecord | None:
        record = self.get(chunk_id)
        if record is None or (doc_id is not None and record.doc_id != doc_id):
            return None
        return record

    def version_conflicts(self, chunk_ids: Iterable[str] | None = None) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """Return documents whose retrieved evidence carries multiple versions."""
        selected = self.values() if chunk_ids is None else tuple(
            record for chunk_id in chunk_ids if (record := self.get(chunk_id)) is not None
        )
        versions: dict[str, set[str]] = {}
        for record in selected:
            if record.document_version:
                versions.setdefault(record.doc_id, set()).add(str(record.document_version))
        return tuple(sorted((doc_id, tuple(sorted(values))) for doc_id, values in versions.items() if len(values) > 1))

    def missing_provenance(self, chunk_ids: Iterable[str] | None = None) -> tuple[str, ...]:
        """Identify evidence spans without stable source hash or version metadata."""
        selected = self.values() if chunk_ids is None else tuple(
            record for chunk_id in chunk_ids if (record := self.get(chunk_id)) is not None
        )
        return tuple(sorted(record.chunk_id for record in selected
                           if not record.source_hash and not record.document_version))
