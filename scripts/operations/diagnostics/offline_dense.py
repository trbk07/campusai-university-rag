"""Qualify a verified local encoder, without cloud/provider/network claims."""
import argparse
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import socket
import time
from types import SimpleNamespace

from campusai.deployment.config.preflight import sha
from campusai.deployment.runtime.models import pinned_retriever
from campusai.retrieval.index_builder import build_document_indexes
from campusai.retrieval.dense_index import DenseIndex
from campusai.retrieval.model_runtime import retrieval_runtime
from campusai.schemas import Chunk, Document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--workdir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists() or args.workdir.exists():
        parser.error('Use new output/workdir paths; do not overwrite a previous run')
    args.workdir.mkdir(parents=True)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    attempts = []
    def no_network(_socket, address):
        attempts.append(type(address).__name__)
        raise RuntimeError('network disabled for offline model verification')
    socket.socket.connect = no_network
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    settings = SimpleNamespace(dense_snapshot=args.snapshot.resolve(),
        dense_model=manifest['model'],dense_revision=manifest['revision'],
        dense_manifest_sha256=sha(args.manifest),config_root=args.manifest.parent.resolve(),
        indexes=args.workdir/'index')
    report = {'status':'NOT_PASSED','scope':'Existing local Windows/AMD64 snapshot; not ARM64/cloud or answer-quality acceptance',
        'platform':{'system':platform.system(),'architecture':platform.machine(),
                    'python':platform.python_version()},
        'model':settings.dense_model,'revision':settings.dense_revision,
        'manifest_sha256':settings.dense_manifest_sha256,'provider_calls':0,
        'network_connection_attempts':attempts,
        'packages':{name:version(name) for name in ('torch','sentence-transformers','transformers')},
        'sources_sha256':{name:sha(Path(name)) for name in (
            'scripts/operations/diagnostics/offline_dense.py','src/campusai/deployment/runtime/models.py',
            'src/campusai/deployment/config/preflight.py','src/campusai/retrieval/model_runtime.py',
            'src/campusai/retrieval/dense_index.py','src/campusai/retrieval/hybrid.py',
            'src/campusai/retrieval/index_builder.py')}}
    started = time.perf_counter()
    try:
        import torch
        torch.set_num_threads(2)
        retriever = pinned_retriever(settings)
        document = Document('offline-fixture','offline-fixture.pdf',1,language='en',chunks=[
            Chunk('stack-fixture','offline-fixture',1,'A stack removes the most recently added item.'),
            Chunk('queue-fixture','offline-fixture',1,'A queue removes the least recently added item.')])
        build_document_indexes(document,settings.indexes,dense_model=settings.dense_model,
                               model_revision=settings.dense_revision,device='cpu')
        dense = DenseIndex.load(settings.indexes/'offline-fixture/dense.json',
            expected_model_name=settings.dense_model,expected_model_revision=settings.dense_revision)
        retriever.warm_up()
        results = retriever.search('Which item does a stack remove?',doc_ids=['offline-fixture'],mode='hybrid_rrf')
        first = retrieval_runtime().get_encoder(settings.dense_model,revision=settings.dense_revision)
        second = retrieval_runtime().get_encoder(settings.dense_model,revision=settings.dense_revision)
        norms = [math.sqrt(sum(v*v for v in vector)) for vector in dense.vectors]
        assert first is second and len(retrieval_runtime().loaded_models()) == 1
        assert dense.manifest['embedding_dimension'] == 1024
        assert all(math.isfinite(n) and abs(n-1)<0.0001 for n in norms)
        assert results and not attempts
        report.update(status='PASS',actual_encoder_instances=1,device='cpu',
            embedding_dimension=dense.manifest['embedding_dimension'],
            persisted_revision=dense.model_revision,vector_norm_range=[min(norms),max(norms)],
            retrieval_count=len(results),elapsed_ms=(time.perf_counter()-started)*1000,
            vector_sha256=hashlib.sha256(json.dumps(dense.vectors).encode()).hexdigest())
    except Exception as error:
        report['error_type'] = type(error).__name__
        raise
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('status','platform','actual_encoder_instances',
        'device','embedding_dimension','elapsed_ms','provider_calls','network_connection_attempts')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
