"""Dependency-free application adapter for a web/CLI transport.

The adapter keeps HTTP concerns out of ingestion and RAG logic while exposing
the contracts a frontend needs: health/readiness, asynchronous jobs, metrics,
and structured query responses. A FastAPI/WSGI adapter can call these methods
without duplicating business rules.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .ingestion.jobs import IngestionJobManager, JobQueueFull, JobStoreUnavailable
from .observability import MetricsRegistry
from .rag.service import CampusAIQueryService


class CampusAIApplication:
    def __init__(self, query_service: CampusAIQueryService,
                 jobs: IngestionJobManager | None = None,
                 metrics: MetricsRegistry | None = None,
                 ingestion_defaults: dict[str, Any] | None = None,
                 provider_failure_excerpts: bool = False) -> None:
        self.query_service = query_service
        self.jobs = jobs
        self.metrics = metrics or query_service.metrics
        self.ingestion_defaults = dict(ingestion_defaults or {})
        # Web uploads own the OCR workflow. Library/CLI ingestion retains its
        # explicit flags; operators may still disable automatic OCR here.
        self.ingestion_defaults.setdefault('enable_ocr', True)
        self.ingestion_defaults.setdefault('progressive_ocr', True)
        self.provider_failure_excerpts = provider_failure_excerpts

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "service": "campusai"}

    def query_timeout_ms(self) -> int:
        """Keep the browser deadline beyond bounded generation/source audit."""
        import math
        timeout = getattr(getattr(getattr(self.query_service, 'answer_generator', None), 'llm', None), 'timeout', None)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            return 45000
        # Initial generation plus one bounded full-source follow-up (and PDF
        # token measurement when enabled); no automatic infinite client wait.
        return max(45000, min(300000, math.ceil(timeout * 3000 + 15000)))

    def liveness(self) -> dict[str, Any]:
        """Process-level probe; dependency state belongs to readiness."""
        return {"status": "alive", "service": "campusai"}

    def readiness(self) -> dict[str, Any]:
        retriever = self.query_service.retriever
        index_exists = retriever.index_root.is_dir()
        policies = getattr(retriever, "policies", {})
        expected_indexes = {policy.index_sha256 for policy in policies.values() if policy.index_sha256}
        calibration_matches_index = True
        if expected_indexes:
            try:
                fingerprint = hashlib.sha256((retriever.index_root / "manifest.json").read_bytes()).hexdigest()
                calibration_matches_index = expected_indexes == {fingerprint}
            except OSError:
                calibration_matches_index = False
        llm_configured = getattr(getattr(self.query_service, "answer_generator", None), "llm", None) is not None
        phase7_enabled = getattr(retriever, "phase7_enabled", False)
        phase7_ready = bool(getattr(getattr(retriever, "phase7_provider", None), "ready", False))
        jobs_available = self.jobs is None or self.jobs.stats().get('store_available',True)
        ready = index_exists and calibration_matches_index and llm_configured and jobs_available and (not phase7_enabled or phase7_ready)
        return {"status": "ready" if ready else "not_ready", "index_root_exists": index_exists,
                "loaded_documents": len(retriever._indexes), "phase7_enabled": phase7_enabled,
                "phase7_ready": phase7_ready, "llm_configured": llm_configured,
                "calibration_matches_index": calibration_matches_index,"ingestion_available":jobs_available}

    def submit_ingestion(self, source_path: str, **options: Any) -> dict[str, Any]:
        if self.jobs is None:
            return {"ok": False, "error_code": "jobs_not_configured", "action": "configure_worker"}
        try:
            job_id = self.jobs.submit(source_path, **{**self.ingestion_defaults, **options})
        except JobQueueFull:
            return {'ok':False,'error_code':'ingestion_busy','retry_after_seconds':2}
        except JobStoreUnavailable:
            return {'ok':False,'error_code':'job_store_unavailable'}
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
        if getattr(answer, "reason", None) == "llm_error":
            # An operational outage is different from insufficient evidence.
            failure = (getattr(answer, "provider_failure", None)
                       or {"error_code": "provider_unavailable"})
            if self.provider_failure_excerpts:
                from .rag.excerpts import source_excerpts
                excerpts = source_excerpts(question, self.query_service.last_retrieval)
                if excerpts:
                    # Keep the answer abstained. The separate fallback is a
                    # source view, never a successful synthesized AI answer.
                    return {"ok": True, "answer": answer.to_public_dict(), "cache_hit": False,
                            "fallback": {"kind": "source_excerpts", "citations": excerpts},
                            "provider_status": failure}
            return {"ok": False, **failure}
        serializer = getattr(answer, "to_public_dict", answer.to_dict)
        response = {"ok": True, "answer": serializer(), "cache_hit": self.query_service.last_cache_hit}
        kind = getattr(getattr(self.query_service, '_request_local', None), 'conversation_kind', None)
        if kind:
            response['conversation_kind'] = kind
        context_question=getattr(getattr(self.query_service,'_request_local',None),'context_question',None)
        if isinstance(context_question,str) and context_question:
            response['context_question']=context_question
        return response

    def metrics_snapshot(self) -> dict[str, Any]:
        return self.metrics.as_dict()

    def close(self) -> None:
        """Gracefully stop worker and cache resources."""
        try:
            if self.jobs is not None:
                self.jobs.shutdown(wait=True)
        finally:
            self.query_service.close()
