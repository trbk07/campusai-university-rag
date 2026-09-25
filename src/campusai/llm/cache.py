"""SQLite-backed cache for LLM responses.

The cache keeps the original response metadata on hits. File-backed caches
use SQLite's busy timeout and WAL mode; an in-memory cache keeps one connection
alive so its data and schema survive across ``get`` and ``put`` calls.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CachedResponse:
    """A response together with the provider metadata from the first call."""

    text: str
    usage: dict
    latency_ms: float
    created_at: float


class SQLiteLLMCache:
    """Store and retrieve responses using a small SQLite database."""

    def __init__(
        self,
        path: str = "data/cache/llm_cache.sqlite",
        *,
        timeout: float = 30.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.path = path
        self.timeout = timeout
        self._lock = threading.RLock()
        self._memory_connection: sqlite3.Connection | None = None

        if path != ":memory:":
            parent = os.path.dirname(path) or "."
            os.makedirs(parent, exist_ok=True)
        else:
            self._memory_connection = sqlite3.connect(
                ":memory:", check_same_thread=False, timeout=timeout
            )

        self._initialize()

    def _open(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection
        database = sqlite3.connect(self.path, timeout=self.timeout)
        database.execute(f"PRAGMA busy_timeout = {int(self.timeout * 1000)}")
        return database

    def _initialize(self) -> None:
        with self._lock:
            database = self._open()
            try:
                database.execute(
                    """
                    CREATE TABLE IF NOT EXISTS responses (
                        cache_key TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        usage TEXT NOT NULL,
                        latency_ms REAL NOT NULL,
                        created_at REAL NOT NULL
                    )
                    """
                )
                if self._memory_connection is None:
                    database.execute("PRAGMA journal_mode = WAL")
                database.commit()
            finally:
                if self._memory_connection is None:
                    database.close()

    def get(self, key: str) -> CachedResponse | None:
        """Return a cached response, or ``None`` when the key is unknown."""

        with self._lock:
            database = self._open()
            try:
                row = database.execute(
                    "SELECT text, usage, latency_ms, created_at "
                    "FROM responses WHERE cache_key = ?",
                    (key,),
                ).fetchone()
            finally:
                if self._memory_connection is None:
                    database.close()

        if row is None:
            return None
        return CachedResponse(
            text=row[0],
            usage=json.loads(row[1]),
            latency_ms=row[2],
            created_at=row[3],
        )

    def put(self, key: str, text: str, usage: dict, latency_ms: float) -> None:
        """Insert or replace one cached response."""

        serialized_usage = json.dumps(usage, sort_keys=True, ensure_ascii=False)
        with self._lock:
            database = self._open()
            try:
                database.execute(
                    "INSERT OR REPLACE INTO responses "
                    "(cache_key, text, usage, latency_ms, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (key, text, serialized_usage, latency_ms, time.time()),
                )
                database.commit()
            finally:
                if self._memory_connection is None:
                    database.close()

    def close(self) -> None:
        """Close the persistent in-memory connection, if one exists."""

        with self._lock:
            if self._memory_connection is not None:
                self._memory_connection.close()
                self._memory_connection = None

    def __enter__(self) -> "SQLiteLLMCache":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
