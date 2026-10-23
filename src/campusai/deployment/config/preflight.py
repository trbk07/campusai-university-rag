"""Read-only cloud prerequisites. No model import, directory creation or API call."""
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path, PurePosixPath
import platform
import re
import sys

from .settings import Budget, ConfigurationError, read_json


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verified_model(settings):
    manifest_path = settings.config_root/'dense-manifest.json'
    if sha(manifest_path) != settings.dense_manifest_sha256:
        raise ConfigurationError('model_manifest_hash_mismatch')
    value = read_json(manifest_path)
    if (value.get('schema_version') != 1 or value.get('model') != settings.dense_model
            or value.get('revision') != settings.dense_revision):
        raise ConfigurationError('model_identity_mismatch')
    files = value.get('files')
    required = {'config.json','config_sentence_transformers.json','modules.json',
                'tokenizer.json','tokenizer_config.json','special_tokens_map.json',
                'sentencepiece.bpe.model','sentence_bert_config.json','1_Pooling/config.json'}
    if (not isinstance(files,dict) or not required <= set(files)
            or not {'pytorch_model.bin','model.safetensors'} & set(files)):
        raise ConfigurationError('model_manifest_incomplete')
    snapshot = settings.dense_snapshot
    if not snapshot.is_dir() or snapshot.resolve() != snapshot:
        raise ConfigurationError('model_snapshot_missing_or_redirected')
    inventory = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*')
                 if p.is_file() and '.cache' not in p.relative_to(snapshot).parts}
    if inventory != set(files):
        raise ConfigurationError('model_inventory_mismatch')
    for name,digest in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or not re.fullmatch('[0-9a-f]{64}',str(digest)):
            raise ConfigurationError('model_manifest_path_invalid')
        target = snapshot.joinpath(*path.parts)
        if not target.resolve().is_relative_to(snapshot) or sha(target) != digest:
            raise ConfigurationError('model_file_mismatch')
    # Modules are data declarations, but SentenceTransformers can import types
    # from them. Permit only the built-in BGE encoder/pooling/normalization stack.
    modules = read_json(snapshot/'modules.json')
    allowed = {'sentence_transformers.models.Transformer',
               'sentence_transformers.models.Pooling','sentence_transformers.models.Normalize'}
    if (not isinstance(modules,list) or not modules or any(not isinstance(m,dict)
            or m.get('type') not in allowed or m.get('path') not in ('','1_Pooling','2_Normalize') for m in modules)):
        raise ConfigurationError('model_modules_forbidden')
    return snapshot


def verified_runtime(settings):
    path = settings.config_root/'runtime-lock.json'
    if sha(path) != settings.runtime_lock_sha256:
        raise ConfigurationError('runtime_lock_hash_mismatch')
    lock = read_json(path)
    if lock.get('schema_version') != 1 or lock.get('python') != platform.python_version():
        raise ConfigurationError('runtime_python_mismatch')
    packages = lock.get('packages')
    required = {'torch','sentence-transformers','pymupdf','pyyaml','waitress'}
    if not isinstance(packages,dict) or not required <= set(packages):
        raise ConfigurationError('runtime_lock_incomplete')
    try:
        if any(not isinstance(pin,str) or version(name) != pin for name,pin in packages.items()):
            raise ConfigurationError('runtime_dependency_mismatch')
    except PackageNotFoundError:
        raise ConfigurationError('runtime_dependency_missing') from None
    return {name:packages[name] for name in sorted(packages)}


def verified_quota(settings):
    # Operator-provided Console evidence is a prerequisite, not an API discovery
    # endpoint or a claim that reading JSON verifies entitlement independently.
    value = read_json(settings.config_root/'gemini-free-quota.json')
    if (value.get('schema_version') != 1 or value.get('provider') != 'gemini'
            or value.get('model') != 'gemini-3.8-flash' or value.get('tier') != 'free'
            or not value.get('observed_at') or not re.fullmatch('[0-9a-f]{64}',str(value.get('evidence_sha256','')))):
        raise ConfigurationError('free_quota_receipt_required')
    observed = datetime.fromisoformat(value['observed_at'])
    if observed.tzinfo is None or not -300 <= (datetime.now(timezone.utc)-observed).total_seconds() <= 86400:
        raise ConfigurationError('quota_evidence_not_current')
    if sha(settings.config_root/'gemini-free-quota-evidence') != value['evidence_sha256']:
        raise ConfigurationError('quota_evidence_hash_mismatch')
    limits = Budget.parse(value.get('limits'),account=True)
    return settings.budget.within(limits)


