"""Consent and source binding fail closed before any provider is initialized."""
from pathlib import Path
import json
import pytest

from scripts.benchmarks.phase7_repaired_answer_pilot import collect
from campusai.rag.grounding import GroundedAnswerGenerator


@pytest.mark.parametrize('changed', ['digest', 'ceiling', 'retry', 'consent', 'host'])
def test_new_packet_needs_its_own_exact_consent(tmp_path, changed):
    packet = tmp_path / 'packet.json'
    packet.write_text(json.dumps({'endpoint_host': 'generativelanguage.googleapis.com'}))
    import hashlib
    auth = {'packet_sha256': hashlib.sha256(packet.read_bytes()).hexdigest(),
            'max_provider_calls': 8, 'max_retries': 0, 'explicit_user_authorization': True,
            'endpoint_host': 'generativelanguage.googleapis.com'}
    key, value = {'digest': ('packet_sha256', 'another-packet'), 'ceiling': ('max_provider_calls', 9),
                  'retry': ('max_retries', 1), 'consent': ('explicit_user_authorization', False),
                  'host': ('endpoint_host', 'other.example')}[changed]
    auth[key] = value
    receipt = tmp_path / 'receipt.json';receipt.write_text(json.dumps(auth))
    with pytest.raises(ValueError, match='explicit consent'):
        collect(packet, receipt, Path('credential-must-not-be-read.yaml'), tmp_path / 'out.json')
    assert not (tmp_path / 'out.json').exists()


def test_atomic_table_prompt_retains_source_only_and_correct_column_instructions():
    prompt = GroundedAnswerGenerator().prompt('How many credits?', [], 'en')
    assert "Course CODE has N credits." in prompt
    assert 'own credit column' in prompt
    assert 'one source row' in prompt
    assert 'Do not use outside knowledge' in prompt
