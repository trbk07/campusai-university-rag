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


class NoProvider:
    def generate_json(self, *_args, **_kwargs):
        raise RuntimeError("LLM provider is not configured")


def main():
    # The release corpus is evaluation-only. Runtime indexes are populated
    # exclusively from user uploads into the configured index directory.
    index_dir = Path(os.getenv("CAMPUSAI_INDEX_DIR", "data/index"))
    store_dir = Path(os.getenv("CAMPUSAI_STORE_DIR", "data/store"))
    calibration = Path(os.getenv(
        "CAMPUSAI_RETRIEVAL_CALIBRATION",
        "evaluation/results/phase6_retrieval_calibration.json",
    ))
    if calibration.is_file():
        retriever = HybridRetriever.with_calibration_report(index_dir, calibration)
    else:
        retriever = HybridRetriever(index_dir)
    service = CampusAIQueryService(
        retriever, GroundedAnswerGenerator(NoProvider()), default_mode="auto"
    )
    jobs = IngestionJobManager(max_workers=int(os.getenv("CAMPUSAI_INGESTION_WORKERS", "1")))
    app = CampusAIApplication(
        service,
        jobs=jobs,
        ingestion_defaults={
            "store_dir": store_dir,
            "index_dir": index_dir,
            "dense_model": os.getenv("CAMPUSAI_DENSE_MODEL", "BAAI/bge-m3"),
            "device": os.getenv("CAMPUSAI_DEVICE", "cpu"),
        },
    )
    with make_server("127.0.0.1", 8000, make_wsgi_app(app)) as server:
        print("CampusAI listening on http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    main()
