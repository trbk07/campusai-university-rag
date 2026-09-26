"""Dependency-free application adapter for a web/CLI transport.

The adapter keeps HTTP concerns out of ingestion and RAG logic while exposing
the contracts a frontend needs: health/readiness, asynchronous jobs, metrics,
and structured query responses. A FastAPI/WSGI adapter can call these methods
without duplicating business rules.
"""

from __future__ import annotations

from typing import Any

from .ingestion.jobs import IngestionJobManager
from .observability import MetricsRegistry
from .rag.service import CampusAIQueryService


class CampusAIApplication:
    def __init__(self, query_service: CampusAIQueryService,
                 jobs: IngestionJobManager | None = None,
                 metrics: MetricsRegistry | None = None) -> None:
        self.query_service = query_service
        self.jobs = jobs
        self.metrics = metrics or query_service.metrics

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "service": "campusai"}

    def readiness(self) -> dict[str, Any]:
        retriever = self.query_service.retriever
        ready = retriever.index_root.exists()
        return {"status": "ready" if ready else "not_ready", "index_root_exists": ready,
                "loaded_documents": len(retriever._indexes)}

    def submit_ingestion(self, source_path: str, **options: Any) -> dict[str, Any]:
        if self.jobs is None:
            return {"ok": False, "error_code": "jobs_not_configured", "action": "configure_worker"}
        job_id = self.jobs.submit(source_path, **options)
        return {"ok": True, "job_id": job_id, "job": self.jobs.get(job_id)}

    def job(self, job_id: str) -> dict[str, Any]:
        if self.jobs is None:
            return {"ok": False, "error_code": "jobs_not_configured"}
        value = self.jobs.get(job_id)
        return {"ok": value is not None, "job": value,
                **({} if value is not None else {"error_code": "job_not_found"})}

    def jobs_snapshot(self) -> dict[str, Any]:
        if self.jobs is None:
            return {"jobs": [], "stats": {}}
        return {"jobs": self.jobs.list(), "stats": self.jobs.stats()}

    def query(self, question: str, **options: Any) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            return {"ok": False, "error_code": "empty_question", "action": "provide_question"}
        answer = self.query_service.ask(question, **options)
        serializer = getattr(answer, "to_public_dict", answer.to_dict)
        return {"ok": True, "answer": serializer(),
                "cache_hit": self.query_service.last_cache_hit}

    def metrics_snapshot(self) -> dict[str, Any]:
        return self.metrics.as_dict()
