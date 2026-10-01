"""Offline, bounded cross-encoder provider for opt-in Phase 7 experiments.

This provider never substitutes lexical scores for a failed model. Callers
must preserve their Phase 6 fused result when ``RerankerUnavailable`` occurs.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
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

    def __post_init__(self) -> None:
        supported_device = self.device == "cpu" or bool(re.fullmatch(r"cuda(?::[0-9]+)?", self.device))
        if (not self.model_name or not self.model_revision or not self.tokenizer_revision
                or self.tokenizer_revision != self.model_revision
                or len(self.model_sha256) != 64 or any(char not in "0123456789abcdef" for char in self.model_sha256)
                or self.provider != "sentence_transformers" or not supported_device
                or self.dtype != "float32" or not 1 <= self.batch_size <= 16
                or not 1 <= self.max_length <= 1024 or self.normalization != "raw_logit"):
            raise ValueError("invalid reranker model identity")
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
                 model_loader: Callable[[], object] | None = None) -> None:
        if not 1 <= candidate_cap <= 60 or not 1 <= timeout_ms <= 60000 or queue_limit < 0 or failure_limit < 1:
            raise ValueError("invalid reranker resource limits")
        self.model_identity = model_identity
        self.model_name = model_identity.model_name
        self.model_dir = Path(model_dir)
        if self.model_dir.name != model_identity.model_revision:
            raise ValueError("model snapshot revision mismatch")
        self.timeout_ms = timeout_ms
        self.candidate_cap = candidate_cap
        self.failure_limit = failure_limit
        self._permits = BoundedSemaphore(1 + queue_limit)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="phase7-reranker")
        self._submitted = self._completed = self._cancelled = self._rejected = 0
        self._pending = self._active = self._max_queue_depth = 0
        self._queue_wait_ms = self._max_queue_wait_ms = self._worker_ms = 0.0
        self._state_lock = Lock()
        self._idle = Condition(self._state_lock)
        self._failures = 0
        self._closed = False
        self._verified = False
        self._model = None
        self._loader = model_loader or (lambda: retrieval_runtime().get_offline_reranker(
            self.model_dir, device=model_identity.device,
            max_length=model_identity.max_length, snapshot_sha256=model_identity.model_sha256))

    @property
    def fingerprint(self) -> str:
        return self.model_identity.fingerprint

    def _predict(self, query: str, candidates: Sequence[RerankCandidate]) -> list[float]:
        self.verify_snapshot()
        if self._model is None:
            self._model = self._loader()
        model = self._model
        pairs = [(query[:2048], item.content[:8192]) for item in candidates]
        values = model.predict(pairs, batch_size=self.model_identity.batch_size,
                               show_progress_bar=False, activation_fn=lambda value: value)
        scores = [float(value) for value in values]
        if len(scores) != len(candidates) or any(not math.isfinite(value) for value in scores):
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
                    "closed": self._closed, "failure_count": self._failures}

    def _predict_queued(self, query, candidates, enqueued_at):
        started = time.perf_counter()
        waited = (started - enqueued_at) * 1000
        with self._state_lock:
            self._pending -= 1
            self._active += 1
            self._queue_wait_ms += waited
            self._max_queue_wait_ms = max(self._max_queue_wait_ms, waited)
        try:
            return self._predict(query, candidates)
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
        if not candidates:
            return []
        if not query.strip() or len(candidates) > self.candidate_cap:
            raise RerankerUnavailable("invalid_query_or_candidate_cap")
        ids = [(item.doc_id, item.chunk_id) for item in candidates]
        if (len(ids) != len(set(ids)) or len({item.candidate_id for item in candidates}) != len(candidates)
                or any(not item.candidate_id or not item.doc_id or not item.chunk_id
                       or isinstance(item.page, bool) or not isinstance(item.page, int) or item.page < 1
                       or item.original_rank < 1 or not math.isfinite(item.original_rrf_score)
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
                future = self._executor.submit(self._predict_queued, query, tuple(candidates), time.perf_counter())
                self._pending += 1
                self._submitted += 1
                self._max_queue_depth = max(self._max_queue_depth, max(0, self._pending - int(self._active == 0)))
            except Exception as error:
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
        self._executor.shutdown(wait=False, cancel_futures=True)
