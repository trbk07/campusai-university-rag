"""Offline input/provenance contracts, never model answer quality."""
import hashlib
import json

import pytest
from jsonschema import ValidationError

from evaluation.phase10 import run as runner


@pytest.fixture
def packet(tmp_path,monkeypatch):
    # No production corpus, credentials or runtime generation is opened.
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'RAW',tmp_path/'raw')
    monkeypatch.setattr(runner,'entries',lambda:{})
    schema=dict(type='object',required=['answer'],additionalProperties=False,
                properties=dict(answer=dict(type='string')))
    return tmp_path,{qid:dict(schema=schema) for qid in ['p10-control-a','p10-control-b']}


def write(root,rows):
    path=root/'owner.jsonl'
    path.write_bytes(('\ufeff'+''.join(json.dumps(row,ensure_ascii=False)+'\r\n' for row in rows)).encode('utf-8'))
    return path


def case(qid='p10-control-a',answer='synthetic format control'):
    return dict(qid=qid,response=dict(answer=answer))


def test_valid_input_retains_exact_bom_newlines_values_and_hash(packet):
    root,captures=packet;path=write(root,[case(),case('p10-control-b')])
    body=path.read_bytes()
    responses,preserved,digest=runner.load_chat_responses(path,captures)
    assert set(responses)==set(captures)
    assert preserved.read_bytes()==body and digest==hashlib.sha256(body).hexdigest()
    assert runner.load_chat_responses(path,captures)==(responses,preserved,digest)


@pytest.mark.parametrize('rows,message',[
    ([case('p9-robotics-01')],'does not belong'),
    ([case(),case()],'duplicate qid'),
    ([case()],'missing: p10-control-b'),
    ([dict(qid='p10-control-a',response=dict(answer='x'),extra='not silently removed')],'exactly qid and response'),
])
def test_wrong_duplicate_partial_or_extra_envelope_is_rejected_with_raw_retained(packet,rows,message):
    root,captures=packet;path=write(root,rows)
    with pytest.raises(ValueError,match=message):runner.load_chat_responses(path,captures)
    retained=list((root/'raw').glob('received-chat-*.jsonl'))
    assert len(retained)==1 and retained[0].read_bytes()==path.read_bytes()


def test_invalid_schema_is_not_repaired_or_counted_as_raw_pass(packet):
    root,captures=packet;path=write(root,[dict(qid='p10-control-a',response=dict(answer=123))])
    with pytest.raises(ValidationError):runner.load_chat_responses(path,captures)
    assert next((root/'raw').glob('received-chat-*.jsonl')).read_bytes()==path.read_bytes()


def test_invalid_json_is_retained_without_inventing_a_response(packet):
    root,captures=packet;path=root/'owner.jsonl';path.write_bytes(b'{"qid":')
    with pytest.raises(json.JSONDecodeError):runner.load_chat_responses(path,captures)
    assert next((root/'raw').glob('received-chat-*.jsonl')).read_bytes()==path.read_bytes()


def test_preserved_input_collision_never_overwrites_history(packet):
    root,captures=packet;path=write(root,[case(),case('p10-control-b')])
    _,preserved,_=runner.load_chat_responses(path,captures)
    preserved.write_bytes(b'corrupted existing raw input')
    with pytest.raises(AssertionError,match='identity collision'):runner.load_chat_responses(path,captures)
    assert preserved.read_bytes()==b'corrupted existing raw input'
