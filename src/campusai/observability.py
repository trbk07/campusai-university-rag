"""Small dependency-free metrics primitives for the web and worker layers."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
import threading
import time
from typing import Iterator


@dataclass(frozen=True)
class MetricSummary:
    count: int
    errors: int
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None


class MetricsRegistry:
    """Bounded in-process latency/error metrics with no secret or payload data."""

    def __init__(self, max_samples: int = 2048) -> None:
        self.max_samples = max(1, int(max_samples))
        self._lock = threading.RLock()
        self._samples: dict[str, list[float]] = defaultdict(list)
        self._errors: dict[str, int] = defaultdict(int)

    @contextmanager
    def observe(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        except Exception:
            with self._lock:
                self._errors[name] += 1
            raise
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            with self._lock:
                values = self._samples[name]
                values.append(elapsed)
                if len(values) > self.max_samples:
                    del values[: len(values) - self.max_samples]

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, round(percentile / 100 * len(ordered) + 0.5) - 1))
        return round(ordered[index], 3)

    def snapshot(self) -> dict[str, MetricSummary]:
        with self._lock:
            return {
                name: MetricSummary(
                    len(values), self._errors.get(name, 0),
                    self._percentile(values, 50), self._percentile(values, 95), self._percentile(values, 99),
                )
                for name, values in self._samples.items()
            }

    def as_dict(self) -> dict[str, dict]:
        return {name: summary.__dict__.copy() for name, summary in self.snapshot().items()}
