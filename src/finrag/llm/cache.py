"""SQLite-backed cache for LLM responses.

The cache deliberately uses only the Python standard library. This keeps the
foundation easy to install and makes it straightforward to inspect locally.
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

    def __init__(self, path: str = "data/cache/llm_cache.sqlite") -> None:
        self.path = path
        self._lock = threading.Lock()

        if path != ":memory:":
            parent = os.path.dirname(path) or "."
            os.makedirs(parent, exist_ok=True)

        with sqlite3.connect(self.path) as database:
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

    def get(self, key: str) -> CachedResponse | None:
        """Return a cached response, or ``None`` when the key is unknown."""

        with self._lock, sqlite3.connect(self.path) as database:
            row = database.execute(
                "SELECT text, usage, latency_ms, created_at "
                "FROM responses WHERE cache_key = ?",
                (key,),
            ).fetchone()

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

        with self._lock, sqlite3.connect(self.path) as database:
            database.execute(
                "INSERT OR REPLACE INTO responses "
                "(cache_key, text, usage, latency_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, text, json.dumps(usage), latency_ms, time.time()),
            )
            database.commit()
