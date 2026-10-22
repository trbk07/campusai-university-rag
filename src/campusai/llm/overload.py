"""Persist endpoint overload/rate-limit cooldowns across workers and restarts.

Only health metadata is stored. An expired cooldown admits one real request,
never an extra probe; other callers fail fast until that request completes.
"""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
import math


class ProviderCoolingDown(Exception):
    def __init__(self, seconds, error_code="provider_overloaded"):
        self.retry_after_seconds = max(1, int(seconds + 0.999))
        self.provider_error_code = error_code
        super().__init__("provider temporarily unavailable")


class OverloadCircuit:
    def __init__(self, path, endpoint, *, cooldown=60, maximum=300):
        self.path, self.endpoint = Path(path), endpoint
        self.cooldown, self.maximum = cooldown, maximum
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS overload (endpoint TEXT PRIMARY KEY, "
                       "failures INTEGER, until REAL, probe_until REAL, generation INTEGER)")
            # Keep the original five-column table writable by older releases.
            db.execute('CREATE TABLE IF NOT EXISTS provider_failure_reason '
                       '(endpoint TEXT PRIMARY KEY, error_code TEXT NOT NULL)')
            if 'error_code' in {row[1] for row in db.execute('PRAGMA table_info(overload)')}:
                db.execute('INSERT OR IGNORE INTO provider_failure_reason SELECT endpoint, error_code FROM overload')
            db.execute("INSERT OR IGNORE INTO overload "
                       "(endpoint, failures, until, probe_until, generation) VALUES (?, 0, 0, 0, 0)", (endpoint,))
            db.execute("INSERT OR IGNORE INTO provider_failure_reason VALUES (?, 'provider_overloaded')", (endpoint,))

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
            failures, until, probe_until, generation, code = db.execute(
                "SELECT failures, until, probe_until, generation, error_code FROM overload JOIN provider_failure_reason USING(endpoint) WHERE endpoint=?",
                (self.endpoint,)).fetchone()
            if max(until, probe_until) > now:
                raise ProviderCoolingDown(max(until, probe_until) - now, code)
            if failures:
                # A crashed recovery worker releases its lease after its timeout.
                db.execute("UPDATE overload SET probe_until=?, generation=generation+1 WHERE endpoint=?",
                           (now + timeout + 5, self.endpoint))
                generation += 1
            return generation

    def failed(self, generation, *, overloaded, rate_limited=False, retry_after=None):
        now = time.time()
        if not isinstance(retry_after, (int, float)) or not math.isfinite(retry_after):
            retry_after = None
        with self.transaction() as db:
            failures, current, until = db.execute(
                "SELECT failures, generation, until FROM overload WHERE endpoint=?", (self.endpoint,)).fetchone()
            if overloaded or rate_limited:
                failures += 1
                delay = min(self.maximum, self.cooldown * 2 ** min(failures - 1, 20))
                delay = max(delay, retry_after or 0)
                code = 'provider_rate_limited' if rate_limited else 'provider_overloaded'
                db.execute("UPDATE overload SET failures=?, until=?, probe_until=0, generation=generation+1 "
                           "WHERE endpoint=?", (failures, max(until, now + delay), self.endpoint))
                db.execute('UPDATE provider_failure_reason SET error_code=? WHERE endpoint=?', (code, self.endpoint))
            elif current == generation and failures:
                # A failed recovery still waits; do not allow a stream of probes.
                db.execute("UPDATE overload SET until=?, probe_until=0 WHERE endpoint=?",
                           (now + self.cooldown, self.endpoint))

    def check(self, generation):
        # Requests admitted while healthy may have waited in the rate limiter.
        # Recheck just before transport so a later 503 cancels queued work too.
        now = time.time()
        with self.transaction() as db:
            until, probe_until, current, code = db.execute(
                "SELECT until, probe_until, generation, error_code FROM overload JOIN provider_failure_reason USING(endpoint) WHERE endpoint=?",
                (self.endpoint,)).fetchone()
            if current != generation or until > now:
                raise ProviderCoolingDown(max(until, probe_until) - now, code)

    def remaining_seconds(self):
        """Read cooldown without admitting a probe or calling the provider."""
        with self.transaction() as db:
            until, probe_until = db.execute(
                "SELECT until, probe_until FROM overload JOIN provider_failure_reason USING(endpoint) WHERE endpoint=?",
                (self.endpoint,)).fetchone()
        return max(0, int(max(until, probe_until) - time.time() + 0.999))

    def succeeded(self, generation):
        with self.transaction() as db:
            # An older in-flight success must not undo a newer overload signal.
            db.execute("UPDATE overload SET failures=0, until=0, probe_until=0 "
                       "WHERE endpoint=? AND generation=?", (self.endpoint, generation))

    def abandon(self, generation):
        """Release a recovery lease when local admission stopped before send."""
        with self.transaction() as db:
            db.execute('UPDATE overload SET probe_until=0 WHERE endpoint=? AND generation=?',
                       (self.endpoint, generation))