def verified_provider_config(settings):
    from ...llm.factory import _read_config
    document = _read_config(settings.config_root/'llm.yaml')
    config = document.get('llm')
    budget = verified_quota(settings)
    expected = {'provider':'gemini','model':'gemini-3.8-flash',
        'api_key_env':'GEMINI_API_KEY','timeout_seconds':settings.provider_timeout,
        'max_retries':0,'cache_path':':memory:',
        'overload_circuit_path':str(settings.operations/'gemini-provider-health.sqlite3'),
        'requests_per_minute':budget.rpm,
        'quota':{'state_path':str(settings.operations/'gemini-quota.sqlite3'),
                 'scope':'gemini:owner:gemini-3.8-flash', 'input_tokens_per_minute':budget.input_tpm,
                 'requests_per_day':budget.rpd, 'total_tokens_per_day':budget.tokens_per_day,
                 'max_in_flight':1, 'max_wait_seconds':2},
        'generation_config':{'temperature':1,'maxOutputTokens':1024,
                             'thinkingConfig':{'thinkingLevel':'low'}}}
    if not isinstance(config,dict) or json.dumps(config,sort_keys=True) != json.dumps(expected,sort_keys=True):
        raise ConfigurationError('provider_configuration_mismatch')
    return config


def inspect(settings, *, environ=None):
    env = os.environ if environ is None else environ
    checks = []
    def check(name, fn):
        try:
            fn()
        except ConfigurationError as error:
            checks.append({'check':name,'ok':False,'code':error.code})
        except (OSError, ValueError, TypeError, KeyError):
            checks.append({'check':name,'ok':False,'code':'prerequisite_missing_or_invalid'})
        else:
            checks.append({'check':name,'ok':True})
    def host():
        if platform.system() != 'Linux' or platform.machine().casefold() not in {'aarch64','arm64'}:
            raise ConfigurationError('linux_arm64_required')
        if sys.version_info[:2] != (3,12):
            raise ConfigurationError('python_312_required')
    def credentials():
        if not isinstance(env.get('GEMINI_API_KEY'),str) or not env['GEMINI_API_KEY'].strip():
            raise ConfigurationError('gemini_environment_secret_required')
    def paths():
        for path in (settings.state_root,settings.model_cache,settings.config_root,settings.release_root):
            if not path.is_absolute() or not path.is_dir() or path.resolve() != path:
                raise ConfigurationError('managed_directory_missing_or_redirected')
        if not os.path.ismount(settings.state_root):
            raise ConfigurationError('persistent_state_mount_required')
        for path in (settings.store,settings.indexes,settings.operations):
            if not path.is_dir() or not path.resolve().is_relative_to(settings.state_root):
                raise ConfigurationError('persistent_state_layout_missing')
        if not os.access(settings.state_root, os.W_OK):
            raise ConfigurationError('state_not_writable')
        if hasattr(os,'statvfs') and os.statvfs(settings.state_root).f_flag & getattr(os,'ST_RDONLY',1):
            raise ConfigurationError('state_read_only')
    check('host',host)
    check('secret_presence',credentials)
    check('persistent_paths',paths)
    check('dense_snapshot',lambda:verified_model(settings))
    check('runtime_identity',lambda:verified_runtime(settings))
    check('free_quota_evidence',lambda:verified_quota(settings))
    check('provider_configuration',lambda:verified_provider_config(settings))
    # This command audits prerequisites only. Service/job/budget/ingress gates
    # are separately exercised and cannot become green from configuration alone.
    return {'status':'PREREQUISITES_PASS' if all(c['ok'] for c in checks) else 'NOT_READY',
            'deployment_accepted':False, 'checks':checks, 'provider_calls':0,
            'model_loads':0,'filesystem_writes':0}
