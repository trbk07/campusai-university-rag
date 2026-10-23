"""Publish complete managed indexes; temporary artifacts stay inside their roots."""
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def atomic_text(path,text,encoding='utf-8'):
    target = Path(path)
    fd,name = tempfile.mkstemp(prefix='.'+target.name+'.',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'w',encoding=encoding) as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name,target)
    finally:
        Path(name).unlink(missing_ok=True)


def _inside(root,path):
    root,path = Path(root).resolve(),Path(path).absolute()
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current/part
        if current.is_symlink() or (hasattr(current,'is_junction') and current.is_junction()):
            raise ValueError('index artifact redirected')
    if not path.resolve().is_relative_to(root): raise ValueError('index artifact outside root')
    return path


def cleanup_stage(options,job_id,doc_id,*,restore=False):
    if options['index_dir'] is None: return
    if not re.fullmatch('[0-9a-f]{32}',job_id) or not re.fullmatch('[0-9a-f]{64}',doc_id):
        raise ValueError('managed job identity required')
    root = Path(options['index_dir']).resolve()
    stage = _inside(root,root/'.jobs'/job_id)
    target,previous = _inside(root,root/doc_id),_inside(root,stage/'previous')
    if restore and previous.is_dir() and not target.exists():
        previous.replace(target)
    if stage.is_dir(): shutil.rmtree(stage)


def build_indexes(manager,job_id,document,options,builder):
    from ...retrieval.bm25_index import BM25Index
    from ...retrieval.dense_index import DenseIndex, corpus_hash
    from ...retrieval.index_builder import chunk_records, _write_corpus_manifest
    root = Path(options['index_dir']).resolve()
    target = _inside(root,root/document.doc_id)
    expected = {'expected_model_name':options['dense_model'],
        'expected_model_revision':options['dense_model_revision'],
        'expected_corpus_hash':corpus_hash(chunk_records(document))}
    try:
        dense = DenseIndex.load(target/'dense.json',**expected)
        if BM25Index.load(target/'bm25.json').items != dense.items:
            raise ValueError('index pair mismatch')
    except (OSError,ValueError,RuntimeError,TypeError,KeyError):
        dense = None
    if dense is not None:
        with manager._lock:
            manager._checkpoint(job_id)
            _write_corpus_manifest(root,document.doc_id,dense.items,dense.manifest)
        return
    stage = _inside(root,root/'.jobs'/job_id)
    stage.mkdir(parents=True,exist_ok=True)
    atomic_text(stage/'intent.json',json.dumps({'job_id':job_id,'doc_id':document.doc_id}))
    try:
        builder(document,stage,dense_model=options['dense_model'],device=options['device'],
                batch_size=options['batch_size'],model_revision=options['dense_model_revision'],
                corpus_id=root.name)
        complete = _inside(root,stage/document.doc_id)
        dense = DenseIndex.load(complete/'dense.json',**expected)
        if BM25Index.load(complete/'bm25.json').items != dense.items:
            raise ValueError('staged index pair mismatch')
        with manager._lock:
            manager._checkpoint(job_id)
            previous = _inside(root,stage/'previous')
            if target.exists(): target.replace(previous)
            try:
                complete.replace(target)
                _write_corpus_manifest(root,document.doc_id,dense.items,dense.manifest)
            except Exception:
                if not target.exists() and previous.exists(): previous.replace(target)
                raise
    finally:
        # Abrupt process death leaves this tracked job workspace for recovery.
        # Normal failure/cancel can remove generated staging files immediately.
        if stage.exists(): cleanup_stage(options,job_id,document.doc_id,restore=True)
