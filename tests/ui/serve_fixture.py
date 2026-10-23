"""Isolated UI test host. Never use this deterministic provider in production."""
import argparse
from pathlib import Path
from campusai.deployment.local_server import make_local_server

from campusai.api import CampusAIApplication
from campusai.ingestion.jobs import IngestionJobManager
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app
from tests.test_web_documents import LocalEvidenceLLM, pdf_bytes
from tests.test_mixed_pdf import mixed_pdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8012)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    mixed_pdf.__wrapped__(args.root)
    (args.root/'Enrollment.pdf').write_bytes(pdf_bytes())
    for number in range(2, 11):
        (args.root/f'Enrollment-{number}.pdf').write_bytes(pdf_bytes(
            f'Enrollment requires approval from the academic advisor. Fixture source {number} has independent content.'))
    provider = LocalEvidenceLLM()
    service = CampusAIQueryService(HybridRetriever(args.root/'index'), GroundedAnswerGenerator(provider), default_mode='bm25')
    provider.evidence = lambda: service.last_retrieval[0]
    application = CampusAIApplication(service, jobs=IngestionJobManager(max_workers=3, max_pending=8,
        journal_path=args.root/"operations/jobs.sqlite3"), ingestion_defaults={
        'store_dir':args.root/'store','index_dir':args.root/'index','dense_model':'fallback-hash-256'})
    try:
        with make_local_server('127.0.0.1',args.port,
                make_wsgi_app(application,max_concurrent_queries=4)) as server:
            print(f'Isolated UI test host: http://127.0.0.1:{args.port}', flush=True)
            server.serve_forever()
    finally:
        application.close()


if __name__ == '__main__':
    main()
