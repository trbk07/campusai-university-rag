"""Background ingestion jobs for a responsive upload experience.

The UI should acknowledge an upload immediately and poll this manager instead
of waiting for parsing, table extraction, and optional dense indexing in the
request thread.
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .pipeline import ingest_document


@dataclass
class IngestionJob:
    job_id: str
    source_path: str
    state: str = "queued"
    stage: str = "queued"
    progress: float = 0.0
    document_id: str | None = None
    error: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    retryable: bool = False
    action: str | None = None
    created_at: float = 0.0
    updated_at: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    ingestion_status: str = "queued"
    index_status: str = "not_requested"
    ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IngestionJobManager:
    """Bounded background executor with observable progress and deduplication."""

    def __init__(self, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_workers))
        self._lock = threading.RLock()
        self._jobs: dict[str, IngestionJob] = {}
        self._futures: dict[str, Future] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._by_sha256: dict[str, str] = {}

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def submit(
        self,
        source_path: str | Path,
        *,
        store_dir: str | Path = "data/store",
        index_dir: str | Path | None = None,
        dense_model: str = "fallback-hash-256",
        device: str = "cpu",
        batch_size: int = 8,
        max_mb: int = 50,
        max_pages: int = 218,
        enable_ocr: bool = False,
        ocr_max_pages: int = 50,
        ocr_timeout_seconds: float = 120.0,
    ) -> str:
        path = Path(source_path).resolve()
        digest = self._sha256(path)
        now = time.time()
        with self._lock:
            existing = self._by_sha256.get(digest)
            if existing:
                existing_job = self._jobs.get(existing)
                # A failed attempt must be retryable from the UI. Keep
                # deduplication for queued/running/succeeded jobs, but replace
                # the SHA mapping after a failure.
                if existing_job is not None and existing_job.state != "failed":
                    return existing
            job = IngestionJob(
                job_id=uuid.uuid4().hex,
                source_path=str(path),
                created_at=now,
                updated_at=now,
            )
            self._jobs[job.job_id] = job
            self._by_sha256[digest] = job.job_id
            self._cancel_events[job.job_id] = threading.Event()
            self._futures[job.job_id] = self._executor.submit(
                self._run,
                job.job_id,
                path,
                store_dir,
                index_dir,
                dense_model,
                device,
                batch_size,
                max_mb,
                max_pages,
                enable_ocr,
                ocr_max_pages,
                ocr_timeout_seconds,
            )
            return job.job_id

    def _update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in values.items():
                setattr(job, key, value)
            job.updated_at = time.time()

    def _run(
        self,
        job_id: str,
        path: Path,
        store_dir: str | Path,
        index_dir: str | Path | None,
        dense_model: str,
        device: str,
        batch_size: int,
        max_mb: int,
        max_pages: int,
        enable_ocr: bool,
        ocr_max_pages: int,
        ocr_timeout_seconds: float,
    ) -> None:
        try:
            if self._cancel_events[job_id].is_set():
                self._update(job_id, state="cancelled", stage="cancelled", progress=1.0, ingestion_status="cancelled", completed_at=time.time())
                return
            started_at = time.time()
            self._update(
                job_id,
                state="running",
                stage="validating",
                progress=0.05,
                started_at=started_at,
                ingestion_status="running",
            )

            def progress(stage: str, value: float) -> None:
                if self._cancel_events[job_id].is_set():
                    raise RuntimeError("job_cancelled")
                stage_progress = {
                    "validating": (0.00, 0.08),
                    "parsing": (0.08, 0.45),
                    "ocr": (0.45, 0.75),
                    "detecting_metadata": (0.45, 0.55),
                    "extracting_tables": (0.55, 0.65),
                    "chunking": (0.65, 0.76),
                    "persisting": (0.76, 0.90),
                    "indexing": (0.90, 0.98),
                    "review_required": (0.90, 1.0),
                    "done": (1.0, 1.0),
                }
                start, end = stage_progress.get(stage, (0.05, 0.90))
                self._update(
                    job_id,
                    stage=stage,
                    progress=round(start + (end - start) * max(0.0, min(1.0, value)), 4),
                )

            document = ingest_document(
                path,
                store_dir=store_dir,
                max_mb=max_mb,
                max_pages=max_pages,
                progress=progress,
                enable_ocr=enable_ocr,
                ocr_max_pages=ocr_max_pages,
                ocr_timeout_seconds=ocr_timeout_seconds,
            )
            cancel_event = self._cancel_events[job_id]
            if cancel_event.is_set():
                self._update(job_id, state="cancelled", stage="cancelled", progress=1.0, action="cleanup", completed_at=time.time())
                return
            if index_dir is not None:
                self._update(job_id, index_status="running")
                self._update(job_id, stage="indexing", progress=0.90)
                from ..retrieval.index_builder import build_document_indexes

                build_document_indexes(
                    document,
                    index_dir,
                    dense_model=dense_model,
                    device=device,
                    batch_size=batch_size,
                )
                self._update(job_id, index_status="ready")
            if document.status == "review_required":
                self._update(
                    job_id,
                    state="review_required",
                    stage="review_required",
                    progress=1.0,
                    document_id=document.doc_id,
                    error=document.review_reason or "ocr_required",
                    error_code=document.review_reason or "ocr_required",
                    ingestion_status="review_required",
                    completed_at=time.time(),
                )
            else:
                self._update(
                    job_id,
                    state="succeeded",
                    stage="done",
                    progress=1.0,
                    document_id=document.doc_id,
                    ingestion_status="succeeded",
                    completed_at=time.time(),
                    ready=index_dir is not None,
                )
        except Exception as error:  # noqa: BLE001 - stored for UI diagnostics
            if str(error) == "job_cancelled":
                self._update(job_id, state="cancelled", stage="cancelled", progress=1.0, action="cleanup", completed_at=time.time(), ingestion_status="cancelled")
                return
            retryable = isinstance(error, (TimeoutError, OSError, ConnectionError))
            self._update(
                job_id,
                state="failed",
                stage="failed",
                error=f"{type(error).__name__}: {error}",
                error_code=type(error).__name__.lower(),
                retryable=retryable,
                action="retry" if retryable else "review_input",
                error_message=str(error),
                ingestion_status="failed",
                completed_at=time.time(),
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def list(self) -> list[dict[str, Any]]:
        """Return job summaries for a dashboard/admin endpoint."""
        with self._lock:
            return [job.to_dict() for job in self._jobs.values()]

    def stats(self) -> dict[str, int]:
        """Return queue state counts without exposing source contents."""
        with self._lock:
            counts: dict[str, int] = {}
            for job in self._jobs.values():
                counts[job.state] = counts.get(job.state, 0) + 1
            counts["active_workers"] = sum(1 for job in self._jobs.values() if job.state == "running")
            return counts

    def cancel(self, job_id: str) -> bool:
        """Request cooperative cancellation and release queued work when possible."""

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.state in {"succeeded", "failed", "review_required", "cancelled"}:
                return False
            self._cancel_events[job_id].set()
            future = self._futures.get(job_id)
            if future is not None and future.cancel():
                job.state = "cancelled"
                job.stage = "cancelled"
                job.progress = 1.0
                job.ingestion_status = "cancelled"
                job.completed_at = time.time()
                job.updated_at = time.time()
            return True

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)
