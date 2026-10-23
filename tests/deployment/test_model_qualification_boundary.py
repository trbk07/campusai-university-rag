"""Live qualification cannot silently expand to unreviewed or paid models."""
import json
import pytest
from scripts.operations.diagnostics.model_qualification import free_boundary


def test_only_screened_models_can_run(tmp_path):
    assert 'free-only' in free_boundary('gemma-4-31b-it', tmp_path)['basis']
    with pytest.raises(ValueError, match='screened'):
        free_boundary('gemini-3.8-flash', tmp_path)
    with pytest.raises(FileNotFoundError):
        free_boundary('gemini-3.5-flash-lite', tmp_path)


def test_gemini_requires_free_owner_attestation(tmp_path):
    path = tmp_path / 'owner-tier-attestation.json'
    proof = {'source': 'owner_chat_reply', 'existing_campusai_project': True, 'tier': 'paid'}
    path.write_text(json.dumps(proof), encoding='utf-8')
    with pytest.raises(ValueError, match='Free tier'):
        free_boundary('gemini-3.5-flash-lite', tmp_path)
    proof['tier'] = 'free'
    path.write_text(json.dumps(proof), encoding='utf-8')
    boundary = free_boundary('gemini-3.5-flash-lite', tmp_path)
    assert len(boundary['evidence_sha256']) == 64
    assert 'no independent' in boundary['basis']
