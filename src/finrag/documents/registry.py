"""Persistent registry of ingested documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DocumentRegistry:
    """Keep document metadata in a human-readable JSON file."""

    def __init__(self, path: str | Path = "data/store/registry.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.items: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load the registry, or return an empty registry for a new project."""

        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        """Write the current registry to disk."""

        self.path.write_text(
            json.dumps(self.items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, document) -> None:
        """Add or replace a document using its SHA256 id."""

        self.items[document.doc_id] = document.to_dict()
        self._save()

    def get(self, doc_id: str) -> dict[str, Any] | None:
        """Return one document record by id."""

        return self.items.get(doc_id)

    def list(self) -> list[dict[str, Any]]:
        """Return all registered document records."""

        return list(self.items.values())

    def remove(self, doc_id: str) -> None:
        """Remove a record if it exists."""

        self.items.pop(doc_id, None)
        self._save()

    def contains(self, doc_id: str) -> bool:
        """Return whether a document is registered."""

        return doc_id in self.items
