"""Local launch config and lifecycle; these tests never call a provider."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.operations import local


@pytest.fixture
def configured_root(tmp_path):
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/product_llm.yaml').write_text(json.dumps({'llm':{
        'provider':'gemini','model':'fixture-model','api_key_env':'GEMINI_API_KEY'}}))
    return tmp_path


def test_local_launcher_loads_existing_owner_key_and_approved_profile(configured_root):
    root = configured_root
    (root/'configs/key.yaml').write_text('key_1: fixturecredential123\nkey_2: othercredential456\n')
    (root/'configs/gemini.yaml').write_text('llm: {model: obsolete-preview}')
    env = {}
    result = local.configure_local(root,env)
    assert env['GEMINI_API_KEY'] == 'fixturecredential123'
    assert env['CAMPUSAI_LLM_CONFIG'] == str(root/'configs/product_llm.yaml')
    assert result == {'ai_configured':True,'provider':'gemini','model':'fixture-model'}
    assert 'credential' not in json.dumps(result)


def test_continuity_profile_is_default_and_explicit_profile_still_wins(configured_root):
    root = configured_root
    (root/'configs/continuity_llm.yaml').write_text(json.dumps({'llm':{
        'provider':'gemini','model':'continuity-model','api_key_env':'GEMINI_API_KEY'}}))
    env = {'GEMINI_API_KEY':'fake'}
    assert local.configure_local(root,env)['model'] == 'continuity-model'
    assert env['CAMPUSAI_LLM_CONFIG'] == str(root/'configs/continuity_llm.yaml')
    explicit = {'GEMINI_API_KEY':'fake','CAMPUSAI_LLM_CONFIG':'configs/product_llm.yaml'}
    assert local.configure_local(root,explicit)['model'] == 'fixture-model'


def test_qualified_free_profile_is_preferred_without_overriding_explicit_choice(configured_root):
    root = configured_root
    (root/'configs/free_llm.yaml').write_text(json.dumps({'llm':{
        'provider':'gemini','model':'selected-free-model','api_key_env':'GEMINI_API_KEY'}}))
    env = {'GEMINI_API_KEY':'fake'}
    assert local.configure_local(root,env)['model'] == 'selected-free-model'
    assert env['CAMPUSAI_RAG_CACHE_PATH'] == str(Path(env['CAMPUSAI_STATE_ROOT'])/'data/cache/grounded-answers.sqlite3')
    explicit = {'GEMINI_API_KEY':'fake','CAMPUSAI_LLM_CONFIG':'configs/product_llm.yaml'}
    assert local.configure_local(root,explicit)['model'] == 'fixture-model'


def test_explicit_environment_profile_and_key_take_priority_over_dotenv(configured_root,monkeypatch):
    root = configured_root
    (root/'custom.yaml').write_text('llm: {provider: gemini, model: chosen-model}')
    (root/'.env').write_text('CAMPUSAI_LLM_CONFIG=configs/product_llm.yaml\nGEMINI_API_KEY=dotenvcredential123\n')
    env = {'CAMPUSAI_LLM_CONFIG':'custom.yaml','GEMINI_API_KEY':'existingcredential123'}
    monkeypatch.setattr(local,'read_key',lambda *_a,**_k:pytest.fail('must not rotate key'))
    result = local.configure_local(root,env)
    assert result['model'] == 'chosen-model' and env['GEMINI_API_KEY'] == 'existingcredential123'


def test_dotenv_values_are_literal_and_do_not_execute_shell_code(tmp_path):
    env = {}
    path = tmp_path/'.env'
    path.write_text('export GEMINI_API_KEY="quotedcredential123"\nCAMPUSAI_INDEX_DIR=$(create-unwanted-file) # comment\n')
    local.load_local_env(path,env)
    assert env['CAMPUSAI_INDEX_DIR'] == '$(create-unwanted-file)'
    assert env['GEMINI_API_KEY'] == 'quotedcredential123'
    path.write_text('=private-credential-must-not-appear')
    with pytest.raises(local.LocalSetupError) as error:
        local.load_local_env(path,{})
    assert 'private-credential' not in str(error.value)


def test_missing_or_unignored_credential_has_safe_actionable_error(configured_root,monkeypatch):
    root = configured_root
    with pytest.raises(local.LocalSetupError,match='GEMINI_API_KEY'):
        local.configure_local(root,{})
    (root/'configs/key.yaml').write_text('key_1: fixturecredential123')
    (root/'.git').mkdir()
    monkeypatch.setattr(local.subprocess,'run',lambda *_a,**_k:SimpleNamespace(returncode=1))
    with pytest.raises(local.LocalSetupError,match='Git ignore'):
        local.configure_local(root,{})


def test_second_launch_reuses_configured_app_without_loading_models(configured_root,monkeypatch):
    monkeypatch.chdir(configured_root)
    monkeypatch.setattr(local,'ROOT',configured_root)
    monkeypatch.setattr(local,'running_app',lambda:{'runtime':{'ai_configured':True}})
    monkeypatch.setattr(local,'build_application',lambda:pytest.fail('duplicate app load'))
    opened=[]
    monkeypatch.setattr(local.webbrowser,'open',opened.append)
    assert local.main(['--open-browser']) == 0
    assert opened == [local.URL]


def test_local_ocr_auto_selection_requires_valid_assets_and_respects_explicit_backend(configured_root,monkeypatch):
    from campusai.ingestion import ocr_assets
    monkeypatch.setattr(ocr_assets,'validate_tesseract_assets',lambda _: {'languages':'vie+eng'})
    env={'GEMINI_API_KEY':'fake'}
    local.configure_local(configured_root,env)
    assert env['CAMPUSAI_OCR_BACKEND']=='tesseract'
    assert env['CAMPUSAI_OCR_DATA_DIR']==str(Path(env['CAMPUSAI_MODEL_CACHE'])/'ocr/tessdata_fast')
    explicit={'GEMINI_API_KEY':'fake','CAMPUSAI_OCR_BACKEND':'rapidocr'}
    monkeypatch.setattr(ocr_assets,'validate_tesseract_assets',lambda _:pytest.fail('explicit backend wins'))
    local.configure_local(configured_root,explicit)
    assert explicit['CAMPUSAI_OCR_BACKEND']=='rapidocr' and 'CAMPUSAI_OCR_DATA_DIR' not in explicit


def test_old_unconfigured_app_is_not_misreported_as_ready(configured_root,monkeypatch,capsys):
    monkeypatch.chdir(configured_root)
    monkeypatch.setattr(local,'ROOT',configured_root)
    monkeypatch.setattr(local,'running_app',lambda:{'documents':[]})
    assert local.main([]) == 1
    assert 'Ctrl+C' in capsys.readouterr().out


@pytest.mark.parametrize('streaming', [False, True])
def test_port_is_reserved_before_model_load_and_resources_close(configured_root,monkeypatch,streaming):
    monkeypatch.chdir(configured_root)
    monkeypatch.setattr(local,'ROOT',configured_root)
    monkeypatch.setattr(local,'running_app',lambda:None)
    monkeypatch.setattr(local,'configure_local',lambda:{'model':'fixture-model'})
    monkeypatch.setattr(local,'inspect_local',lambda _: {'status':'PREREQUISITES_PASS'})
    monkeypatch.setattr(local,'prepare_state',lambda _: None)
    calls=[]
    class Server:
        def __enter__(self): calls.append('bound'); return self
        def __exit__(self,*_args): calls.append('server_closed')
        def set_app(self,app): calls.append('set_app')
        def serve_forever(self): calls.append('serve'); raise KeyboardInterrupt
    def build():
        assert calls == ['bound']
        calls.append('model_loaded')
        return SimpleNamespace(close=lambda:calls.append('app_closed'))
    monkeypatch.setattr(local,'make_server',lambda *_args:Server())
    monkeypatch.setattr(local,'build_application',build)
    web_options=[]
    monkeypatch.delenv('CAMPUSAI_QUERY_WORKERS', raising=False)
    if streaming:
        monkeypatch.setenv('CAMPUSAI_QUERY_STREAMING', '1')
    else:
        monkeypatch.delenv('CAMPUSAI_QUERY_STREAMING', raising=False)
    monkeypatch.setattr(local,'make_wsgi_app',lambda app, **kwargs:(web_options.append(kwargs) or object()))
    assert local.main([]) == 0
    assert calls == ['bound','model_loaded','set_app','serve','server_closed','app_closed']
    assert web_options == [{'max_concurrent_queries':4,'enable_query_streaming':streaming}]


def project_profile(root, *, slots=None):
    refs = ['GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3']
    config = {'provider':'gemini','model':'fixture-model','api_key_env':refs[0],
              'api_key_envs':refs,'independent_projects':True,
              'local_key_names':slots if slots is not None else dict(zip(refs,['key_1','key_2','key_3']))}
    (root/'configs/free_llm.yaml').write_text(json.dumps({'llm':config}))
    return config


def test_local_launcher_loads_three_explicit_independent_projects(configured_root):
    project_profile(configured_root)
    (configured_root/'configs/key.yaml').write_text('key_1: credentialfirst123\nkey_2: credentialsecond456\nkey_3: credentialthird789\n')
    env = {'GEMINI_API_KEY_2':'explicitcredential456'}
    local.configure_local(configured_root,env)
    assert [env[k] for k in ['GEMINI_API_KEY','GEMINI_API_KEY_2','GEMINI_API_KEY_3']] == [
        'credentialfirst123','explicitcredential456','credentialthird789']


@pytest.mark.parametrize('slots', [
    {'GEMINI_API_KEY':'key_1'},
    {'GEMINI_API_KEY':'key_1','GEMINI_API_KEY_2':'key_1','GEMINI_API_KEY_3':'key_3'},
    {'GEMINI_API_KEY':'key_1','GEMINI_API_KEY_2':[],'GEMINI_API_KEY_3':'key_3'},
])
def test_invalid_project_bindings_fail_safely(configured_root, slots):
    project_profile(configured_root, slots=slots)
    with pytest.raises(local.LocalSetupError,match='bindings'):
        local.configure_local(configured_root,{})


def test_partial_project_file_does_not_publish_partial_credentials(configured_root):
    project_profile(configured_root)
    (configured_root/'configs/key.yaml').write_text('key_1: credentialfirst123\nkey_2: credentialsecond456\n')
    env = {}
    with pytest.raises(local.LocalSetupError):
        local.configure_local(configured_root,env)
    assert not any(k.startswith('GEMINI_API_KEY') for k in env)
