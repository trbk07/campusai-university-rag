"""Run the dependency-free local WSGI shell.

This command is a transport smoke test. Production deployments should inject
real CampusAIApplication dependencies through their process entrypoint.
"""

from wsgiref.simple_server import make_server
import os
from pathlib import Path

from campusai.api import CampusAIApplication
from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import HybridRetriever
from campusai.ingestion.jobs import IngestionJobManager
from campusai.web import make_wsgi_app
from campusai.retrieval.reranker_activation import build_phase7_retriever
from campusai.retrieval.canary_rollout import CanaryController
from campusai.llm.factory import create_llm


class NoProvider:
    def generate_json(self, *_args, **_kwargs):
        raise RuntimeError("LLM provider is not configured")


def build_application():
    # The release corpus is evaluation-only. Runtime indexes are populated
    # exclusively from user uploads into the configured index directory.
    index_dir = Path(os.getenv("CAMPUSAI_INDEX_DIR", "data/index"))
    store_dir = Path(os.getenv("CAMPUSAI_STORE_DIR", "data/store"))
    calibration = Path(os.getenv(
        "CAMPUSAI_RETRIEVAL_CALIBRATION",
        "evaluation/results/hybrid_retrieval_calibration.json",
    ))
    if calibration.is_file():
        retriever = build_phase7_retriever(index_dir, calibration,
            Path(os.getenv("CAMPUSAI_RERANKER_DEV", "data/benchmark/human_retrieval_dev.jsonl")))
    else:
        retriever = HybridRetriever(index_dir)
    service = None
    llm = None
    try:
        llm_config = os.getenv("CAMPUSAI_LLM_CONFIG")
        llm = create_llm(llm_config) if llm_config else NoProvider()
        active = getattr(retriever, "phase7_enabled", False)
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm),
            default_mode=None if active else "auto", canary=CanaryController() if active else None)
        jobs = IngestionJobManager(max_workers=int(os.getenv("CAMPUSAI_INGESTION_WORKERS", "1")))
        return CampusAIApplication(
            service,
            jobs=jobs,
            ingestion_defaults={
                "store_dir": store_dir,
                "index_dir": index_dir,
                "dense_model": os.getenv("CAMPUSAI_DENSE_MODEL", "BAAI/bge-m3"),
                "device": os.getenv("CAMPUSAI_DEVICE", "cpu"),
            },
        )
    except Exception:
        if service is not None:
            service.close()
        else:
            try:
                provider = getattr(retriever, "phase7_provider", None)
                if provider is not None:
                    provider.close()
            finally:
                close_llm = getattr(llm, "close", None)
                if close_llm is not None:
                    close_llm()
        raise


def main():
    app = build_application()
    try:
        with make_server("127.0.0.1", 8000, make_wsgi_app(app)) as server:
            print("CampusAI listening on http://127.0.0.1:8000")
            server.serve_forever()
    finally:
        app.close()


if __name__ == "__main__":
    main()
