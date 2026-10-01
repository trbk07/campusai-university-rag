"""Deterministic gradual canary admission and automatic Phase 6 rollback."""
from __future__ import annotations

import hashlib
import math
from threading import RLock
from typing import Callable

STEPS = (0, 1, 5, 10, 25)
RATES = ("timeout_rate", "negative_fpr", "error_rate", "baseline_error_rate", "fallback_rate",
         "selection_rate", "easy_unnecessary_rerank_rate", "hard_query_coverage")


class CanaryController:
    def __init__(self, rollback: Callable[[str], None] | None = None) -> None:
        self._lock = RLock()
        self._rollback = rollback
        self.traffic_percent = 0
        self._healthy_windows = 0
        self._latency_failures = 0
        self.rollback_reason: str | None = None

    def admits(self, request_id: str) -> bool:
        """Stable traffic cohort, independent of query text or language."""
        if not request_id:
            raise ValueError("stable request identity required")
        with self._lock:
            bucket = int(hashlib.sha256(request_id.encode()).hexdigest()[:8], 16) % 100
            return self.rollback_reason is None and bucket < self.traffic_percent

    def promote(self) -> int:
        with self._lock:
            if self.rollback_reason or self._healthy_windows < 3 or self.traffic_percent == STEPS[-1]:
                raise ValueError("canary promotion requires three healthy windows at the current step")
            self.traffic_percent = STEPS[STEPS.index(self.traffic_percent) + 1]
            self._healthy_windows = 0
            self._latency_failures = 0
            return self.traffic_percent

    def observe(self, window: dict) -> str | None:
        required = (*RATES, "requests", "p50_ms", "p95_ms", "p99_ms", "peak_rss_bytes", "ram_limit_bytes",
                    "queue_depth", "provenance_errors", "scope_errors", "citation_errors", "traffic_percent")
        if any(type(window.get(key)) not in (int, float) or not math.isfinite(window[key])
               or window[key] < 0 for key in required):
            raise ValueError("canary window missing finite metrics")
        if (any(window[key] > 1 for key in RATES) or window["requests"] < 100
                or window["ram_limit_bytes"] <= 0 or window["peak_rss_bytes"] <= 0
                or window["traffic_percent"] not in STEPS):
            raise ValueError("invalid canary metric domain or insufficient observations")
        callback = None
        with self._lock:
            if self.rollback_reason:
                return self.rollback_reason
            if window["traffic_percent"] != self.traffic_percent:
                # Recorded replay follows the same promotion policy as live traffic.
                if (STEPS.index(window["traffic_percent"]) != STEPS.index(self.traffic_percent) + 1
                        or self._healthy_windows < 3):
                    raise ValueError("canary traffic step skipped or insufficient healthy windows")
                self.traffic_percent = window["traffic_percent"]
                self._healthy_windows = 0
                self._latency_failures = 0
            self._latency_failures = self._latency_failures + 1 if window["p95_ms"] > 1000 else 0
            reason = None
            if window["provenance_errors"] > 0:
                reason = "provenance_error"
            elif window["scope_errors"] > 0:
                reason = "scope_leakage"
            elif window["citation_errors"] > 0:
                reason = "citation_error"
            elif window["timeout_rate"] > .01:
                reason = "timeout_budget"
            elif window["negative_fpr"] > .01:
                reason = "negative_fpr_budget"
            elif window["error_rate"] > window["baseline_error_rate"]:
                reason = "error_rate_regression"
            elif window["peak_rss_bytes"] > .75 * window["ram_limit_bytes"]:
                reason = "memory_budget"
            elif self._latency_failures >= 3:
                reason = "latency_budget_three_windows"
            if reason:
                self.rollback_reason = reason
                self.traffic_percent = 0
                callback = self._rollback
            else:
                healthy = window["p95_ms"] <= 1000 and window["p99_ms"] <= 2000
                if window["traffic_percent"]:
                    healthy &= window["easy_unnecessary_rerank_rate"] <= .25 and window["hard_query_coverage"] >= .90
                self._healthy_windows = self._healthy_windows + 1 if healthy else 0
        if callback:
            callback(reason)
        return reason


def rollback_retriever(retriever, reason: str = "operator_rollback") -> None:
    """Disable new inference and invalidate retrieval caches without rebuilding."""
    retriever.phase7_enabled = False
    retriever.phase7_activation_reason = reason
    with retriever._cache_lock:
        retriever._query_cache.clear()
        retriever._trace_cache.clear()
    provider = retriever.phase7_provider
    close = getattr(provider, "close", None)
    if close:
        close()
    # Answer cache keys include the active policy fingerprint and mode; after
    # disabling, the Phase 6 namespace cannot reuse an earlier Phase 7 answer.
