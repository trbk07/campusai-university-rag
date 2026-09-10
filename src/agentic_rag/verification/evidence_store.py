"""In-memory evidence registry with stable IDs."""
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    text: str
    metadata: dict

class EvidenceStore:
    def __init__(self, evidence: Iterable[Evidence] = ()):
        self._items = {item.evidence_id: item for item in evidence}
    def add(self, evidence: Evidence) -> None: self._items[evidence.evidence_id] = evidence
    def get(self, evidence_id: str) -> Evidence | None: return self._items.get(evidence_id)
    def ids(self) -> list[str]: return list(self._items)
    def as_context(self, ids: Iterable[str] | None = None) -> str:
        selected = ids if ids is not None else self.ids()
        return "\n".join(f"[{key}] {self._items[key].text}" for key in selected if key in self._items)

