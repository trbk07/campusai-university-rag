"""Pinned encoder configuration and validation for the local launcher."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from campusai.deployment.config.preflight import sha, verified_model


DEFAULT_MANIFEST_SHA256 = 'db8ceaa057afc89a288f264555ce38d9a9cdbee351c3d88be3199545cef486d1'


def configure_encoder(root: Path, env: dict) -> dict:
    custom = bool(env.get('CAMPUSAI_DENSE_MANIFEST'))
    if custom != bool(env.get('CAMPUSAI_DENSE_MANIFEST_SHA256')):
        raise ValueError('encoder_manifest_path_and_checksum_required')
    path = Path(env.get('CAMPUSAI_DENSE_MANIFEST') or root/'configs/local/dense-manifest.json')
    if not path.is_absolute():
        path = root/path
    expected = env.get('CAMPUSAI_DENSE_MANIFEST_SHA256') or DEFAULT_MANIFEST_SHA256
    try:
        if sha(path) != expected:
            raise ValueError('encoder_manifest_checksum_mismatch')
        value = json.loads(path.read_text(encoding='utf-8'))
        model, revision = value['model'], value['revision']
        if env.get('CAMPUSAI_DENSE_MODEL', model) != model or env.get('CAMPUSAI_DENSE_REVISION', revision) != revision:
            raise ValueError('encoder_identity_mismatch_explicit_settings_preserved')
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        raise ValueError('encoder_manifest_missing_or_invalid') from None
    env['CAMPUSAI_DENSE_MANIFEST'] = str(path.resolve())
    env['CAMPUSAI_DENSE_MANIFEST_SHA256'] = expected
    env['CAMPUSAI_DENSE_MODEL'] = model
    env['CAMPUSAI_DENSE_REVISION'] = revision
    env.setdefault('CAMPUSAI_DENSE_SNAPSHOT', str(Path(env['CAMPUSAI_MODEL_CACHE'])/'bge-m3'/revision))
    return value


def verify_encoder(env: dict) -> Path:
    """Hash every file; never import the model, create state or download."""
    manifest = Path(env['CAMPUSAI_DENSE_MANIFEST'])
    # Reuse the strict inventory and built-in SentenceTransformer module checks.
    if manifest.name != 'dense-manifest.json':
        raise ValueError('encoder_manifest_must_be_named_dense_manifest_json')
    settings = SimpleNamespace(config_root=manifest.parent,
        dense_manifest_sha256=env['CAMPUSAI_DENSE_MANIFEST_SHA256'],
        dense_model=env['CAMPUSAI_DENSE_MODEL'], dense_revision=env['CAMPUSAI_DENSE_REVISION'],
        dense_snapshot=Path(env['CAMPUSAI_DENSE_SNAPSHOT']).absolute())
    return verified_model(settings)
