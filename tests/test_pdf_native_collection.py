"""PDF transport and capture integrity with local providers only, no live evidence."""
import hashlib
import json

import pytest

from campusai.llm.client import LLMProviderError
from evaluation.grounding.collect_native_predictions import collect, prepare_egress
from evaluation.grounding.native_artifacts import load_native_run
from tests.test_document_scope import QUESTION, absent, scope_service
from tests.test_pdf_scope_client import client


def fixture(tmp_path):
    service, _, doc_id, _ = scope_service(tmp_path, [], image=True,
        reader_options={'allow_pdf_scope': True}, pdf_client=True)
    llm = client(tmp_path)
    service.answer_generator.llm = llm
    row = {'id': 'offline-pdf', 'question': QUESTION, 'language': 'en',
           'selected_doc_ids': [doc_id], 'gold_claims': ['GOLD_NEVER_IN_REQUEST']}
    packet = prepare_egress(service, [row], llm, tmp_path/'egress', 3)
    path = tmp_path/'egress'/'egress.json'
    requests = {row['id']: [item for case in packet['cases'] for item in case['http_requests']]}
    metadata = {'model': llm.model, 'egress_packet_path': str(path),
                'egress_packet_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return service, llm, row, packet, requests, metadata


def run_fixture(tmp_path, *, failure=False, exact=True):
    service, llm, row, packet, requests, metadata = fixture(tmp_path)
    calls = []
    def transport(request, *args, **kwargs):
        calls.append(request.full_url)
        if request.full_url.endswith(':countTokens'):
            return {'totalTokens': 100}
        if failure and len(calls) == 3:
            raise LLMProviderError('Offline generation failure after measurement')
        return {'candidates': [{'content': {'parts': [{'text': json.dumps(absent())}]}}]}
    directory = tmp_path/'native'
    try:
        collect(service, [row], llm, output=directory, max_provider_calls=3,
            transport=transport, egress_requests=requests if exact else None,
            egress_prompts={row['id']: [c['prompt_sha256'] for c in packet['cases']]},
            run_metadata=metadata)
    finally:
        service.close()
    return directory, packet, calls


def test_pdf_native_request_binds_exact_binary_measurement_and_http_bodies(tmp_path):
    directory, packet, calls = run_fixture(tmp_path)
    run, predictions, raw, posts = load_native_run(directory)
    assert len(calls) == len(posts) == 3 and len(raw) == 2
    assert run['real_model_outputs_successful'] == 2 and run['official_predictions'] == 0
    assert predictions[0]['document_scope_audit']['status'] == 'checked'
    assert len(packet['pdf_sources']) == 1
    assert 'GOLD_NEVER_IN_REQUEST' not in json.dumps(packet)
    assert 'data' not in packet['cases'][1]['generation_arguments']['pdf_documents'][0]
    assert raw[1]['input_measurements'][0]['response'] == {'totalTokens': 100}
    started = json.loads((directory/'run-started.json').read_text())
    assert started['egress_requests'] == run['egress_requests']


def test_prompt_permission_does_not_authorize_pdf_http_requests(tmp_path):
    directory, _, calls = run_fixture(tmp_path, exact=False)
    assert len(calls) == 1
    run = json.loads((directory/'run.json').read_text())
    assert run['stop_reason'] == 'provider_failure'
    assert run['real_model_outputs_successful'] == 1


def test_measurement_remains_durable_when_pdf_generation_fails(tmp_path):
    directory, _, calls = run_fixture(tmp_path, failure=True)
    run, _, raw, _ = load_native_run(directory)
    assert len(calls) == 3 and run['stop_reason'] == 'provider_failure'
    assert raw[1]['success'] is False and raw[1]['input_measurements']
    events = [json.loads(line) for line in (directory/'model-started.jsonl').read_text().splitlines()]
    assert any(e.get('event') == 'token_measurement_returned' for e in events)


@pytest.mark.parametrize('mutation', ['measurement', 'body', 'binary', 'model', 'packet', 'post'])
def test_rehashed_pdf_capture_tampering_fails_closed(tmp_path, mutation):
    directory, _, _ = run_fixture(tmp_path)
    run = json.loads((directory/'run.json').read_text())
    name = 'raw-model.jsonl'
    values = [json.loads(line) for line in (directory/name).read_text().splitlines()]
    capture = values[1]
    if mutation == 'measurement': capture['input_measurements'] = []
    elif mutation == 'body': capture['pdf_request']['body_reference'] = {}
    elif mutation == 'binary': capture['generation_arguments']['pdf_documents'][0]['data'] = 'broken'
    elif mutation == 'model': capture['pdf_request']['model'] = 'other-model'
    elif mutation == 'packet':
        with open(run['egress_packet_path'], 'a') as stream: stream.write(' ')
    else:
        name = 'provider-posts.jsonl'
        values = [json.loads(line) for line in (directory/name).read_text().splitlines()]
        values[1]['request_body_sha256'] = '0'*64
    (directory/name).write_text(''.join(json.dumps(item)+'\n' for item in values))
    run['artifacts'][name] = hashlib.sha256((directory/name).read_bytes()).hexdigest()
    (directory/'run.json').write_text(json.dumps(run))
    with pytest.raises(ValueError): load_native_run(directory)
