"""Record live staged retrieval requests and derive auditable canary windows."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from threading import Event, RLock, Thread
import time


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone required")
        return result
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("telemetry timestamp requires timezone") from error


def summarize_window(samples: list[dict], *, traffic_percent: int, ram_limit_bytes: int,
                     started_at: str, ended_at: str) -> dict:
    """No inferred zero: every sample must supply measured outcomes and gauges."""
    if not isinstance(samples, list) or len(samples) < 100:
        raise ValueError("at least 100 actual request observations required")
    start, end = timestamp(started_at), timestamp(ended_at)
    if end <= start or type(ram_limit_bytes) is not int or ram_limit_bytes <= 0:
        raise ValueError("invalid window interval or deployment RAM limit")
    if type(traffic_percent) is not int or traffic_percent not in (0, 1, 5, 10, 25):
        raise ValueError("invalid observed rollout percentage")
    ids = set()
    bool_fields = ("answerable", "error", "baseline_error", "has_results", "route_selected",
                   "rerank_selected", "fallback", "timeout")
    counts = ("queue_depth", "provenance_errors", "scope_errors", "citation_errors", "peak_rss_bytes")
    for sample in samples:
        if not isinstance(sample, dict) or not isinstance(sample.get("request_id"), str) or not sample["request_id"]:
            raise ValueError("observed request identity required")
        if sample["request_id"] in ids:
            raise ValueError("duplicate observed request identity")
        ids.add(sample["request_id"])
        if (any(type(sample.get(key)) is not bool for key in bool_fields)
                or sample.get("difficulty") not in {"easy", "medium", "hard"}
                or any(type(sample.get(key)) is not int or sample[key] < 0 for key in counts)
                or sample["peak_rss_bytes"] == 0
                or type(sample.get("latency_ms")) not in (int, float)
                or not math.isfinite(sample["latency_ms"]) or sample["latency_ms"] < 0):
            raise ValueError("missing measured request outcomes/resource gauges")
        req_start, req_end = timestamp(sample["started_at"]), timestamp(sample["ended_at"])
        if req_start < start or req_end > end or req_end < req_start:
            raise ValueError("request interval outside its window")
    negative = [s for s in samples if not s["answerable"]]
    easy = [s for s in samples if s["answerable"] and s["difficulty"] == "easy"]
    hard = [s for s in samples if s["answerable"] and s["difficulty"] == "hard"]
    if not negative or not easy or not hard:
        raise ValueError("negative/easy/hard observations required; absent cohorts cannot be reported as zero")
    latency = sorted(s["latency_ms"] for s in samples)
    n = len(samples)
    fraction = lambda key: sum(s[key] for s in samples) / n
    return {"traffic_percent": traffic_percent, "requests": n, "started_at": started_at, "ended_at": ended_at,
            **{f"p{int(p*100)}_ms": latency[max(0, math.ceil(n*p)-1)] for p in (.5, .95, .99)},
            "timeout_rate": fraction("timeout"), "negative_fpr": sum(s["has_results"] for s in negative) / len(negative),
            "error_rate": fraction("error"), "baseline_error_rate": fraction("baseline_error"),
            "fallback_rate": fraction("fallback"), "selection_rate": fraction("rerank_selected"),
            # Shadow routing uses the frozen policy on live Phase 6 evidence
            # for all cohorts, including 0%; labels never enter the route.
            "routing_metrics_scope": "frozen_policy_shadow_on_all_requests",
            "easy_unnecessary_rerank_rate": sum(s["route_selected"] for s in easy) / len(easy),
            "hard_query_coverage": sum(s["route_selected"] for s in hard) / len(hard),
            "peak_rss_bytes": max(s["peak_rss_bytes"] for s in samples), "ram_limit_bytes": ram_limit_bytes,
            "queue_depth": max(s["queue_depth"] for s in samples),
            **{key: sum(s[key] for s in samples) for key in ("provenance_errors", "scope_errors", "citation_errors")},
            "request_observations": samples}


def outcome_counts(output: list[dict], doc_ids: list[str], filters: dict, evidence: dict) -> dict:
    provenance = scope = citations = 0
    for item in output:
        frozen = evidence.get((item["doc_id"], item["chunk_id"]))
        invalid = not (frozen and item["page"] == frozen["page"] and item["content"] == frozen["content"])
        provenance += invalid
        metadata = item.get("metadata", {})
        expected_metadata = (frozen or {}).get("metadata", {})
        citations += invalid or type(item["page"]) is not int or any(
            metadata.get(key) != expected_metadata[key]
            for key in ("page_range", "source_hash", "table_id") if key in expected_metadata)
        scope += item["doc_id"] not in doc_ids or any(
            str(metadata.get(key, "")).casefold() != str(value).casefold()
            or str(expected_metadata.get(key, "")).casefold() != str(value).casefold()
            for key, value in filters.items())
    return {"provenance_errors": provenance, "scope_errors": scope, "citation_errors": citations}


def audit_window(window: dict, evidence=None) -> dict:
    """Reject scalar summaries that do not follow their raw observations."""
    result = summarize_window(window.get("request_observations"), traffic_percent=window["traffic_percent"],
                              ram_limit_bytes=window["ram_limit_bytes"], started_at=window["started_at"],
                              ended_at=window["ended_at"])
    resources = window.get("resource_observations", [])
    if not isinstance(resources, list):
        raise ValueError("invalid periodic resource observations")
    for gauge in resources:
        if (not isinstance(gauge, dict) or any(type(gauge.get(key)) is not int or gauge[key] < minimum
                for key, minimum in (("peak_rss_bytes", 1), ("queue_depth", 0)))
                or not timestamp(window["started_at"]) <= timestamp(gauge.get("observed_at")) <= timestamp(window["ended_at"])):
            raise ValueError("invalid periodic resource observation")
    if resources:
        for key in ("peak_rss_bytes", "queue_depth"):
            result[key] = max(result[key], max(g[key] for g in resources))
    if any(window.get(key) != value for key, value in result.items()):
        raise ValueError("staging summary does not match raw request/resource observations")
    if evidence is not None:
        for sample in result["request_observations"]:
            output = sample["output"]
            actual = outcome_counts(output, sample["doc_ids"], sample["filters"], evidence)
            if any(sample.get(key) != value for key, value in actual.items()) or sample["has_results"] != bool(output):
                raise ValueError("staging outcomes do not match frozen evidence")
    return result


class CanaryWindowRecorder:
    """Optional evaluation instrumentation around a real service, never a fixture generator."""
    def __init__(self, service, baseline, evidence: dict, *, ram_limit_bytes: int, resource_probe=None):
        self.service, self.baseline, self.evidence = service, baseline, evidence
        self.ram_limit_bytes = ram_limit_bytes
        self._lock = RLock()
        self._samples, self._ids = [], set()
        self._inflight = 0
        self._started_at = None
        self._traffic = None
        if resource_probe is None:
            import psutil
            process = psutil.Process()
            resource_probe = lambda: {"peak_rss_bytes": process.memory_info().rss,
                                      "queue_depth": service.retriever.phase7_provider.metrics_snapshot()["queue_depth"]}
        self._resource_probe = resource_probe
        self._stop = Event()
        self._sampler = None
        self._resource_error = None
        self._gauges = []

    def _sample_resources(self):
        try:
            gauge = self._resource_probe()
            if any(type(gauge.get(key)) is not int or gauge[key] < minimum
                   for key, minimum in (("peak_rss_bytes", 1), ("queue_depth", 0))):
                raise ValueError("invalid measured resource gauge")
            with self._lock:
                self._gauges.append({"observed_at": datetime.now(timezone.utc).isoformat(), **gauge})
            return gauge
        except Exception as error:
            with self._lock:
                self._resource_error = type(error).__name__
            raise

    def _sample_loop(self):
        while not self._stop.wait(.01):
            try:
                self._sample_resources()
            except Exception:
                return

    def close(self):
        self._stop.set()
        if self._sampler is not None:
            self._sampler.join()
            self._sampler = None

    def start(self):
        with self._lock:
            if self._started_at is not None:
                raise ValueError("a telemetry window is already open")
            if self.service.canary is None:
                raise ValueError("a live canary controller is required")
            self._traffic = self.service.canary.traffic_percent
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._samples, self._ids = [], set()
            self._gauges, self._resource_error = [], None
            self._sample_resources()
            self._stop.clear()
            self._sampler = Thread(target=self._sample_loop, name="canary-resource-sampler", daemon=True)
            self._sampler.start()

    def retrieve(self, row: dict, *, request_id: str):
        with self._lock:
            if self._started_at is None or request_id in self._ids:
                raise ValueError("open window and unique request ID required")
            if self.service.canary.traffic_percent != self._traffic:
                raise ValueError("traffic changed during an open observation window")
            self._ids.add(request_id)
            self._inflight += 1
        try:
            # Labels belong to the evaluator. Only question/scope/filter are
            # sent to either retriever or the routing policy.
            kwargs = {"doc_ids": row["doc_ids"], "filters": row.get("filters"), "top_k": 5}
            before_error, route_selected = False, False
            try:
                before = self.baseline.search(row["question"], mode="auto", **kwargs)
                route_selected, _ = self.service.retriever.phase7_policy.route(row["question"], before, self.baseline.last_trace)
            except Exception:
                before_error = True
            began = datetime.now(timezone.utc).isoformat()
            started = time.perf_counter()
            gauge_before = self._sample_resources()
            values, error, trace = [], False, None
            try:
                values = self.service.retrieve(row["question"], mode="phase7", request_id=request_id, **kwargs)
                trace = self.service.retriever.last_trace
            except Exception:
                error = True
            elapsed = (time.perf_counter() - started) * 1000
            ended = datetime.now(timezone.utc).isoformat()
            gauge_after = self._sample_resources()
            output = [item.to_dict() for item in values]
            counts = outcome_counts(output, row["doc_ids"], row.get("filters") or {}, self.evidence)
            reason = trace.rerank_reason if trace else None
            sample = {"request_id": request_id, "qid": row["qid"], "started_at": began, "ended_at": ended,
                      "answerable": row["answerable"], "difficulty": row["difficulty"], "latency_ms": elapsed,
                      "doc_ids": row["doc_ids"], "filters": row.get("filters") or {}, "output": output,
                      "error": error, "baseline_error": before_error, "has_results": bool(values),
                      "route_selected": bool(route_selected), "rerank_selected": bool(trace and trace.rerank_selected),
                      "timeout": reason == "reranker_timeout",
                      "fallback": bool(reason and reason not in {"easy_confident", "exact_or_abstained", "single_candidate", "hard_query"}
                                       and trace and not trace.rerank_selected),
                      **counts,
                      **{key: max(gauge_before[key], gauge_after[key]) for key in ("peak_rss_bytes", "queue_depth")}}
            with self._lock:
                self._samples.append(sample)
            return values
        finally:
            with self._lock:
                self._inflight -= 1

    def finish(self) -> dict:
        with self._lock:
            if self._started_at is None or self._inflight:
                raise ValueError("window is absent or requests are still in flight")
        self.close()
        with self._lock:
            if self._resource_error:
                raise ValueError("resource sampling failed: " + self._resource_error)
            # Each sample retains its request gauges; the window also retains
            # the periodically sampled process RSS and provider queue gauges.
            result = summarize_window(self._samples.copy(), traffic_percent=self._traffic,
                                      ram_limit_bytes=self.ram_limit_bytes, started_at=self._started_at,
                                      ended_at=datetime.now(timezone.utc).isoformat())
            result["resource_observations"] = self._gauges.copy()
            for key in ("peak_rss_bytes", "queue_depth"):
                result[key] = max(result[key], max(g[key] for g in self._gauges))
            self._started_at = None
            return result
