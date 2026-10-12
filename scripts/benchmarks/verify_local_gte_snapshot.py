"""Build an immutable GTE snapshot from local bytes and two pinned public origins.

Downloads public metadata only; no corpus, benchmark or credentials are sent.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen

from evaluation.common.release_artifacts import sha256, write_json
from evaluation.reranker.model_origin import verified_model_origin

MODEL = 'Alibaba-NLP/gte-multilingual-reranker-base'
REVISION = '8215cf04918ba6f7b6a62bb44238ce2953d8831c'
IMPLEMENTATION = 'Alibaba-NLP/new-impl'
IMPLEMENTATION_REVISION = '40ced75c3017eb27626c9d4ea981bde21a2662f4'
MODEL_FILES = ('config.json', 'model.safetensors', 'README.md',
               'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json')
CODE_FILES = ('configuration.py', 'modeling.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-model', type=Path, required=True)
    parser.add_argument('--local-implementation', type=Path, required=True)
    parser.add_argument('--output-model', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output_model.resolve()
    if (not output.is_relative_to(root / '.local_artifacts/models')
            or output.name != REVISION or output.exists()):
        raise ValueError('use a new pinned snapshot inside the local artifact store')
    if args.local_model.name != REVISION or args.local_implementation.name != IMPLEMENTATION_REVISION:
        raise ValueError('local input revision mismatch')
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    metadata, origins = {}, {}
    for key, name, revision in [('model', MODEL, REVISION), ('implementation', IMPLEMENTATION, IMPLEMENTATION_REVISION)]:
        url = f'https://huggingface.co/api/models/{name}/revision/{revision}?blobs=true'
        path = args.evidence_dir / f'p7-09-gte-{key}-upstream-20261007.json'
        if path.exists():
            raise FileExistsError(path)
        with urlopen(url, timeout=60) as response:
            data = response.read()
        info = json.loads(data)
        if info.get('id') != name or info.get('sha') != revision:
            raise ValueError('upstream identity mismatch')
        path.write_bytes(data)
        metadata[key] = {item['rfilename']: item for item in info['siblings']}
        origins[key] = {'model_name': name, 'revision': revision,
                        'metadata_path': path.as_posix(), 'metadata_sha256': sha256(path), 'metadata_url': url}
    files = {}
    for key, names, directory in [('model', MODEL_FILES, args.local_model), ('implementation', CODE_FILES, args.local_implementation)]:
        for name in names:
            path = directory / name
            if path.is_symlink():
                raise ValueError('symlink source rejected')
            info = metadata[key][name]
            size, digest = path.stat().st_size, sha256(path)
            if size != info['size']:
                raise ValueError('upstream file size mismatch')
            if info.get('lfs'):
                if digest != info['lfs']['sha256']:
                    raise ValueError('upstream LFS bytes mismatch')
            else:
                raw = path.read_bytes()
                if hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != info['blobId']:
                    raise ValueError('upstream Git bytes mismatch')
            files[name] = {'sha256': digest, 'bytes': size, 'upstream_blob': info['blobId'],
                           'upstream_lfs': info.get('lfs'), **({'origin': key} if key != 'model' else {})}
    output.mkdir(parents=True)
    for name, recorded in files.items():
        directory = args.local_implementation if recorded.get('origin') == 'implementation' else args.local_model
        shutil.copyfile(directory / name, output / name)
    receipt_path = args.evidence_dir / 'p7-09-verified-gte-local-20261007.json'
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    write_json(receipt_path, {'status': 'PASS_PINNED_PUBLIC_FILE_HASHES', **origins['model'],
        'additional_origins': {'implementation': origins['implementation']}, 'files': files,
        'source_inputs': {'model': args.local_model.as_posix(), 'implementation': args.local_implementation.as_posix()},
        'excluded_generated_files': ['__pycache__', '.download_manifest.json', '.implementation_origin.json'],
        'runner_sha256': sha256(Path(__file__))})
    print(json.dumps(verified_model_origin(output, receipt_path)))


if __name__ == '__main__':
    main()
