from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from evaluation.phase8.replay_chat_baseline import ChatReplay, correct_annotations
from evaluation.phase8 import replay_chat_baseline as replay
from evaluation.phase8 import replay_chat_baseline as replay


def source_fixture():
    cells = ['1', 'Algebra', '4', 'UET']
    digest = hashlib.sha256(json.dumps({'cells': cells}, ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    row = {'qid': 'example-semester-1', 'answerable': True,
        'expected_claims': [{'course_name': 'Algebra', 'credits': 4, 'semester': 1}],
        'source_validation': {'facts': [{'doc_id': 'd', 'chunk_id': 'c',
            'table_row': 1, 'cells_sha256': digest}]},
        'gold_claims': [{'text': 'Algebra carries 4 credits.', 'evidence': [{'chunk_id': 'c'}]}]}
    content = json.dumps({'headers': ['No.', 'Course', 'Credits', 'Source'],
                         'rows': [['Semester 1', '', '', ''], cells]})
    index = {('d', 'c'): SimpleNamespace(content=content, page=1)}
    return row, index


def test_correction_uses_source_heading_and_preserves_frozen_input():
    row, index = source_fixture()
    frozen = deepcopy(row)
    corrected, changes = correct_annotations([row], index)
    assert row == frozen
    assert corrected[0]['gold_claims'][0]['text'] == 'Algebra is listed in semester 1.'
    assert corrected[0]['gold_claims'][0]['evidence'] == row['gold_claims'][0]['evidence']
    assert changes[0]['proof']['semester_from_preceding_heading'] == 1
    assert correct_annotations(corrected, index)[1] == []


@pytest.mark.parametrize('mutation', ['heading', 'credits', 'row'])
def test_correction_rejects_inconsistent_structured_gold_or_source(mutation):
    row, index = source_fixture()
    if mutation == 'heading':
        index[('d', 'c')].content = index[('d', 'c')].content.replace('Semester 1', 'Semester 2')
    elif mutation == 'credits':
        row['expected_claims'][0]['credits'] = 5
    else:
        index[('d', 'c')].content = index[('d', 'c')].content.replace('Algebra', 'Networks')
    with pytest.raises(ValueError):
        correct_annotations([row], index)


def test_replay_rejects_prompt_schema_drift_and_repeated_calls():
    client = ChatReplay({'q': {'response': {'answer': 'recorded'}}})
    client.current = {'qid': 'q', 'prompt': 'original evidence', 'schema': {'type': 'object'}}
    with pytest.raises(ValueError, match='prompt/schema'):
        client.generate_json('modified evidence', schema={'type': 'object'})
    assert client.calls == 0
    with pytest.raises(ValueError, match='prompt/schema'):
        client.generate_json('original evidence', schema={})
    result = client.generate_json('original evidence', schema={'type': 'object'})
    result['answer'] = 'mutated'
    assert client.outputs['q']['response']['answer'] == 'recorded'
    with pytest.raises(ValueError, match='multiple model calls'):
        client.generate_json('original evidence', schema={'type': 'object'})


@pytest.fixture
def reviewed_packet(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, 'ROOT', tmp_path)
    benchmark = tmp_path / 'benchmark.jsonl'
    monkeypatch.setattr(replay, 'BENCHMARK', benchmark)
    benchmark.write_text('{"qid":"a"}\n{"qid":"n"}\n', encoding='utf-8')
    packet = tmp_path / 'packet.json'
    chat = tmp_path / 'chat.jsonl'
    summary = tmp_path / 'summary.json'
    replay.write_json(packet, {'benchmark': {'sha256': replay.sha(benchmark)},
        'cases': [{'qid': 'a', 'planned_provider_call': True},
                  {'qid': 'n', 'planned_provider_call': False}]})
    chat.write_text('{"qid":"a","response":{"answer":"recorded"}}\n', encoding='utf-8')
    replay.write_json(summary, {'cases': [{'qid': 'a', 'decision': 'ACCEPT_CONTENT'}],
        'bindings': {p.name: replay.sha(p) for p in (benchmark, packet, chat)}})
    return packet, chat, summary


def test_reviewed_inputs_accept_exact_bound_generation_cohort(reviewed_packet):
    packet, rows, outputs, summary = replay.load_reviewed_inputs(*reviewed_packet)
    assert [row['qid'] for row in rows] == ['a', 'n']
    assert set(outputs) == {'a'}
    assert summary['cases'][0]['decision'] == 'ACCEPT_CONTENT'


@pytest.mark.parametrize('mutation, message', [
    ('unbound', 'not bound'), ('tampered', 'not bound'),
    ('duplicate', 'cohort mismatch'), ('missing_review', 'cohort mismatch'),
    ('rejected', 'unaccepted'), ('routing', 'cohort mismatch'),
    ('order', 'population/order'), ('external_binding', 'binding changed'),
])
def test_reviewed_inputs_reject_drift_and_unreviewed_cohorts(reviewed_packet, mutation, message):
    packet_path, chat_path, summary_path = reviewed_packet
    packet = json.loads(packet_path.read_text(encoding='utf-8'))
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    if mutation == 'unbound':
        del summary['bindings'][chat_path.name]
    elif mutation == 'tampered':
        chat_path.write_text('{"qid":"a","response":{"answer":"different"}}\n', encoding='utf-8')
    elif mutation == 'duplicate':
        chat_path.write_text(chat_path.read_text(encoding='utf-8') * 2, encoding='utf-8')
        summary['bindings'][chat_path.name] = replay.sha(chat_path)
    elif mutation == 'missing_review':
        summary['cases'] = []
    elif mutation == 'rejected':
        summary['cases'][0]['decision'] = 'REJECT_CONTENT'
    elif mutation == 'routing':
        packet['cases'][1]['planned_provider_call'] = True
    elif mutation == 'order':
        packet['cases'].reverse()
    elif mutation == 'external_binding':
        summary['bindings']['../outside-project'] = '0' * 64
    replay.write_json(packet_path, packet)
    summary['bindings'][packet_path.name] = replay.sha(packet_path)
    replay.write_json(summary_path, summary)
    with pytest.raises(ValueError, match=message):
        replay.load_reviewed_inputs(*reviewed_packet)


@pytest.fixture
def reviewed_packet(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, 'ROOT', tmp_path)
    benchmark = tmp_path / 'benchmark.jsonl'
    monkeypatch.setattr(replay, 'BENCHMARK', benchmark)
    benchmark.write_text('{"qid":"a"}\n{"qid":"n"}\n', encoding='utf-8')
    packet = tmp_path / 'packet.json'
    chat = tmp_path / 'chat.jsonl'
    summary = tmp_path / 'summary.json'
    replay.write_json(packet, {'benchmark': {'sha256': replay.sha(benchmark)},
        'cases': [{'qid': 'a', 'planned_provider_call': True},
                  {'qid': 'n', 'planned_provider_call': False}]})
    chat.write_text('{"qid":"a","response":{"answer":"recorded"}}\n', encoding='utf-8')
    replay.write_json(summary, {'cases': [{'qid': 'a', 'decision': 'ACCEPT_CONTENT'}],
        'bindings': {p.name: replay.sha(p) for p in (benchmark, packet, chat)}})
    return packet, chat, summary


def test_reviewed_inputs_accept_exact_bound_generation_cohort(reviewed_packet):
    packet, rows, outputs, summary = replay.load_reviewed_inputs(*reviewed_packet)
    assert [row['qid'] for row in rows] == ['a', 'n']
    assert set(outputs) == {'a'}
    assert summary['cases'][0]['decision'] == 'ACCEPT_CONTENT'


@pytest.mark.parametrize('mutation, message', [
    ('unbound', 'not bound'), ('tampered', 'not bound'),
    ('duplicate', 'cohort mismatch'), ('missing_review', 'cohort mismatch'),
    ('rejected', 'unaccepted'), ('routing', 'cohort mismatch'),
    ('order', 'population/order'), ('external_binding', 'binding changed'),
])
def test_reviewed_inputs_reject_drift_and_unreviewed_cohorts(reviewed_packet, mutation, message):
    packet_path, chat_path, summary_path = reviewed_packet
    packet = json.loads(packet_path.read_text(encoding='utf-8'))
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    if mutation == 'unbound':
        del summary['bindings'][chat_path.name]
    elif mutation == 'tampered':
        chat_path.write_text('{"qid":"a","response":{"answer":"different"}}\n', encoding='utf-8')
    elif mutation == 'duplicate':
        chat_path.write_text(chat_path.read_text(encoding='utf-8') * 2, encoding='utf-8')
        summary['bindings'][chat_path.name] = replay.sha(chat_path)
    elif mutation == 'missing_review':
        summary['cases'] = []
    elif mutation == 'rejected':
        summary['cases'][0]['decision'] = 'REJECT_CONTENT'
    elif mutation == 'routing':
        packet['cases'][1]['planned_provider_call'] = True
    elif mutation == 'order':
        packet['cases'].reverse()
    elif mutation == 'external_binding':
        summary['bindings']['../outside-project'] = '0' * 64
    replay.write_json(packet_path, packet)
    summary['bindings'][packet_path.name] = replay.sha(packet_path)
    replay.write_json(summary_path, summary)
    with pytest.raises(ValueError, match=message):
        replay.load_reviewed_inputs(*reviewed_packet)
