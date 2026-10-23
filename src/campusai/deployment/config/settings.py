"""Cloud settings contain no credentials and never load the local launcher env."""
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _object(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ConfigurationError('configuration_fields_invalid')
    return value


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ConfigurationError('duplicate_configuration_field')
            result[key] = value
        return result
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique)
    except (OSError, ValueError) as error:
        if isinstance(error, ConfigurationError):
            raise
        raise ConfigurationError('configuration_unreadable') from None


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ConfigurationError('configuration_integer_out_of_range')
    return value


def _path(value):
    if (not isinstance(value, str) or not value or '\x00' in value
            or '$' in value or '~' in value or value.startswith(('//','\\\\'))):
        raise ConfigurationError('absolute_path_required')
    # Permit inspection of a Linux profile on Windows; native IO validation
    # belongs to preflight and never treats this as a compatible cloud host.
    pure = PureWindowsPath(value) if PureWindowsPath(value).is_absolute() else PurePosixPath(value)
    if not pure.is_absolute() or '..' in pure.parts or len(pure.parts) < 3:
        raise ConfigurationError('absolute_path_required')
    return Path(value)


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ConfigurationError('sha256_required')
    return value


@dataclass(frozen=True)
class Budget:
    rpm: int
    input_tpm: int
    rpd: int
    tokens_per_day: int | None

    @classmethod
    def parse(cls, value, *, account=False):
        _object(value, ('rpm','input_tpm','rpd','tokens_per_day'))
        return cls(*(_integer(value[key], 1, 1_000_000_000)
                     for key in ('rpm','input_tpm','rpd')),
                   None if account and value['tokens_per_day'] is None else
                   _integer(value['tokens_per_day'],1,1_000_000_000))

    def within(self, account):
        return Budget(*(min(getattr(self, name), getattr(account, name))
                        if getattr(account,name) is not None else getattr(self,name)
                        for name in ('rpm','input_tpm','rpd','tokens_per_day')))


@dataclass(frozen=True)
class CloudSettings:
    state_root: Path
    model_cache: Path
    config_root: Path
    release_root: Path
    allowed_host: str
    origin: str
    port: int
    http_threads: int
    query_concurrency: int
    ingestion_workers: int
    ingestion_pending: int
    provider_timeout: int
    dense_model: str
    dense_revision: str
    dense_manifest_sha256: str
    runtime_lock_sha256: str
    budget: Budget
    storage_limit_bytes: int
    cpu_threads: int

    @property
    def store(self):
        return self.state_root/'store'

    @property
    def indexes(self):
        return self.state_root/'index'

    @property
    def operations(self):
        return self.state_root/'operations'

    @property
    def dense_snapshot(self):
        return self.model_cache/'bge-m3'/self.dense_revision

    @classmethod
    def load(cls, path, *, environ=None):
        env = os.environ if environ is None else environ
        value = read_json(path)
        _object(value, ('schema_version','profile','paths','http','workers','provider',
                        'dense','runtime','budget','storage','features'))
        if type(value['schema_version']) is not int or value['schema_version'] != 1 or value['profile'] != 'oci-a1-owner':
            raise ConfigurationError('unsupported_deployment_profile')
        paths = _object(value['paths'], ('state_root','model_cache','config_root','release_root'))
        resolved = {name: _path(env.get('CAMPUSAI_CLOUD_'+name.upper(), paths[name])) for name in paths}
        # No state/config/cache subtree may be inside an immutable release, or
        # inside another managed root. Avoid native path resolution at this step.
        roots = [str(p).replace('\\','/').rstrip('/').casefold() for p in resolved.values()]
        if any(a == b or a.startswith(b+'/') or b.startswith(a+'/')
               for index,a in enumerate(roots) for b in roots[index+1:]):
            raise ConfigurationError('managed_paths_overlap')
        http = _object(value['http'], ('bind','port','threads','allowed_host','origin','query_concurrency'))
        host = http['allowed_host']
        if (http['bind'] != '127.0.0.1' or not isinstance(host, str)
                or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.[a-z0-9-]+\.ts\.net', host)):
            raise ConfigurationError('private_ingress_invalid')
        origin = http['origin']
        if not isinstance(origin,str):
            raise ConfigurationError('private_origin_invalid')
        try:
            url = urlsplit(origin)
            valid = url.scheme == 'https' and url.hostname == host and url.port in (None,443)
        except (ValueError, TypeError):
            valid = False
        if not valid or url.username or url.password or url.path or url.query or url.fragment:
            raise ConfigurationError('private_origin_invalid')
        workers = _object(value['workers'], ('ingestion','pending'))
        if http['query_concurrency'] != 1 or workers['ingestion'] != 1 or workers['pending'] != 2:
            raise ConfigurationError('worker_budget_invalid')
        # Reject booleans that compare equal to integer 1.
        for number in (http['query_concurrency'], workers['ingestion'], workers['pending']):
            _integer(number,1,2)
        provider = _object(value['provider'], ('name','model','timeout_seconds','max_retries'))
        if provider['name'] != 'gemini' or provider['model'] != 'gemini-3.8-flash':
            raise ConfigurationError('provider_profile_changed')
        if type(provider['max_retries']) is not int or provider['max_retries'] != 0:
            raise ConfigurationError('provider_retries_forbidden')
        dense = _object(value['dense'], ('model','revision','manifest_sha256','device'))
        if (dense['model'] != 'BAAI/bge-m3' or dense['device'] != 'cpu'
                or not isinstance(dense['revision'], str) or not re.fullmatch('[0-9a-f]{40}',dense['revision'])):
            raise ConfigurationError('pinned_cpu_model_required')
        runtime = _object(value['runtime'], ('python','architecture','lock_sha256','cpu_threads'))
        if runtime['python'] != '3.12' or runtime['architecture'] != 'aarch64':
            raise ConfigurationError('runtime_target_invalid')
        storage = _object(value['storage'], ('limit_bytes','maximum_volume_fraction','require_mount'))
        if (storage['maximum_volume_fraction'] != 0.8 or storage['require_mount'] is not True):
            raise ConfigurationError('persistent_volume_policy_required')
        features = _object(value['features'], ('reranker','knowledge_graph'))
        if any(flag is not False for flag in features.values()):
            raise ConfigurationError('experimental_feature_forbidden')
        return cls(**resolved, allowed_host=host, origin=origin,
            port=_integer(http['port'],1024,65535),http_threads=_integer(http['threads'],4,8),
            query_concurrency=1,ingestion_workers=1,ingestion_pending=2,
            provider_timeout=_integer(provider['timeout_seconds'],1,25),
            dense_model=dense['model'],dense_revision=dense['revision'],
            dense_manifest_sha256=_digest(dense['manifest_sha256']),
            runtime_lock_sha256=_digest(runtime['lock_sha256']),budget=Budget.parse(value['budget']),
            storage_limit_bytes=_integer(storage['limit_bytes'],1,10*1024**3),
            cpu_threads=_integer(runtime['cpu_threads'],1,2))
