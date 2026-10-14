"""Chat inputs remain blinded, complete and bound to exact prepared bodies."""
import json
from copy import deepcopy

import pytest

from evaluation.common.release_artifacts import write_json
from scripts.benchmarks import product_chat_quality as chat


def body(prompt):
    return {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseSchema': {
        'type': 'object', 'required': ['answer'], 'properties': {'answer': {'type': 'string'}},
        'additionalProperties': False}}}


@pytest.fixture
def exported(tmp_path, monkeypatch):
    monkeypatch.setattr(chat, 'ROOT', tmp_path)
    monkeypatch.setattr(chat, 'RAW', tmp_path / 'raw')
    monkeypatch.setattr(chat.primary, 'validate_packet', lambda _packet: None)
    monkeypatch.setattr(chat, 'source_identity', lambda _root: {'runtime': 'unchanged'})
    rubric = tmp_path / 'rubric.json'
    write_json(rubric, {'gold_answer': 'DO_NOT_EXPORT_THIS_GOLD'})
    packet = {'source_identity': {'runtime': 'unchanged'}, 'rows': [{'split': 'test'}, {'split': 'holdout'}],
        'schedule': [{'arm': 'baseline', 'qid': 'q1'}, {'arm': 'current', 'qid': 'q1'},
                     {'arm': 'baseline', 'qid': 'q2'}, {'arm': 'current', 'qid': 'q2'}],
        'cases': {'baseline': {'q1': {'provider_body': body('question one')}, 'q2': {'provider_body': None}},
                  'current': {'q1': {'provider_body': body('question one, current context')},
                              'q2': {'provider_body': body('question two')}}},
        'rubric': {'path': str(rubric), 'sha256': chat.sha256(rubric)}, 'max_provider_calls': 3}
    path, output = tmp_path / 'packet.json', tmp_path / 'export'
    write_json(path, packet)
    chat.export(path, output, max_cases=2)
    return tmp_path, packet, output


def test_export_excludes_gold_and_arm_labels_and_preserves_exact_inputs(exported):
    root, packet, output = exported
    manifest, recovered, cases = chat.load_export(output)
    assert recovered == packet and manifest['model_inputs'] == 3
    assert manifest['model_inputs_by_arm'] == {'baseline': 1, 'current': 2}
    assert [b['count'] for b in manifest['batches']] == [2, 1]
    assert len(cases) == 3
    for b in manifest['batches']:
        content = (root / b['path']).read_text(encoding='utf-8')
        assert 'DO_NOT_EXPORT_THIS_GOLD' not in content
        assert '"arm"' not in content and '"qid"' not in content and 'gold_answer' not in content
    assert cases['p7-chat-002']['prompt'] == 'question one, current context'
    assert manifest['external_api_calls'] == 0 and not manifest['quality_accepted']


def test_export_drift_is_rejected_before_import(exported):
    root, _packet, output = exported
    (output / 'batch-01.md').write_text('changed prompt', encoding='utf-8')
    with pytest.raises(ValueError, match='batch changed'):
        chat.load_export(output)


def test_invalid_raw_json_is_retained_without_escape_repair(exported):
    root, _packet, output = exported
    raw = root / 'reply.txt'
    text = '{"case_id":"p7-chat-001","response":{"answer":"bad "quote""}}\n'
    raw.write_text(text, encoding='utf-8')
    report = chat.import_batch(raw, 1, output)
    assert report['status'] == 'INCOMPLETE_OR_INVALID' and len(report['missing_case_ids']) == 2
    assert report['issues'][0]['issue'] == 'invalid_json_no_automatic_repair'
    assert (root / report['raw']['path']).read_bytes() == raw.read_bytes()
    assert not report['normalization_or_repair'] and not report['quality_accepted']


def test_schema_valid_chat_still_requires_source_review(exported):
    root, _packet, output = exported
    raw = root / 'reply.txt'
    raw.write_text('\n'.join(json.dumps({'case_id': f'p7-chat-{n:03}', 'response': {'answer': 'observed'}})
                             for n in [1, 2]), encoding='utf-8')
    report = chat.import_batch(raw, 1, output)
    assert report['status'] == 'SCHEMA_COMPLETE_PENDING_SOURCE_REVIEW'
    assert len(report['responses']) == 2 and not report['issues'] and not report['missing_case_ids']
    assert not report['quality_accepted']
    with pytest.raises(FileExistsError):
        chat.import_batch(raw, 1, output)


