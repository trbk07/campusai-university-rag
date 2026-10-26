"""Persistent registry of ingested documents."""

from __future__ import annotations

from copy import deepcopy
import json
import os
import threading
import contextlib
import weakref
import tempfile
import time
from pathlib import Path
from typing import Any


_LOCKS = weakref.WeakValueDictionary()
_LOCKS_GUARD = threading.Lock()


def _path_lock(path):
    key = str(path.resolve())
    if os.name == 'nt':
        if key.startswith('\\\\?\\UNC\\'):
            key = '\\\\' + key[8:]
        elif key.startswith('\\\\?\\'):
            key = key[4:]
    key = os.path.normcase(key)
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


class DocumentRegistry:
    """Keep document metadata in a human-readable JSON file."""

    def __init__(self, path: str | Path = "data/store/registry.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = _path_lock(self.path)
        self._metadata_cache = None
        self._metadata_identity = None
        with self._lock, self._process_lock():
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
        locked = False
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            locked = True
            yield
        finally:
            try:
                if not locked:
                    pass
                elif os.name == "nt":
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
        fd, name = tempfile.mkstemp(prefix='.' + self.path.name + '.', suffix='.tmp', dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(self.items, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            # Windows readers/scanners can briefly hold a non-delete-sharing
            # handle even after the registry writer lock is acquired. Retry
            # only that OS sharing/access conflict, keeping the same atomic
            # snapshot and writer lock; other I/O failures remain immediate.
            for attempt in range(6):
                try:
                    os.replace(temporary, self.path)
                    break
                except PermissionError as error:
                    if os.name != 'nt' or getattr(error, 'winerror', None) not in {5,32,33} or attempt == 5:
                        raise
                    time.sleep(min(.005 * 2**attempt, .05))
        finally:
            temporary.unlink(missing_ok=True)

    def add(self, document) -> None:
        """Add or replace a document using its SHA256 id."""

        with self._lock, self._process_lock():
            self.items = self._load()
            self.items[document.doc_id] = document.to_dict()
            self._save()

    def _file_identity(self):
        try:
            stat = self.path.stat()
        except FileNotFoundError:
            return None
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)

    def _metadata_snapshot(self):
        """Cache only transport metadata, checking the live file under its lock."""
        fields = {'doc_id','source_path','page_count','language','metadata','status','review_reason','cached'}
        with self._lock, self._process_lock():
            identity = self._file_identity()
            if self._metadata_cache is None or identity != self._metadata_identity:
                items = self._load()
                if self._file_identity() != identity:
                    raise OSError('registry changed during metadata read')
                self.items = items
                self._metadata_cache = deepcopy({key:{name:value for name,value in row.items() if name in fields}
                                                 for key,row in items.items()})
                self._metadata_identity = identity
            return self._metadata_cache

    def metadata_get(self, doc_id: str) -> dict[str, Any] | None:
        """Return an isolated metadata record without parsing all chunk bodies."""
        return deepcopy(self._metadata_snapshot().get(doc_id))

    def metadata_list(self, *, doc_ids=None) -> list[dict[str, Any]]:
        """Return isolated metadata; external writes and deletions remain visible."""
        wanted = None if doc_ids is None else set(doc_ids)
        return deepcopy([row for identifier, row in self._metadata_snapshot().items()
                         if wanted is None or identifier in wanted])

    def get(self, doc_id: str) -> dict[str, Any] | None:
        """Return one document record by id."""

        with self._lock, self._process_lock():
            self.items = self._load()
            return self.items.get(doc_id)

    def list(self) -> list[dict[str, Any]]:
        """Return all registered document records."""

        with self._lock, self._process_lock():
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

        with self._lock, self._process_lock():
            self.items = self._load()
            return doc_id in self.items
