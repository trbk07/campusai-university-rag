"""Offline, bounded cross-encoder provider for opt-in Phase 7 experiments.

This provider never substitutes lexical scores for a failed model. Callers
must preserve their Phase 6 fused result when ``RerankerUnavailable`` occurs.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from threading import Lock, BoundedSemaphore, Condition
import time
from typing import Callable, Protocol, Sequence

from .model_runtime import retrieval_runtime


class RerankerUnavailable(RuntimeError):
    """The guarded reranker cannot be used; keep the existing hybrid ranking."""


def snapshot_sha256(root: Path) -> str:
    """Hash relative filenames and file bytes, independent of local path."""
    if not root.is_dir():
        raise RerankerUnavailable("model_snapshot_missing")
    entries = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(root).as_posix()):
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        entries.append((path.relative_to(root).as_posix(), digest.hexdigest()))
    if not entries:
        raise RerankerUnavailable("model_snapshot_empty")
    return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ModelIdentity:
    model_name: str
    model_revision: str
    model_sha256: str
    tokenizer_revision: str
    provider: str = "sentence_transformers"
    device: str = "cpu"
    dtype: str = "float32"
    max_length: int = 512
    batch_size: int = 8
    normalization: str = "raw_logit"
    batch_window_ms: float = 0.0
    max_batch_pairs: int = 200

    def __post_init__(self) -> None:
        supported_device = self.device == "cpu" or bool(re.fullmatch(r"cuda(?::[0-9]+)?", self.device))
        if (not self.model_name or not self.model_revision or not self.tokenizer_revision
                or self.tokenizer_revision != self.model_revision
                or len(self.model_sha256) != 64 or any(char not in "0123456789abcdef" for char in self.model_sha256)
                or self.provider != "sentence_transformers" or not supported_device
                or self.dtype not in {"float32", "float16", "bfloat16"}
                or (self.device == "cpu" and self.dtype != "float32")
                or type(self.batch_size) is not int or not 1 <= self.batch_size <= (16 if self.device == "cpu" else 64)
                or type(self.max_length) is not int or not 1 <= self.max_length <= 1024 or self.normalization != "raw_logit"):
            raise ValueError("invalid reranker model identity")
        if (not math.isfinite(self.batch_window_ms) or not 0 <= self.batch_window_ms <= 10
                or type(self.max_batch_pairs) is not int or not 40 <= self.max_batch_pairs <= 400):
            raise ValueError("invalid inference batching identity")
        if any(marker in self.model_name for marker in ("\\", ":", "..")) or self.model_name.startswith("/"):
            raise ValueError("model_name must be a canonical repository ID, not a local path")

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RerankCandidate:
    candidate_id: str
    doc_id: str
    chunk_id: str
    page: int
    content: str
    original_rank: int
    original_rrf_score: float


@dataclass(frozen=True)
class RerankedCandidate:
    candidate_id: str
    doc_id: str
    chunk_id: str
    page: int
    original_rank: int
    original_rrf_score: float
    reranker_score: float
    final_rank: int
    model_identity: ModelIdentity


class RerankerProvider(Protocol):
    @property
    def model_identity(self) -> ModelIdentity: ...
    def score(self, query: str, candidates: Sequence[RerankCandidate]) -> list[RerankedCandidate]: ...


class OfflineCrossEncoderReranker:
    """One model per process, one inference worker, bounded pending requests."""

    def __init__(self, model_identity: ModelIdentity, model_dir: str | Path, *,
                 timeout_ms: int = 1000, candidate_cap: int = 40,
                 queue_limit: int = 2, failure_limit: int = 3,
                 score_cache_size: int = 0,
                 batch_window_ms: float | None = None, max_batch_pairs: int | None = None,
                 model_loader: Callable[[], object] | None = None) -> None:
        if (any(type(value) is not int for value in (candidate_cap, timeout_ms, queue_limit, failure_limit))
                or not 1 <= candidate_cap <= 60 or not 1 <= timeout_ms <= 60000
                or not 0 <= queue_limit <= 99 or failure_limit < 1):
            raise ValueError("invalid reranker resource limits")
        self.model_identity = model_identity
        self.model_name = model_identity.model_name
        self.model_dir = Path(model_dir)
        if self.model_dir.name != model_identity.model_revision:
            raise ValueError("model snapshot revision mismatch")
        self.timeout_ms = timeout_ms
        self.candidate_cap = candidate_cap
        self.failure_limit = failure_limit
        self.queue_limit = queue_limit
        self._permits = BoundedSemaphore(1 + queue_limit)
        self._submitted = self._completed = self._cancelled = self._rejected = 0
        self._pending = self._active = self._max_queue_depth = 0
        self._queue_wait_ms = self._max_queue_wait_ms = self._worker_ms = 0.0
        self._state_lock = Lock()
        self._idle = Condition(self._state_lock)
        self._failures = 0
        self._closed = False
        self._verified = False
        self._model = None
        if type(score_cache_size) is not int or not 0 <= score_cache_size <= 4096:
            raise ValueError("invalid score cache size")
        self._score_cache_size = score_cache_size
        self._score_cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self._cache_hits = 0
        batch_window_ms = model_identity.batch_window_ms if batch_window_ms is None else batch_window_ms
        max_batch_pairs = model_identity.max_batch_pairs if max_batch_pairs is None else max_batch_pairs
        if (batch_window_ms != model_identity.batch_window_ms or max_batch_pairs != model_identity.max_batch_pairs
                or not math.isfinite(batch_window_ms) or not 0 <= batch_window_ms <= 10
                or type(max_batch_pairs) is not int or not candidate_cap <= max_batch_pairs <= 400):
            raise ValueError("invalid inference batching limits")
        if score_cache_size and batch_window_ms:
            raise ValueError("batched inference uses uncached scores; enable the service answer cache instead")
        self._batch_window_ms = batch_window_ms
        self._max_batch_pairs = max_batch_pairs
        self._batch_queue = deque()
        self._batch_running = False
        self._inference_batches = self._max_batch_requests = 0
        self._loader = model_loader or (lambda: retrieval_runtime().get_offline_reranker(
            self.model_dir, device=model_identity.device,
            max_length=model_identity.max_length, snapshot_sha256=model_identity.model_sha256,
            dtype=model_identity.dtype))
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="phase7-reranker")

    @property
    def fingerprint(self) -> str:
        return self.model_identity.fingerprint

    @property
    def resource_limits(self) -> dict:
        return {"timeout_ms": self.timeout_ms, "queue_limit": self.queue_limit,
                "failure_limit": self.failure_limit, "score_cache_size": self._score_cache_size}

    def _predict(self, query: str, candidates: Sequence[RerankCandidate]) -> list[float]:
        return self._predict_pairs([(query[:2048], item.content[:8192]) for item in candidates])

    def _predict_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        self.verify_snapshot()
        if self._model is None:
            self._model = self._loader()
        model = self._model
        values = model.predict(pairs, batch_size=self.model_identity.batch_size,
                               show_progress_bar=False, activation_fn=lambda value: value)
        scores = [float(value) for value in values]
        if len(scores) != len(pairs) or any(not math.isfinite(value) for value in scores):
            raise RerankerUnavailable("invalid_model_scores")
        return scores

    def verify_snapshot(self) -> None:
        """Verify identity before activation without importing/loading the model."""
        if not self._verified:
            if snapshot_sha256(self.model_dir) != self.model_identity.model_sha256:
                raise RerankerUnavailable("model_checksum_mismatch")
            self._verified = True

    def metrics_snapshot(self) -> dict:
        """Actual admission/worker counters, including outstanding timed-out work."""
        with self._state_lock:
            return {"submitted_requests": self._submitted, "completed_requests": self._completed,
                    "cancelled_requests": self._cancelled, "rejected_requests": self._rejected,
                    "active_requests": self._active, "queue_depth": max(0, self._pending - int(self._active == 0)),
                    "max_queue_depth": self._max_queue_depth, "queue_wait_ms_total": self._queue_wait_ms,
                    "max_queue_wait_ms": self._max_queue_wait_ms, "worker_ms_total": self._worker_ms,
                    "closed": self._closed, "failure_count": self._failures,
                    "score_cache_hits": self._cache_hits, "score_cache_entries": len(self._score_cache),
                    "inference_batches": self._inference_batches, "max_batch_requests": self._max_batch_requests}

    def _drain_batches(self):
        """One worker coalesces pending requests; outputs remain per-request.

        Cancelled queued requests never reach the model. Running native work
        holds admission until it actually finishes, including after timeout.
        """
        while True:
            jobs = []
            with self._idle:
                if self._closed or not self._batch_queue:
                    self._batch_running = False
                    return
                self._idle.wait(self._batch_window_ms / 1000)
                count = 0
                while self._batch_queue:
                    future, query, candidates, enqueued = self._batch_queue[0]
                    if future.cancelled():
                        self._batch_queue.popleft()
                        continue
                    if count + len(candidates) > self._max_batch_pairs:
                        break
                    self._batch_queue.popleft()
                    if not future.set_running_or_notify_cancel():
                        continue
                    if self._closed:
                        # close() cancels queued futures outside the state lock.
                        # Leave this future running only until cleanup below.
                        jobs.append((future, query, candidates, enqueued))
                        break
                    jobs.append((future, query, candidates, enqueued))
                    count += len(candidates)
                self._pending -= len(jobs)
                self._active += len(jobs)
                now = time.perf_counter()
                for _, _, _, enqueued in jobs:
                    waited = (now - enqueued) * 1000
                    self._queue_wait_ms += waited
                    self._max_queue_wait_ms = max(self._max_queue_wait_ms, waited)
            if not jobs:
                continue
            started = time.perf_counter()
            outputs, error = [], None
            try:
                if self._closed:
                    raise RerankerUnavailable("feature_disabled")
                pairs = [(query[:2048], item.content[:8192]) for _, query, candidates, _ in jobs for item in candidates]
                scores = self._predict_pairs(pairs)
                offset = 0
                for _, _, candidates, _ in jobs:
                    outputs.append(scores[offset:offset + len(candidates)])
                    offset += len(candidates)
                with self._state_lock:
                    self._inference_batches += 1
                    self._max_batch_requests = max(self._max_batch_requests, len(jobs))
            except Exception as exc:
                error = exc
            finally:
                with self._idle:
                    self._active -= len(jobs)
                    self._completed += len(jobs)
                    self._worker_ms += (time.perf_counter() - started) * 1000
                    self._idle.notify_all()
            for index, (future, _, _, _) in enumerate(jobs):
                if error is not None:
                    future.set_exception(error)
                else:
                    future.set_result(outputs[index])

    def _score_key(self, query, candidates):
        payload = [self.fingerprint, query,
                   [(c.candidate_id, c.doc_id, c.chunk_id, c.page, c.content) for c in candidates]]
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

    def _predict_queued(self, query, candidates, enqueued_at):
        started = time.perf_counter()
        waited = (started - enqueued_at) * 1000
        with self._state_lock:
            self._pending -= 1
            self._active += 1
            self._queue_wait_ms += waited
            self._max_queue_wait_ms = max(self._max_queue_wait_ms, waited)
        try:
            key = self._score_key(query, candidates)
            with self._state_lock:
                cached = self._score_cache.get(key)
                if cached is not None:
                    self._score_cache.move_to_end(key)
                    self._cache_hits += 1
                    return list(cached)
            scores = self._predict(query, candidates)
            with self._state_lock:
                if self._score_cache_size and not self._closed:
                    self._score_cache[key] = tuple(scores)
                    while len(self._score_cache) > self._score_cache_size:
                        self._score_cache.popitem(last=False)
            return scores
        finally:
            with self._state_lock:
                self._active -= 1
                self._completed += 1
                self._worker_ms += (time.perf_counter() - started) * 1000
                self._idle.notify_all()

    def _release_admission(self, future):
        if future.cancelled():
            with self._state_lock:
                self._pending -= 1
                self._cancelled += 1
                self._idle.notify_all()
        self._permits.release()

    def score(self, query: str, candidates: Sequence[RerankCandidate], *,
              timeout_ms: int | None = None) -> list[RerankedCandidate]:
        if timeout_ms is not None and (type(timeout_ms) is not int or not 1 <= timeout_ms <= 60000):
            raise ValueError("invalid inference timeout override")
        if not candidates:
            return []
        if not query.strip() or len(candidates) > self.candidate_cap:
            raise RerankerUnavailable("invalid_query_or_candidate_cap")
        ids = [(item.doc_id, item.chunk_id) for item in candidates]
        if (len(ids) != len(set(ids)) or len({item.candidate_id for item in candidates}) != len(candidates)
                or any(not item.candidate_id or not item.doc_id or not item.chunk_id
                       or isinstance(item.page, bool) or not isinstance(item.page, int) or item.page < 1
                       or type(item.original_rank) is not int or item.original_rank < 1
                       or type(item.original_rrf_score) not in (int, float) or not math.isfinite(item.original_rrf_score)
                       for item in candidates)):
            raise RerankerUnavailable("invalid_candidate_provenance")
        with self._state_lock:
            if self._closed:
                self._rejected += 1
                raise RerankerUnavailable("feature_disabled")
            if self._failures >= self.failure_limit:
                self._rejected += 1
                raise RerankerUnavailable("circuit_open")
            if not self._permits.acquire(blocking=False):
                self._rejected += 1
                raise RerankerUnavailable("queue_full")
            try:
                if self._batch_window_ms:
                    future = Future()
                    self._batch_queue.append((future, query, tuple(candidates), time.perf_counter()))
                    if not self._batch_running:
                        self._batch_running = True
                        self._executor.submit(self._drain_batches)
                else:
                    future = self._executor.submit(self._predict_queued, query, tuple(candidates), time.perf_counter())
                self._pending += 1
                self._submitted += 1
                self._max_queue_depth = max(self._max_queue_depth, max(0, self._pending - int(self._active == 0)))
            except Exception as error:
                if self._batch_window_ms:
                    self._batch_queue.pop()
                    self._batch_running = False
                self._permits.release()
                raise RerankerUnavailable("reranker_submit_failed") from error
        future.add_done_callback(self._release_admission)
        try:
            scores = future.result(timeout=(self.timeout_ms if timeout_ms is None else timeout_ms) / 1000)
        except FutureTimeout as error:
            future.cancel()
            self._record_failure()
            raise RerankerUnavailable("reranker_timeout") from error
        except Exception as error:
            self._record_failure()
            raise RerankerUnavailable(str(error) if isinstance(error, RerankerUnavailable)
                                      else "reranker_inference_failed") from error
        with self._state_lock:
            if self._closed:
                raise RerankerUnavailable("feature_disabled")
            self._failures = 0
        ranked = sorted(zip(candidates, scores),
                        key=lambda pair: (-pair[1], pair[0].original_rank, pair[0].candidate_id))
        return [RerankedCandidate(item.candidate_id, item.doc_id, item.chunk_id, item.page,
                                  item.original_rank, item.original_rrf_score, score, rank,
                                  self.model_identity)
                for rank, (item, score) in enumerate(ranked, 1)]

    def _record_failure(self) -> None:
        with self._state_lock:
            self._failures += 1

    def reset_circuit(self) -> None:
        with self._state_lock:
            self._failures = 0

    def warm_up(self) -> None:
        """Explicit startup probe; callers control activation on failure."""
        self.score("model readiness probe", [RerankCandidate(
            "warmup", "warmup", "warmup", 1, "Model readiness probe.", 1, 1.0)], timeout_ms=60000)

    def drain(self, timeout_ms: int = 60000) -> None:
        """Wait for prior inference to finish between offline capacity profiles."""
        deadline = time.monotonic() + timeout_ms / 1000
        with self._idle:
            while self._active or self._pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RerankerUnavailable("reranker_drain_failed")
                self._idle.wait(remaining)

    def close(self) -> None:
        with self._state_lock:
            self._closed = True
            self._score_cache.clear()
            queued = [job[0] for job in self._batch_queue]
        for future in queued:
            future.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
