"""Persist endpoint overload cooldowns across workers, restarts and credentials.

Only health metadata is stored. An expired cooldown admits one real request,
never an extra probe; other callers fail fast until that request completes.
"""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time


class ProviderCoolingDown(Exception):
    def __init__(self, seconds):
        self.retry_after_seconds = max(1, int(seconds + 0.999))
        super().__init__("provider temporarily unavailable")


class OverloadCircuit:
    def __init__(self, path, endpoint, *, cooldown=60, maximum=300):
        self.path, self.endpoint = Path(path), endpoint
        self.cooldown, self.maximum = cooldown, maximum
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS overload (endpoint TEXT PRIMARY KEY, "
                       "failures INTEGER, until REAL, probe_until REAL, generation INTEGER)")
            db.execute("INSERT OR IGNORE INTO overload VALUES (?, 0, 0, 0, 0)", (endpoint,))

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=1)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        finally:
            db.close()

    def acquire(self, timeout):
        now = time.time()
        with self.transaction() as db:
            failures, until, probe_until, generation = db.execute(
                "SELECT failures, until, probe_until, generation FROM overload WHERE endpoint=?",
                (self.endpoint,)).fetchone()
            if max(until, probe_until) > now:
                raise ProviderCoolingDown(max(until, probe_until) - now)
            if failures:
                # A crashed recovery worker releases its lease after its timeout.
                db.execute("UPDATE overload SET probe_until=?, generation=generation+1 WHERE endpoint=?",
                           (now + timeout + 5, self.endpoint))
                generation += 1
            return generation

    def failed(self, generation, *, overloaded, retry_after=None):
        now = time.time()
        with self.transaction() as db:
            failures, current = db.execute(
                "SELECT failures, generation FROM overload WHERE endpoint=?", (self.endpoint,)).fetchone()
            if overloaded:
                failures += 1
                delay = min(self.maximum, self.cooldown * 2 ** min(failures - 1, 20))
                delay = max(delay, retry_after or 0)
                db.execute("UPDATE overload SET failures=?, until=?, probe_until=0, generation=generation+1 "
                           "WHERE endpoint=?", (failures, now + delay, self.endpoint))
            elif current == generation and failures:
                # A failed recovery still waits; do not allow a stream of probes.
                db.execute("UPDATE overload SET until=?, probe_until=0 WHERE endpoint=?",
                           (now + self.cooldown, self.endpoint))

    def check(self, generation):
        # Requests admitted while healthy may have waited in the rate limiter.
        # Recheck just before transport so a later 503 cancels queued work too.
        now = time.time()
        with self.transaction() as db:
            until, probe_until, current = db.execute(
                "SELECT until, probe_until, generation FROM overload WHERE endpoint=?",
                (self.endpoint,)).fetchone()
            if current != generation or until > now:
                raise ProviderCoolingDown(max(until, probe_until) - now)

    def succeeded(self, generation):
        with self.transaction() as db:
            # An older in-flight success must not undo a newer overload signal.
            db.execute("UPDATE overload SET failures=0, until=0, probe_until=0 "
                       "WHERE endpoint=? AND generation=?", (self.endpoint, generation))
