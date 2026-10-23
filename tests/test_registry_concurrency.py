"""Registry readers must not race atomic replacement on Windows."""
import json
import threading
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from campusai.documents.registry import DocumentRegistry


@pytest.mark.skipif(os.name != 'nt', reason='Windows extended-path normalization')
def test_registry_lease_survives_first_file_creation(tmp_path, monkeypatch):
    path = tmp_path/'registry.json'
    original = Path.resolve

    def resolve(value, *args, **kwargs):
        result = original(value, *args, **kwargs)
        if value == path and path.exists():
            return Path('\\\\?\\' + str(result))
        return result
    monkeypatch.setattr(Path, 'resolve', resolve)
    first = DocumentRegistry(path)
    first.add(SimpleNamespace(doc_id='first', to_dict=lambda:{'doc_id':'first'}))
    second = DocumentRegistry(path)
    assert first._lock is second._lock


@pytest.mark.parametrize('operation',['get','list','contains','construct'])
def test_reader_and_writer_instances_share_a_file_access_lease(tmp_path, monkeypatch, operation):
    path=tmp_path/'registry.json'
    reader,writer=DocumentRegistry(path),DocumentRegistry(path)
    writer.add(SimpleNamespace(doc_id='first',to_dict=lambda:{'doc_id':'first'}))
    reading,release,writing=threading.Event(),threading.Event(),threading.Event()
    failures=[]
    original_load=DocumentRegistry._load
    original_save=writer._save
    def load(registry):
        if threading.current_thread().name=='registry-reader':
            with path.open(encoding='utf-8') as handle:
                reading.set()
                assert release.wait(3)
                return json.load(handle)
        return original_load(registry)
    def save():
        writing.set(); original_save()
    monkeypatch.setattr(DocumentRegistry,'_load',load)
    monkeypatch.setattr(writer,'_save',save)
    def read():
        try:
            if operation=='construct': DocumentRegistry(path)
            elif operation=='list': reader.list()
            else: getattr(reader,operation)('first')
        except BaseException as error: failures.append(error)
    def write():
        try: writer.add(SimpleNamespace(doc_id='second',to_dict=lambda:{'doc_id':'second'}))
        except BaseException as error: failures.append(error)
    first=threading.Thread(target=read,name='registry-reader')
    second=threading.Thread(target=write,name='registry-writer')
    try:
        first.start(); assert reading.wait(3); second.start()
        assert not writing.wait(.15), 'writer replaced a registry while another instance was reading it'
    finally:
        release.set(); first.join(3)
        if second.ident is not None: second.join(3)
    assert not failures and not first.is_alive() and not second.is_alive()
    assert set(json.loads(path.read_text()))=={'first','second'}
