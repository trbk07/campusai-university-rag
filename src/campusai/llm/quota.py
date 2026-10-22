"""Single-host, durable admission for Gemini text requests.

Counters contain no credentials or prompts. Reservations are charged even on
failure/crash; releasing an in-flight lease never refunds the attempt. Token
reservations are estimates, reconciled upwards from returned provider usage.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sqlite3
import time
from uuid import uuid4
from zoneinfo import ZoneInfo


class QuotaExceeded(Exception):
    def __init__(self, reason, seconds=None):
        self.reason = reason
        self.retry_after_seconds = None if seconds is None else max(1, math.ceil(seconds))
        super().__init__('provider request exceeds local admission budget')


class QuotaStateError(Exception):
    """A stale worker cannot use a different policy for the same scope."""


@dataclass(frozen=True)
class QuotaPolicy:
    requests_per_minute: int
    input_tokens_per_minute: int | None = None
    requests_per_day: int | None = None
    total_tokens_per_day: int | None = None
    max_in_flight: int = 1

    def __post_init__(self):
        for name, value in asdict(self).items():
            if value is None and name not in {'requests_per_minute', 'max_in_flight'}:
                continue
            minimum = 0 if name == 'requests_per_minute' else 1
            if type(value) is not int or not minimum <= value <= 1_000_000_000:
                raise ValueError(f'quota {name} must be an integer >= {minimum}')


def estimate_gemini_tokens(body):
    """Conservative text-only estimate, NOT a guaranteed tokenizer bound.

    Count all serialized UTF-8 payload bytes plus framing headroom. This avoids
    a second paid/network token-count request. Keep the output ceiling reserved
    even when an answer is short. Unknown multimodal/cached input fails closed.
    """
    def unsupported(value):
        if isinstance(value, dict):
            return bool({'fileData', 'inlineData', 'cachedContent'} & value.keys()) or any(
                unsupported(item) for item in value.values())
        return isinstance(value, list) and any(unsupported(item) for item in value)

    if unsupported(body):
        raise ValueError('quota admission supports uncached text input only')
    config = body.get('generationConfig', {})
    output = config.get('maxOutputTokens')
    candidates = config.get('candidateCount', 1)
    if type(output) is not int or output < 1 or type(candidates) is not int or candidates < 1:
        raise ValueError('quota admission requires a positive maxOutputTokens and candidateCount')
    return len(json.dumps(body, ensure_ascii=False).encode('utf-8')) + 1024, output * candidates


class QuotaGovernor:
    """Atomic check-and-reserve across threads/processes using one SQLite file.

    One scope must cover every app credential/worker sharing a provider quota.
    Other apps and other machines are outside these counters. Reconfiguring a
    policy preserves usage and causes stale workers to fail closed.
    """
    def __init__(self, path, scope, policy, *, max_wait_seconds=2):
        if not isinstance(scope, str) or not scope.strip() or len(scope) > 200:
            raise ValueError('quota scope must be a nonempty logical project/model identity')
        if not isinstance(path, (str, Path)) or not str(path).strip() or str(path) == ':memory:':
            raise ValueError('quota state_path must be a durable file path')
        if (isinstance(max_wait_seconds, bool) or not isinstance(max_wait_seconds, (int, float))
                or not math.isfinite(max_wait_seconds) or not 0 <= max_wait_seconds <= 20):
            raise ValueError('quota max_wait_seconds must be between 0 and 20')
        self.path, self.scope, self.policy = Path(path), scope, policy
        self.max_wait_seconds = max_wait_seconds
        self.timezone = ZoneInfo('America/Los_Angeles')
        self.identity = json.dumps(asdict(policy), sort_keys=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS quota_state '
                       '(scope TEXT PRIMARY KEY, policy TEXT, last_seen REAL, next_start REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS quota_attempts '
                       '(id TEXT PRIMARY KEY, scope TEXT, started REAL, day TEXT, input_tokens INTEGER, '
                       'total_tokens INTEGER, lease_until REAL, actual_input_tokens INTEGER, actual_total_tokens INTEGER)')
            db.execute('CREATE INDEX IF NOT EXISTS quota_scope_start ON quota_attempts (scope, started)')
            db.execute('CREATE TABLE IF NOT EXISTS quota_observations '
                       '(scope TEXT, kind TEXT, quota_value INTEGER, observed_at REAL, PRIMARY KEY(scope, kind))')
            db.execute('INSERT INTO quota_state VALUES (?, ?, 0, 0) '
                       'ON CONFLICT(scope) DO UPDATE SET policy=excluded.policy', (scope, self.identity))

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=1)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        finally:
            db.close()

    def _day(self, now):
        local = datetime.fromtimestamp(now, self.timezone)
        tomorrow = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return local.date().isoformat(), tomorrow.timestamp() - now

    def _reserve_once(self, input_tokens, output_tokens, lease_seconds):
        p = self.policy
        total = input_tokens + output_tokens
        if ((p.input_tokens_per_minute is not None and input_tokens > p.input_tokens_per_minute)
                or (p.total_tokens_per_day is not None and total > p.total_tokens_per_day)):
            raise QuotaExceeded('request_too_large')
        with self.transaction() as db:
            policy, last_seen, next_start = db.execute(
                'SELECT policy, last_seen, next_start FROM quota_state WHERE scope=?', (self.scope,)).fetchone()
            if policy != self.identity:
                raise QuotaStateError('quota policy changed; restart stale worker')
            # A backwards wall-clock adjustment must not reopen a spent day.
            now = max(time.time(), last_seen)
            day, reset_after = self._day(now)
            rows = db.execute('SELECT started, day, input_tokens, total_tokens, lease_until '
                              'FROM quota_attempts WHERE scope=? ORDER BY started', (self.scope,)).fetchall()
            minute = [row for row in rows if row[0] > now - 60]
            daily = [row for row in rows if row[1] == day]
            leases = sorted(row[4] for row in rows if row[4] > now)
            delays = [(max(0, next_start - now), 'rpm_spacing')]
            if p.requests_per_minute and len(minute) >= p.requests_per_minute:
                delays.append((minute[len(minute) - p.requests_per_minute][0] + 60 - now, 'rpm'))
            if p.input_tokens_per_minute is not None:
                used = sum(row[2] for row in minute)
                for row in minute:
                    if used + input_tokens <= p.input_tokens_per_minute:
                        break
                    used -= row[2]
                    delays.append((row[0] + 60 - now, 'input_tpm'))
            if p.requests_per_day is not None and len(daily) >= p.requests_per_day:
                delays.append((reset_after, 'rpd'))
            if p.total_tokens_per_day is not None and sum(row[3] for row in daily) + total > p.total_tokens_per_day:
                delays.append((reset_after, 'total_tpd'))
            if len(leases) >= p.max_in_flight:
                delays.append((leases[len(leases) - p.max_in_flight] - now, 'in_flight'))
            delay, reason = max(delays)
            if delay > 0:
                return None, delay + max(0, now - time.time()), reason
            reservation = uuid4().hex
            db.execute('INSERT INTO quota_attempts VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)',
                       (reservation, self.scope, now, day, input_tokens, total, now + lease_seconds))
            interval = 60 / p.requests_per_minute if p.requests_per_minute else 0
            db.execute('UPDATE quota_state SET last_seen=?, next_start=? WHERE scope=?',
                       (now, now + interval, self.scope))
            # Retain today's accounting, the rolling minute and live leases.
            db.execute('DELETE FROM quota_attempts WHERE scope=? AND day<>? AND started<=? AND lease_until<=?',
                       (self.scope, day, now - 60, now))
            return reservation, 0, None

    def reserve(self, input_tokens, output_tokens, *, lease_seconds, check=None):
        for value in (input_tokens, output_tokens, lease_seconds):
            if type(value) is not int or value < 0:
                raise ValueError('quota reservation values must be nonnegative integers')
        if not lease_seconds:
            raise ValueError('quota lease_seconds must be positive')
        deadline = time.monotonic() + self.max_wait_seconds
        while True:
            if check is not None:
                check()
            reservation, delay, reason = self._reserve_once(input_tokens, output_tokens, lease_seconds)
            if reservation is not None:
                return reservation
            if delay > deadline - time.monotonic():
                raise QuotaExceeded(reason, delay)
            # No SQLite lock is held while waiting. Recheck outage/policy/state.
            time.sleep(min(delay, 0.25))

    def finish(self, reservation, usage=None):
        usage = usage if isinstance(usage, dict) else {}
        def count(name):
            value = usage.get(name)
            return value if type(value) is int and 0 <= value <= 1_000_000_000 else None
        actual_input, actual_total = count('promptTokenCount'), count('totalTokenCount')
        with self.transaction() as db:
            db.execute('UPDATE quota_attempts SET lease_until=0, input_tokens=MAX(input_tokens, ?), '
                       'total_tokens=MAX(total_tokens, ?, ?), actual_input_tokens=?, actual_total_tokens=? '
                       'WHERE id=? AND scope=?', (actual_input or 0, actual_total or 0, actual_input or 0,
                                                actual_input, actual_total, reservation, self.scope))

    def observe(self, observations):
        """Persist safe provider-reported limits; do not silently change policy."""
        allowed = {'requests_per_minute', 'requests_per_day', 'input_tokens_per_minute'}
        with self.transaction() as db:
            for item in observations:
                kind, value = item['kind'], item['value']
                if kind not in allowed or (value is not None and
                        (type(value) is not int or not 0 <= value <= 1_000_000_000)):
                    raise ValueError('invalid provider quota observation')
                db.execute('INSERT INTO quota_observations VALUES (?, ?, ?, ?) '
                           'ON CONFLICT(scope, kind) DO UPDATE SET quota_value=excluded.quota_value, '
                           'observed_at=excluded.observed_at', (self.scope, kind, value, time.time()))

    def snapshot(self):
        """Internal accounting, never a provider quota/entitlement lookup."""
        with self.transaction() as db:
            last_seen = db.execute('SELECT last_seen FROM quota_state WHERE scope=?', (self.scope,)).fetchone()[0]
            now = max(time.time(), last_seen)
            day, _ = self._day(now)
            rows = db.execute('SELECT started, day, input_tokens, total_tokens, lease_until '
                              'FROM quota_attempts WHERE scope=?', (self.scope,)).fetchall()
            observed = db.execute('SELECT kind, quota_value, observed_at FROM quota_observations '
                                  'WHERE scope=?', (self.scope,)).fetchall()
        result = {'day': day, 'day_timezone': str(self.timezone),
                'reserved_attempts_today': sum(row[1] == day for row in rows),
                'accounted_tokens_today': sum(row[3] for row in rows if row[1] == day),
                'reserved_attempts_last_minute': sum(row[0] > now - 60 for row in rows),
                'accounted_input_tokens_last_minute': sum(row[2] for row in rows if row[0] > now - 60),
                'in_flight': sum(row[4] > now for row in rows)}
        if observed:
            result['observed_provider_limits'] = {kind: {'value': value, 'observed_at': stamp}
                                                  for kind, value, stamp in observed}
        return result
