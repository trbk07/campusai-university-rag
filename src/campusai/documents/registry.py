"""Persistent registry of ingested documents."""

from __future__ import annotations

import json
import os
import threading
import contextlib
from pathlib import Path
from typing import Any


class DocumentRegistry:
    """Keep document metadata in a human-readable JSON file."""

    def __init__(self, path: str | Path = "data/store/registry.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.items: dict[str, dict[str, Any]] = self._load()

    @contextlib.contextmanager
    def _process_lock(self):
        """Use an OS file lock when available, while retaining thread safety.

        This closes the multi-worker lost-update window for the JSON registry
        without adding a runtime dependency. Windows uses ``msvcrt`` and Unix
        uses ``fcntl``; failure to lock is surfaced instead of silently
        accepting a potentially corrupted write.
        """
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load the registry, or return an empty registry for a new project."""

        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        """Write the current registry to disk."""
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def add(self, document) -> None:
        """Add or replace a document using its SHA256 id."""

        with self._lock, self._process_lock():
            self.items = self._load()
            self.items[document.doc_id] = document.to_dict()
            self._save()

    def get(self, doc_id: str) -> dict[str, Any] | None:
        """Return one document record by id."""

        with self._lock:
            self.items = self._load()
            return self.items.get(doc_id)

    def list(self) -> list[dict[str, Any]]:
        """Return all registered document records."""

        with self._lock:
            self.items = self._load()
            return list(self.items.values())

    def remove(self, doc_id: str) -> dict[str, Any] | None:
        """Remove a record if it exists."""

        with self._lock, self._process_lock():
            self.items = self._load()
            removed = self.items.pop(doc_id, None)
            if removed is not None:
                self._save()
            return removed

    def contains(self, doc_id: str) -> bool:
        """Return whether a document is registered."""

        with self._lock:
            self.items = self._load()
            return doc_id in self.items
