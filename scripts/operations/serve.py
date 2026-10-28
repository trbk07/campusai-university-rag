"""Run the dependency-free local WSGI shell.

This command is a transport smoke test. Production deployments should inject
real CampusAIApplication dependencies through their process entrypoint.
"""

from campusai.deployment.local_server import make_local_server as make_server
import os
import json
from pathlib import Path

from campusai.api import CampusAIApplication
from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.cache import RAGAnswerCache
from campusai.rag.document_scope import RegisteredDocumentScopeReader
from campusai.llm.client import _safe_endpoint
from campusai.retrieval.hybrid import HybridRetriever
from campusai.ingestion.jobs import IngestionJobManager
from campusai.web import make_wsgi_app
from campusai.retrieval.reranker_activation import build_phase7_retriever
from campusai.retrieval.canary_rollout import CanaryController
from campusai.llm.factory import create_llm, _read_config
from campusai.rag.calibration import load_calibration_artifact


def _load_answer_calibrator():
    path = os.getenv('CAMPUSAI_ANSWER_CALIBRATION')
    checksum = os.getenv('CAMPUSAI_ANSWER_CALIBRATION_SHA256')
    if bool(path) != bool(checksum):
        raise ValueError('Answer calibration requires both artifact path and pinned checksum')
    if not path:
        return None
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if (not isinstance(payload, dict) or payload.get('fit_split') != 'dev'
            or not isinstance(payload.get('benchmark_sha256'), str)
            or len(payload['benchmark_sha256']) != 64
            or any(ch not in '0123456789abcdef' for ch in payload['benchmark_sha256'])):
        raise ValueError('Answer calibration must declare dev-only fitting and its benchmark checksum')
    calibrator, _digest = load_calibration_artifact(path, expected_sha256=checksum)
    return calibrator


def build_application():
    answer_calibrator = _load_answer_calibrator()
    # The release corpus is evaluation-only. Runtime indexes are populated
    # exclusively from user uploads into the configured index directory.
    index_dir = Path(os.getenv("CAMPUSAI_INDEX_DIR", "data/index"))
    store_dir = Path(os.getenv("CAMPUSAI_STORE_DIR", "data/store"))
    device = os.getenv("CAMPUSAI_DEVICE", "cpu")
    # A frozen evaluation calibration binds its original corpus fingerprint.
    # User uploads form a different corpus. Deployments opt into their own
    # matching calibration explicitly; never silently bind the MVP to fixtures.
    calibration = Path(os.getenv("CAMPUSAI_RETRIEVAL_CALIBRATION", ""))
    if calibration.is_file():
        retriever = build_phase7_retriever(index_dir, calibration,
            Path(os.getenv("CAMPUSAI_RERANKER_DEV", "data/benchmark/human_retrieval_dev.jsonl")),
            dense_device=device)
    else:
        retriever = HybridRetriever(index_dir, dense_device=device)
    service = None
    llm = None
    jobs = None
    answer_cache = None
    try:
        llm_config = os.getenv("CAMPUSAI_LLM_CONFIG")
        llm = create_llm(llm_config) if llm_config else None
        rag = _read_config(llm_config).get('rag', {}) if llm_config else {}
        if (not isinstance(rag, dict) or set(rag) - {'context_candidates', 'max_context_chars', 'balanced_context', 'source_citations'}
                or type(rag.get('balanced_context', False)) is not bool
                or type(rag.get('source_citations', False)) is not bool
                or type(rag.get('max_context_chars', 12000)) is not int
                or not 1000 <= rag.get('max_context_chars', 12000) <= 12000
                or (rag.get('context_candidates') is not None and
                    (type(rag['context_candidates']) is not int or not 5 <= rag['context_candidates'] <= 12))):
            raise ValueError('Invalid bounded RAG context profile')
        cache_path = os.getenv('CAMPUSAI_RAG_CACHE_PATH')
        namespace = None
        if cache_path:
            answer_cache = RAGAnswerCache(cache_path)
            namespace = (type(llm).__name__ + ':' + _safe_endpoint(getattr(llm, 'endpoint', '')))
        active = getattr(retriever, "phase7_enabled", False)
        service = CampusAIQueryService(retriever, GroundedAnswerGenerator(llm,
            max_context_chars=rag.get('max_context_chars', 12000), balanced_context=rag.get('balanced_context', False),
            source_citations=rag.get('source_citations', False), calibrator=answer_calibrator),
            cache=answer_cache, cache_namespace=namespace,
            context_candidates=rag.get('context_candidates'),
            document_scope_reader=RegisteredDocumentScopeReader(store_dir,
                allow_pdf_scope=getattr(llm, 'allow_pdf_scope', False)),
            default_mode=None if active else "auto", canary=CanaryController() if active else None)
        jobs = IngestionJobManager(max_workers=int(os.getenv('CAMPUSAI_INGESTION_WORKERS','3')),
            max_pending=int(os.getenv('CAMPUSAI_INGESTION_PENDING','8')),
            journal_path=os.getenv('CAMPUSAI_JOB_DB',str(store_dir.parent/'operations/ingestion-jobs.sqlite3')))
        # Complete dense model/index initialization before HTTP can report ready.
        # This is local retrieval work only; it never asks the answer provider.
        warm_retrieval = getattr(retriever, "warm_up", None)
        if warm_retrieval is not None:
            warm_retrieval()
        return CampusAIApplication(
            service,
            jobs=jobs,
            ingestion_defaults={
                "store_dir": store_dir,
                "index_dir": index_dir,
                "dense_model": os.getenv("CAMPUSAI_DENSE_MODEL", "BAAI/bge-m3"),
                "device": device,
                "ocr_backend": os.getenv('CAMPUSAI_OCR_BACKEND','rapidocr'),
                "ocr_data_dir": os.getenv('CAMPUSAI_OCR_DATA_DIR') or None,
            },
            provider_failure_excerpts=True,
        )
    except Exception:
        if jobs is not None:
            jobs.shutdown()
        if service is not None:
            service.close()
        else:
            if answer_cache is not None:
                answer_cache.close()
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
        with make_server("127.0.0.1", 8000, make_wsgi_app(app,
                max_concurrent_queries=int(os.getenv('CAMPUSAI_QUERY_WORKERS', '4')),
                enable_query_streaming=os.getenv('CAMPUSAI_QUERY_STREAMING','0')=='1')) as server:
            print("CampusAI listening on http://127.0.0.1:8000")
            server.serve_forever()
    finally:
        app.close()


if __name__ == "__main__":
    main()
