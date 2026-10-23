"""Configuration/preflight contracts only; synthetic fixtures are not cloud evidence."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from campusai.deployment.config.settings import Budget, CloudSettings, ConfigurationError
from campusai.deployment.config import preflight
from scripts.operations.preflight import main


def profile(tmp_path):
    value = json.loads(Path('configs/deployment/oci-a1-owner.example.json').read_text(encoding='utf-8'))
    for name in value['paths']:
        value['paths'][name] = str((tmp_path/name).resolve())
    value['http']['allowed_host'] = 'campusai.test-tail.ts.net'
    value['http']['origin'] = 'https://campusai.test-tail.ts.net'
    value['dense']['manifest_sha256'] = '0'*64
    value['runtime']['lock_sha256'] = '0'*64
    return value


def load(tmp_path, value, *, environ=None):
    path = tmp_path/'deployment.json'
    path.write_text(json.dumps(value),encoding='utf-8')
    return CloudSettings.load(path,environ={} if environ is None else environ)


@pytest.mark.parametrize('section,field,bad',[
    ('paths','state_root','data/store'),('paths','model_cache','/'),
    ('paths','config_root','/etc/../private'),('paths','release_root','~/app'),
    ('paths','release_root','/opt/$SECRET'),('paths','state_root','//server/share'),
    ('http','bind','0.0.0.0'),('http','threads',100),('http','threads',True),
    ('http','query_concurrency',2),('http','query_concurrency',True),
    ('http','allowed_host','campusai.test-tail.ts.net.attacker.example'),
    ('http','allowed_host','*.ts.net'),('http','origin','http://campusai.test-tail.ts.net'),
    ('http','origin','https://secret@campusai.test-tail.ts.net'),
    ('http','origin','https://campusai.test-tail.ts.net/path'),('http','origin',123),
    ('workers','ingestion',2),('workers','pending',100),
    ('provider','max_retries',1),('provider','max_retries',False),
    ('provider','model','auto'),('provider','timeout_seconds',60),
    ('dense','device','cuda'),('dense','revision','main'),('dense','manifest_sha256','unknown'),
    ('runtime','python','3.14'),('runtime','architecture','x86_64'),('runtime','cpu_threads',20),
    ('features','reranker',True),('features','knowledge_graph','false'),
    ('storage','require_mount',False),('storage','maximum_volume_fraction',1),
    ('storage','limit_bytes',11*1024**3),('budget','rpm',0),('budget','rpd',False),
])
def test_invalid_profile_fails_with_safe_code(tmp_path,section,field,bad):
    value = profile(tmp_path)
    value[section][field] = bad
    with pytest.raises(ConfigurationError) as error:
        load(tmp_path,value)
    assert str(error.value) == error.value.code
    assert 'secret@' not in str(error.value) and '$SECRET' not in str(error.value)


def test_state_cannot_overlap_release_even_after_environment_override(tmp_path):
    value = profile(tmp_path)
    with pytest.raises(ConfigurationError,match='managed_paths_overlap'):
        load(tmp_path,value,environ={'CAMPUSAI_CLOUD_STATE_ROOT':value['paths']['release_root']+'/data'})


def test_environment_paths_are_validated_and_local_launch_settings_ignored(tmp_path):
    value = profile(tmp_path)
    overridden = str((tmp_path/'external-state').resolve())
    settings = load(tmp_path,value,environ={'CAMPUSAI_CLOUD_STATE_ROOT':overridden,
        'CAMPUSAI_LLM_CONFIG':'configs/private.yaml','CAMPUSAI_KEY_FILE':'configs/key.yaml'})
    assert settings.state_root == Path(overridden)
    assert settings.store == settings.state_root/'store'
    assert settings.operations != settings.release_root/'operations'
    with pytest.raises(ConfigurationError,match='absolute_path_required'):
        load(tmp_path,value,environ={'CAMPUSAI_CLOUD_STATE_ROOT':''})


def test_unknown_or_duplicate_configuration_keys_are_rejected(tmp_path):
    value = profile(tmp_path)
    value['api_key'] = 'private-synthetic-value'
    with pytest.raises(ConfigurationError,match='configuration_fields_invalid'):
        load(tmp_path,value)
    path = tmp_path/'duplicate.json'
    path.write_text('{"schema_version":1,"schema_version":1}',encoding='utf-8')
    with pytest.raises(ConfigurationError,match='duplicate_configuration_field'):
        CloudSettings.load(path,environ={})


def test_budget_is_smaller_of_account_and_operator_caps():
    app = Budget(5,20000,100,200000)
    assert app.within(Budget(2,50000,60,500000)) == Budget(2,20000,60,200000)
    account = Budget.parse({'rpm':10,'input_tpm':50000,'rpd':200,'tokens_per_day':None},account=True)
    assert app.within(account) == app  # RPD-only accounts need no invented TPD quota.


def test_inspection_creates_nothing_and_never_loads_models_or_calls_provider(tmp_path,monkeypatch):
    settings = load(tmp_path,profile(tmp_path))
    before = set(tmp_path.rglob('*'))
    monkeypatch.setattr('urllib.request.urlopen',lambda *_a,**_k:pytest.fail('Preflight must not call any API'))
    report = preflight.inspect(settings,environ={})
    assert report['status'] == 'NOT_READY' and not report['deployment_accepted']
    assert report['provider_calls'] == report['model_loads'] == report['filesystem_writes'] == 0
    assert set(tmp_path.rglob('*')) == before
    codes = {row.get('code') for row in report['checks']}
    assert 'gemini_environment_secret_required' in codes


def prerequisites(tmp_path,monkeypatch):
    """Small fake files and mocked ARM identity; never an actual VM acceptance."""
    settings = load(tmp_path,profile(tmp_path))
    for path in (settings.store,settings.indexes,settings.operations,settings.model_cache,
                 settings.config_root,settings.release_root,settings.dense_snapshot):
        path.mkdir(parents=True,exist_ok=True)
    model_files = ['config.json','config_sentence_transformers.json','modules.json',
        'tokenizer.json','tokenizer_config.json','special_tokens_map.json','sentencepiece.bpe.model',
        'sentence_bert_config.json','1_Pooling/config.json','pytorch_model.bin']
    for name in model_files:
        path = settings.dense_snapshot/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'synthetic fixture; not a loadable model')
    (settings.dense_snapshot/'modules.json').write_text(json.dumps([
        {'idx':0,'path':'','type':'sentence_transformers.models.Transformer'},
        {'idx':1,'path':'1_Pooling','type':'sentence_transformers.models.Pooling'},
        {'idx':2,'path':'2_Normalize','type':'sentence_transformers.models.Normalize'}]),encoding='utf-8')
    model_manifest = settings.config_root/'dense-manifest.json'
    model_manifest.write_text(json.dumps({'schema_version':1,'model':settings.dense_model,
        'revision':settings.dense_revision,'files':{name:preflight.sha(settings.dense_snapshot/name) for name in model_files}}),encoding='utf-8')
    packages = {name:'1.0' for name in ('torch','sentence-transformers','pymupdf','pyyaml','waitress')}
    runtime_lock = settings.config_root/'runtime-lock.json'
    runtime_lock.write_text(json.dumps({'schema_version':1,'python':'3.12.10','packages':packages}),encoding='utf-8')
    settings = replace(settings,dense_manifest_sha256=preflight.sha(model_manifest),
                       runtime_lock_sha256=preflight.sha(runtime_lock))
    evidence = settings.config_root/'gemini-free-quota-evidence'
    evidence.write_bytes(b'redacted synthetic console fixture')
    quota = settings.config_root/'gemini-free-quota.json'
    quota.write_text(json.dumps({'schema_version':1,'provider':'gemini','model':'gemini-3.8-flash',
        'tier':'free','observed_at':datetime.now(timezone.utc).isoformat(),
        'evidence_sha256':preflight.sha(evidence),
        'limits':{'rpm':5,'input_tpm':20000,'rpd':100,'tokens_per_day':None}}),encoding='utf-8')
    provider = {'llm':{'provider':'gemini','model':'gemini-3.8-flash','api_key_env':'GEMINI_API_KEY',
        'timeout_seconds':15,'max_retries':0,'cache_path':':memory:',
        'overload_circuit_path':str(settings.operations/'gemini-provider-health.sqlite3'),
        'requests_per_minute':5,
        'quota':{'state_path':str(settings.operations/'gemini-quota.sqlite3'),
                 'scope':'gemini:owner:gemini-3.8-flash','input_tokens_per_minute':20000,
                 'requests_per_day':100,'total_tokens_per_day':200000,
                 'max_in_flight':1,'max_wait_seconds':2},
        'generation_config':{'temperature':1,'maxOutputTokens':1024,
            'thinkingConfig':{'thinkingLevel':'low'}}}}
    (settings.config_root/'llm.yaml').write_text(json.dumps(provider),encoding='utf-8')
    monkeypatch.setattr(preflight.platform,'system',lambda:'Linux')
    monkeypatch.setattr(preflight.platform,'machine',lambda:'aarch64')
    monkeypatch.setattr(preflight.platform,'python_version',lambda:'3.12.10')
    monkeypatch.setattr(preflight.sys,'version_info',(3,12,10))
    monkeypatch.setattr(preflight,'version',lambda name:packages[name])
    monkeypatch.setattr(preflight.os.path,'ismount',lambda path:Path(path)==settings.state_root)
    return settings


def test_valid_prerequisites_still_do_not_claim_cloud_acceptance(tmp_path,monkeypatch):
    settings = prerequisites(tmp_path,monkeypatch)
    report = preflight.inspect(settings,environ={'GEMINI_API_KEY':'synthetic-secret'})
    assert report['status'] == 'PREREQUISITES_PASS'
    assert all(row['ok'] for row in report['checks'])
    assert report['deployment_accepted'] is False and 'synthetic-secret' not in json.dumps(report)


@pytest.mark.parametrize('change', ['weights','extra_file','modules','manifest_identity'])
def test_corrupt_or_changed_model_is_rejected(tmp_path,monkeypatch,change):
    settings = prerequisites(tmp_path,monkeypatch)
    if change == 'weights':
        (settings.dense_snapshot/'pytorch_model.bin').write_bytes(b'changed')
    elif change == 'extra_file':
        (settings.dense_snapshot/'unbound-config.json').write_text('{}',encoding='utf-8')
    else:
        path = settings.config_root/'dense-manifest.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        if change == 'modules':
            modules = settings.dense_snapshot/'modules.json'
            modules.write_text('[{"path":"","type":"arbitrary.CustomModel"}]',encoding='utf-8')
            value['files']['modules.json'] = preflight.sha(modules)
        else:
            value['revision'] = 'a'*40
        path.write_text(json.dumps(value),encoding='utf-8')
        settings = replace(settings,dense_manifest_sha256=preflight.sha(path))
    with pytest.raises(ConfigurationError):
        preflight.verified_model(settings)


@pytest.mark.parametrize('change', ['paid','stale','evidence','too_fast'])
def test_unverified_or_exceeded_provider_policy_is_rejected(tmp_path,monkeypatch,change):
    settings = prerequisites(tmp_path,monkeypatch)
    path = settings.config_root/'gemini-free-quota.json'
    value = json.loads(path.read_text(encoding='utf-8'))
    if change == 'paid': value['tier'] = 'tier-1'
    if change == 'stale': value['observed_at'] = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    if change == 'evidence': value['evidence_sha256'] = '0'*64
    if change == 'too_fast': value['limits']['rpm'] = 2
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ConfigurationError):
        preflight.verified_provider_config(settings)


def test_preflight_cli_omits_private_values_and_cannot_approve_deployment(tmp_path,capsys):
    path = tmp_path/'secret-config.json'
    path.write_text('{"api_key":"private-synthetic-value"}',encoding='utf-8')
    assert main(['--config',str(path)]) == 2
    text = capsys.readouterr().out
    assert 'private-synthetic-value' not in text
    assert json.loads(text)['deployment_accepted'] is False
    load(tmp_path,profile(tmp_path))
    assert main(['--config',str(tmp_path/'deployment.json'),'--config-only']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'CONFIG_VALID_ONLY' and not report['deployment_accepted']
