"""Start the local app with existing credentials, without printing secrets."""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser
from campusai.deployment.local_server import make_local_server as make_server

from campusai.llm.factory import _read_config
from campusai.web import make_wsgi_app
from .serve import build_application
from .with_gemini_key import read_key
from .local_state import configure_paths, inspect_local, prepare_state

ROOT = Path(__file__).resolve().parents[2]
URL = 'http://127.0.0.1:8000'


class LocalSetupError(ValueError):
    """An actionable startup error whose message contains no private values."""


def load_local_env(path: Path, environ: dict) -> None:
    """Read key=value settings without executing shell expressions."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:]
        name, separator, value = line.partition('=')
        name = name.strip()
        if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*', name):
            raise LocalSetupError('File .env có dòng cấu hình không hợp lệ.')
        value = value.strip()
        if value.startswith(('"', "'")):
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                raise LocalSetupError('File .env có giá trị đặt trong dấu nháy không hợp lệ.') from None
            if not isinstance(value, str):
                raise LocalSetupError('Giá trị trong .env phải là chuỗi.')
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].rstrip()
        if value and not environ.get(name):
            environ[name] = value


def configure_local(root: Path = ROOT, environ: dict | None = None) -> dict:
    """Use explicit environment settings first, then the owner's local key.

    Startup makes no provider requests and never rotates keys/models or billing.
    """
    env = os.environ if environ is None else environ
    load_local_env(root / '.env', env)
    try:
        configure_paths(root, env)
    except ValueError as error:
        raise LocalSetupError(str(error)) from None
    default_profile = root / 'configs/free_llm.yaml'
    if not default_profile.is_file():
        default_profile = root / 'configs/continuity_llm.yaml'
    if not default_profile.is_file():
        default_profile = root / 'configs/product_llm.yaml'
    profile = Path(env.get('CAMPUSAI_LLM_CONFIG') or default_profile)
    if not profile.is_absolute():
        profile = root / profile
    try:
        config = _read_config(profile)['llm']
        provider = config.get('provider', 'gemini')
        key_name = config.get('api_key_env', {'gemini':'GEMINI_API_KEY','groq':'GROQ_API_KEY'}.get(provider, 'OPENAI_API_KEY'))
    except (ValueError, KeyError, AttributeError):
        raise LocalSetupError('Không đọc được cấu hình AI. Kiểm tra CAMPUSAI_LLM_CONFIG.') from None
    if (Path(env['CAMPUSAI_STATE_ROOT']) == root.resolve()
            and config.get('overload_circuit_path') == 'data/operations/gemini-provider-health.sqlite3'
            and (root/'.tmp/gemini-provider-health.sqlite3').exists()
            and not (root/'data/operations/gemini-provider-health.sqlite3').exists()):
        raise LocalSetupError('Có cooldown cũ trong .tmp. Dừng app và backup SQLite sang '
                             'data/operations/gemini-provider-health.sqlite3 theo hướng dẫn local; không reset cooldown.')
    bindings = {key_name: env.get('CAMPUSAI_KEY_NAME')}
    slots = config.get('local_key_names')
    if slots is not None:
        references = config.get('api_key_envs')
        if (provider != 'gemini' or config.get('independent_projects') is not True
                or not isinstance(references, list) or not 2 <= len(references) <= 3
                or any(not isinstance(name, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', name) for name in references)
                or references[0] != key_name or len(set(references)) != len(references)
                or not isinstance(slots, dict) or set(slots) != set(references)
                or any(not isinstance(value, str) or value not in {'key_1', 'key_2', 'key_3'} for value in slots.values())
                or len(set(slots.values())) != len(slots)):
            raise LocalSetupError('Invalid independent-project local credential bindings.')
        bindings = slots
    missing = {name: slot for name, slot in bindings.items() if not env.get(name)}
    if provider == 'gemini' and missing:
        credential = Path(env.get('CAMPUSAI_KEY_FILE') or root / 'configs/key.yaml')
        if not credential.is_absolute():
            credential = root / credential
        if credential.is_file():
            if (root / '.git').exists():
                ignored = subprocess.run(['git','check-ignore','--quiet','--no-index','--',str(credential)], cwd=root, capture_output=True, check=False)
                if ignored.returncode != 0:
                    raise LocalSetupError('File credential phải được Git ignore trước khi chạy ứng dụng.')
            try:
                loaded = {name: read_key(credential, slot) for name, slot in missing.items()}
                if slots is not None and len(set(loaded.values()) | {env[name] for name in bindings if env.get(name)}) != len(bindings):
                    raise ValueError('independent projects require distinct credentials')
                env.update(loaded)
            except ValueError:
                raise LocalSetupError('Credential Gemini chưa hợp lệ. Kiểm tra file key local.') from None
    if not env.get(key_name):
        raise LocalSetupError(f'Chưa có credential AI. Đặt {key_name} trong .env hoặc dùng file key local đã được Git ignore.')
    if slots is not None and (any(not env.get(name) for name in bindings)
            or len({env.get(name) for name in bindings}) != len(bindings)):
        raise LocalSetupError('Independent project credentials must be present and distinct.')
    env['CAMPUSAI_LLM_CONFIG'] = str(profile)
    if not env.get('CAMPUSAI_OCR_BACKEND'):
        from campusai.ingestion.ocr_assets import validate_tesseract_assets
        data_dir = env.get('CAMPUSAI_OCR_DATA_DIR') or Path(env['CAMPUSAI_MODEL_CACHE'])/'ocr/tessdata_fast'
        try:
            validate_tesseract_assets(data_dir)
        except ValueError:
            pass
        else:
            env['CAMPUSAI_OCR_BACKEND'] = 'tesseract'
            env['CAMPUSAI_OCR_DATA_DIR'] = str(Path(data_dir).resolve())
    return {'ai_configured':True, 'provider':provider, 'model':str(config.get('model',''))}


def running_app() -> dict | None:
    try:
        with urlopen(URL + '/health', timeout=1) as response:
            health = json.load(response)
        if health.get('service') != 'campusai':
            raise ValueError('Cổng 8000 đang được ứng dụng khác sử dụng.')
        with urlopen(URL + '/api/documents', timeout=1) as response:
            return json.load(response)
    except (URLError, TimeoutError, OSError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open-browser', action='store_true')
    parser.add_argument('--check', action='store_true', help='Read-only prerequisites; no provider call')
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    if args.check:
        # Isolate configuration changes too; the check writes no files/state.
        env = dict(os.environ)
        try:
            configure_local(ROOT, env)
            report = inspect_local(env)
        except LocalSetupError as error:
            report = {'status':'NOT_READY', 'error':str(error), 'provider_calls':0, 'filesystem_writes':0}
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report['status'] == 'PREREQUISITES_PASS' else 1
    try:
        existing = running_app()
    except ValueError:
        print('Không khởi động được CampusAI: port_in_use. Dừng ứng dụng khác trên cổng 8000.')
        return 1
    if existing is not None:
        if not existing.get('runtime', {}).get('ai_configured'):
            print('CampusAI cũ chưa cấu hình AI đang dùng cổng 8000. Dừng terminal cũ bằng Ctrl+C rồi mở lại app.')
            return 1
        print(f'CampusAI đang chạy: {URL}')
        if args.open_browser:
            webbrowser.open(URL)
        return 0
    application = None
    try:
        configured = configure_local()
        report = inspect_local(os.environ)
        if report['status'] != 'PREREQUISITES_PASS':
            raise LocalSetupError('Preflight: ' + ', '.join(c['code'] for c in report['checks'] if not c['ok']))
        if report.get('device'):
            os.environ['CAMPUSAI_DEVICE'] = report['device']
        if report.get('fallback'):
            print('GPU không khả dụng; dùng CPU. Chưa công bố SLO cho cấu hình này.', flush=True)
        # Bind first so repeated launches cannot load duplicate large models.
        with make_server('127.0.0.1',8000,lambda _env, _start: []) as server:
            prepare_state(os.environ)
            print(f'Đang khởi động CampusAI · {configured["model"]} · giữ cửa sổ này mở...', flush=True)
            application = build_application()
            server.set_app(make_wsgi_app(application,
                max_concurrent_queries=int(os.getenv('CAMPUSAI_QUERY_WORKERS', '4')),
                enable_query_streaming=os.getenv('CAMPUSAI_QUERY_STREAMING','0')=='1'))
            print(f'CampusAI đã sẵn sàng: {URL}', flush=True)
            print('Chọn tài liệu sẵn sàng trong Trợ lý AI rồi đặt câu hỏi. Ctrl+C để dừng.', flush=True)
            if args.open_browser:
                webbrowser.open(URL)
            server.serve_forever()
    except KeyboardInterrupt:
        print('\nĐã dừng CampusAI.')
    except LocalSetupError as error:
        print('Không khởi động được CampusAI. ' + str(error))
        return 1
    except (OSError, ValueError):
        print('Không khởi động được CampusAI. Kiểm tra cấu hình/credential local, cổng 8000 và model đã tải.')
        return 1
    finally:
        if application is not None:
            application.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
