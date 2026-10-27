"""Fresh loopback upload-to-ready runs using real embeddings in an isolated store.

No answer provider is constructed. A native source must be completely readable;
every run checks exact parsed pages and both indexes before deleting its own upload.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import threading
import time

from . import benchmark_pdf_readiness as readiness


def inspect_ingestion(root, identifier, document, expected_text, expected_pages):
    from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION
    store, index = root/'store'/identifier, root/'index'/identifier
    meta = json.loads((store/'meta.json').read_text(encoding='utf8'))
    parsed = (store/'parsed.md').read_text(encoding='utf8')
    bm25 = json.loads((index/'bm25.json').read_text(encoding='utf8'))
    dense = json.loads((index/'dense.json').read_text(encoding='utf8'))
    if (meta['doc_id'] != identifier or meta['page_count'] != expected_pages
            or document['page_count'] != expected_pages or parsed != expected_text
            or meta['metadata'].get('text_coverage_version') != TEXT_COVERAGE_VERSION
            or meta['metadata'].get('unread_pages') or meta['metadata'].get('ocr')):
        raise ValueError('Native text/page/coverage integrity mismatch')
    chunks = {chunk['chunk_id']:chunk for chunk in meta['chunks']}
    expected_ids = set(chunks)
    for data in (bm25, dense):
        items = data['items']
        if (not expected_ids or len(items) != len(expected_ids)
                or {item['chunk_id'] for item in items} != expected_ids
                or any(item['doc_id'] != identifier or item['content'] != chunks[item['chunk_id']]['content']
                       or item['page'] != chunks[item['chunk_id']]['page'] for item in items)):
            raise ValueError('Index/document integrity mismatch')
    if (len(dense['vectors']) != len(expected_ids) or dense.get('model_name') != 'BAAI/bge-m3'
            or dense['manifest'].get('provider') != 'sentence-transformers'):
        raise ValueError('Dense vector coverage mismatch')
    return {'pages':expected_pages, 'exact_parsed_text':True,
            'parsed_sha256':hashlib.sha256(parsed.encode()).hexdigest(),
            'text_coverage_version':TEXT_COVERAGE_VERSION, 'chunks':len(expected_ids),
            'dense_manifest':dense['manifest'], 'bm25_sha256':hashlib.sha256((index/'bm25.json').read_bytes()).hexdigest(),
            'dense_sha256':hashlib.sha256((index/'dense.json').read_bytes()).hexdigest()}


def run(source, count, output, root, *, device='cuda'):
    from campusai.ingestion.docling_parser import parse_pdf
    from evaluation.common.release_artifacts import source_identity
    repo = Path(__file__).resolve().parents[2]
    root = root.resolve()
    if not 1 <= count <= 30 or not root.is_relative_to(repo/'.tmp') or root.exists() or output.exists():
        raise ValueError('Use a fresh isolated .tmp root and preserve prior output')
    pages = parse_pdf(source)
    if not pages or any(page['requires_ocr'] for page in pages):
        raise ValueError('This workload requires fully readable native pages')
    expected = '\n\n'.join(f"## Page {page['page']}\n{page['text']}" for page in pages)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    from campusai.api import CampusAIApplication
    from campusai.deployment.local_server import make_local_server, LocalRequestHandler
    from campusai.ingestion.jobs import IngestionJobManager
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.retrieval.dense_index import DenseIndex
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.web import make_wsgi_app
    import psutil
    import torch
    before = source_identity(repo)
    root.mkdir(parents=True)
    started = time.perf_counter()
    DenseIndex(model_name='BAAI/bge-m3', device=device)._provider().encode_query('CampusAI benchmark startup.')
    warm_seconds = time.perf_counter()-started
    app = CampusAIApplication(CampusAIQueryService(HybridRetriever(root/'index', dense_device=device),
        GroundedAnswerGenerator(None)), jobs=IngestionJobManager(max_workers=3, max_pending=8,
        journal_path=root/'jobs.sqlite3'), ingestion_defaults={'store_dir':root/'store',
        'index_dir':root/'index', 'dense_model':'BAAI/bge-m3', 'device':device})
    class Quiet(LocalRequestHandler):
        def log_message(self, *args): pass
    server = make_local_server('127.0.0.1', 0, make_wsgi_app(app))
    server.RequestHandlerClass = Quiet
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    old_base = readiness.BASE
    readiness.BASE = f'http://127.0.0.1:{server.server_port}'
    thread.start()
    try:
        result = readiness.measure(source, count, output, inspect_ready=lambda identifier, document:
            inspect_ingestion(root, identifier, document, expected, len(pages)))
        result.update(source_identity=before, source_identity_unchanged=source_identity(repo)==before,
            environment={'os':platform.platform(), 'python':platform.python_version(),
                'cpu':platform.processor(), 'logical_cpus':psutil.cpu_count(),
                'ram_bytes':psutil.virtual_memory().total, 'device':device,
                'gpu':torch.cuda.get_device_name() if device=='cuda' else None,
                'torch':torch.__version__, 'model':'BAAI/bge-m3', 'embedding_batch_size':8,
                'offline_models':True, 'ingestion_workers':3, 'http_url':readiness.BASE},
            model_startup_seconds=warm_seconds,
            workload='Warm model/OS cache; fresh upload, native parsing, table extraction, chunking, BM25 and real dense index on every run. Sequential uploads; no pre-existing user documents in isolated store.',
            criterion={'native_pages':100, 'source_bytes_min':10_000_000, 'p95_seconds_max':15,
                'passed':len(pages)==100 and source.stat().st_size>=10_000_000 and count>=20
                and result['p95_seconds']<=15 and source_identity(repo)==before})
        output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        print(json.dumps({key:result[key] for key in ('complete','source_bytes','p95_seconds','criterion')}),flush=True)
        return result
    finally:
        readiness.BASE = old_base
        server.shutdown(); server.server_close(); thread.join(); app.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--runs', type=int, default=20, choices=range(1,31))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--device', choices=('cpu','cuda'), default='cuda')
    args = parser.parse_args()
    run(args.source, args.runs, args.output, args.root, device=args.device)


if __name__ == '__main__': main()