@pytest.mark.parametrize('kind', ['duplicate', 'extra', 'schema'])
def test_duplicates_extra_ids_and_invalid_schema_cannot_complete(exported, kind):
    _root, _packet, output = exported
    _manifest, _packet, cases = chat.load_export(output)
    rows = [{'case_id': 'p7-chat-001', 'response': {'answer': 'first'}},
            {'case_id': 'p7-chat-002', 'response': {'answer': 'second'}}]
    if kind == 'duplicate':
        rows.append(deepcopy(rows[0]))
    elif kind == 'extra':
        rows.append({'case_id': 'p7-chat-003', 'response': {'answer': 'outside batch'}})
    else:
        rows[1]['response']['answer'] = 42
    _valid, issues, _missing = chat.validate_records('\n'.join(map(json.dumps, rows)), cases,
                                                    ['p7-chat-001', 'p7-chat-002'])
    assert issues


def test_replay_does_not_launch_workers_with_missing_batch(exported, monkeypatch):
    _root, _packet, output = exported
    def forbidden(*_args, **_kwargs):
        pytest.fail('Incomplete Chat responses must not launch an application worker')
    monkeypatch.setattr(chat.subprocess, 'run', forbidden)
    with pytest.raises(FileNotFoundError):
        chat.replay(output)


def test_gemini_uppercase_nested_schema_preserves_validation_constraints():
    schema = {'type': 'OBJECT', 'required': ['citations'], 'properties': {
        'citations': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'required': ['page'],
            'properties': {'page': {'type': 'INTEGER', 'minimum': 1}}}}}}
    original = deepcopy(schema)
    cases = {'id': {'schema': schema, 'arm': 'current', 'qid': 'q', 'body_sha256': 'hash'}}
    rows, issues, missing = chat.validate_records(json.dumps({'case_id': 'id',
        'response': {'citations': [{'page': 1}]}}), cases, ['id'])
    assert len(rows) == 1 and not issues and not missing and schema == original
    for invalid in ('1', 0):
        rows, issues, missing = chat.validate_records(json.dumps({'case_id': 'id',
            'response': {'citations': [{'page': invalid}]}}), cases, ['id'])
        assert not rows and issues and missing == ['id']


def test_combined_import_partitions_exact_lines_and_preserves_prior_failure(exported):
    root, _packet, output = exported
    failed = root / 'failed.txt'
    failed.write_bytes(b'bad JSON\n')
    prior = chat.import_batch(failed, 1, output)
    prior_path = root / 'raw/batch-01-received/validation.json'
    prior_bytes = prior_path.read_bytes()
    combined = root / 'combined.txt'
    lines = [json.dumps({'case_id': f'p7-chat-{i:03}', 'response': {'answer': f'answer {i}'}}).encode() + b'\r\n'
             for i in (3, 1, 2)]
    combined.write_bytes(b''.join(lines))
    report = chat.import_combined(combined, output)
    assert report['valid_records'] == 3 and not report['issues'] and not report['quality_accepted']
    assert (root / report['raw']['path']).read_bytes() == combined.read_bytes()
    assert (root / report['partitions'][0]['path']).read_bytes() == lines[1] + lines[2]
    assert prior_path.read_bytes() == prior_bytes
    assert (root / prior['raw']['path']).read_bytes() == failed.read_bytes()
    with pytest.raises(FileExistsError):
        chat.import_combined(combined, output)


def test_invalid_combined_import_keeps_raw_and_does_not_create_batch_receipts(exported):
    root, _packet, output = exported
    combined = root / 'combined.txt'
    combined.write_bytes(b'{"case_id":"p7-chat-001","response":{"answer":"one"}}\n')
    report = chat.import_combined(combined, output)
    assert report['missing_case_ids'] == ['p7-chat-002', 'p7-chat-003']
    assert (root / report['raw']['path']).read_bytes() == combined.read_bytes()
    assert not (root / report['received_dir'] / 'batch-01-received').exists()
