"""Performance probes must never delete a document they did not freshly create."""
import hashlib

import pytest

from scripts.operations import benchmark_pdf_readiness as module


@pytest.mark.parametrize('condition',['preexisting','duplicate_race','wrong_identity'])
def test_probe_does_not_delete_preexisting_duplicate_or_unexpected_document(tmp_path,monkeypatch,condition):
    source=tmp_path/'QA-native100-test.pdf';source.write_bytes(b'owned local fixture')
    identifier=hashlib.sha256(source.read_bytes()).hexdigest();calls=[]
    def request(path,**options):
        calls.append((path,options.get('method')))
        if path=='/api/documents':
            return {'documents':[{'doc_id':identifier}] if condition=='preexisting' else [],'jobs':[]}
        if path=='/api/documents/upload':
            return {'job':{'document_id':'0'*64 if condition=='wrong_identity' else identifier},
                    'duplicate':condition=='duplicate_race'}
        if options.get('method')=='DELETE':
            pytest.fail('A probe must never delete a pre-existing or unexpected source')
        raise AssertionError('Unexpected network path')
    monkeypatch.setattr(module,'request',request)
    with pytest.raises(ValueError):module.measure(source,1,tmp_path/'report.json')
    assert not any(method=='DELETE' for _path,method in calls)
