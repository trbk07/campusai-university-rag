"""Small thread-safe requests-per-minute limiter."""

from __future__ import annotations

import random
import threading
import time


class RateLimiter:
    """Space requests evenly over the configured minute."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        if requests_per_minute < 0:
            raise ValueError("requests_per_minute cannot be negative")

        self.interval_seconds = (
            60.0 / requests_per_minute if requests_per_minute else 0.0
        )
        self._next_allowed_time = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until the next request is allowed."""

        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_allowed_time - now)
            self._next_allowed_time = max(now, self._next_allowed_time)
            self._next_allowed_time += self.interval_seconds

        if delay > 0:
            time.sleep(delay)

    def backoff(self, attempt: int, retry_after: float | None = None) -> None:
        """Sleep for bounded exponential backoff, honoring provider hints."""
        if retry_after is None:
            retry_after = min(60.0, 0.5 * (2 ** max(0, attempt)) + random.random() * 0.25)
        time.sleep(min(60.0, max(0.0, retry_after)))
