"""Opt-in reuse across corpus generations with unchanged selected indexes.

The standard NativeCapturePool remains strict about the whole manifest. This
offline adapter additionally proves every explicitly selected document's BM25
and dense bytes, while retaining exact input/config/model/HTTP-body checks.
It never rewrites producer identities or counts a capture as a fresh call.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from evaluation.common.release_artifacts import verify_index_files
from .checkpoint import NativeCapturePool, digest


POLICY = 'selected-index-scope-reuse-v1'
_MODEL_FIELDS = ('index_type', 'model_name', 'model_revision', 'embedding_dimension')
_FILES = ('bm25.json', 'dense.json')


def _file(root, document, filename):
    root = Path(root).resolve()
    path = root / document / filename
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('Selected index file is missing or outside its root')
    return path


class ScopedCapturePool(NativeCapturePool):
    """Require explicit scope equivalence before consulting a different corpus."""
    def __init__(self, client, *, index_root, **kwargs):
        super().__init__(client, **kwargs)
        self.index_root = Path(index_root).resolve()
        if digest(self.index_root/'manifest.json') != self.index_sha256 or not verify_index_files(self.index_root):
            raise ValueError('Target index manifest is missing, invalid or mismatched')
        self.target_manifest = json.loads((self.index_root/'manifest.json').read_text(encoding='utf-8'))

    def _proof(self, run, request):
        documents = request.get('doc_ids')
        if (not isinstance(documents, list) or not documents or len(set(documents)) != len(documents)
                or any(not isinstance(doc, str) or not re.fullmatch(r'[0-9a-f]{64}',doc) for doc in documents)):
            return None
        root = Path(run['index_path']).resolve()
        if digest(root/'manifest.json') != run['index_manifest_sha256'] or not verify_index_files(root):
            return None
        source = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        if any(source.get(key) is None or source[key] != self.target_manifest.get(key) for key in _MODEL_FIELDS):
            return None
        if not set(documents) <= set(source['documents']) & set(self.target_manifest['documents']):
            return None
        files = {}
        for document in sorted(documents):
            files[document] = {}
            for name in _FILES:
                before, after = digest(_file(root, document, name)), digest(_file(self.index_root, document, name))
                if before != after:
                    return None
                files[document][name] = before
        return {'policy':POLICY, 'source_index':str(root), 'target_index':str(self.index_root),
                'source_manifest_sha256':run['index_manifest_sha256'],
                'target_manifest_sha256':self.index_sha256, 'selected_files':files}

    def add(self, directory):
        directory = Path(directory).resolve()
        run = json.loads((directory/'run.json').read_text(encoding='utf-8'))
        if run.get('index_manifest_sha256') == self.index_sha256:
            return super().add(directory)
        source = NativeCapturePool(self.client, config_sha256=self.config_sha256,
            index_sha256=run.get('index_manifest_sha256'),requests=self.requests,dev_anchors=self.dev_anchors)
        source.add(directory)
        proofs = {}
        for key, value in source.records.items():
            identifier = key[0]
            if identifier not in proofs:
                try:
                    proofs[identifier] = self._proof(run, self.requests[identifier])
                except (OSError, KeyError, TypeError, ValueError):
                    proofs[identifier] = None
            proof = proofs[identifier]
            if proof is None:
                continue
            candidate = deepcopy(value)
            candidate['origin']['selected_index_scope'] = proof
            if key not in self.records or candidate['priority'] < self.records[key]['priority']:
                self.records[key] = candidate
                self.bindings.update(source.bindings)
        self.rejected.extend(source.rejected)

    def lookup(self, identifier, endpoint, body_sha256):
        value = super().lookup(identifier, endpoint, body_sha256)
        proof = value['origin'].get('selected_index_scope')
        if proof:
            for label in ('source', 'target'):
                root = Path(proof[label+'_index'])
                if digest(root/'manifest.json') != proof[label+'_manifest_sha256']:
                    raise ValueError('Selected index manifest changed after proof')
                for document, files in proof['selected_files'].items():
                    if any(digest(_file(root,document,name)) != expected for name,expected in files.items()):
                        raise ValueError('Selected index bytes changed after proof')
        return value
