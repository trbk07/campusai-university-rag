"""Local state layout and read-only startup checks; no provider requests."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import tempfile


STATE_PATHS = {
    'CAMPUSAI_STORE_DIR': 'data/store',
    'CAMPUSAI_INDEX_DIR': 'data/index',
    'CAMPUSAI_JOB_DB': 'data/operations/ingestion-jobs.sqlite3',
    'CAMPUSAI_RAG_CACHE_PATH': 'data/cache/grounded-answers.sqlite3',
}


def configure_paths(root: Path, env: dict) -> None:
    """Resolve paths without creating directories or relocating old data."""
    explicit = bool(env.get('CAMPUSAI_STATE_ROOT'))
    base = Path(env.get('LOCALAPPDATA') or Path.home() / '.local/share') / 'CampusAI'
    state = Path(env.get('CAMPUSAI_STATE_ROOT') or base).expanduser()
    if not state.is_absolute():
        raise ValueError('CAMPUSAI_STATE_ROOT phải là đường dẫn tuyệt đối.')
    # A change of default must never make existing documents/quota disappear.
    legacy = any((root / name).exists() and any((root / name).iterdir())
                 for name in ('data/store', 'data/index', 'data/operations'))
    if legacy and not explicit:
        raise ValueError('Có dữ liệu local cũ. Đặt CAMPUSAI_STATE_ROOT bằng thư mục dự án cũ '
                         'để tiếp tục dùng dữ liệu, hoặc chọn thư mục tuyệt đối mới để cài riêng; không tự di chuyển dữ liệu.')
    env['CAMPUSAI_STATE_ROOT'] = str(state.resolve())
    for key, relative in STATE_PATHS.items():
        value = env.get(key) or relative
        if value == ':memory:' and key == 'CAMPUSAI_RAG_CACHE_PATH':
            continue
        path = Path(value).expanduser()
        env[key] = str((path if path.is_absolute() else state / path).resolve())
    models = Path(env.get('CAMPUSAI_MODEL_CACHE') or state / 'models').expanduser()
    if not models.is_absolute():
        models = state / models
    env['CAMPUSAI_MODEL_CACHE'] = str(models.resolve())
    env.setdefault('HF_HOME', str(models.resolve()))
    env.setdefault('HF_HUB_CACHE', env.get('HUGGINGFACE_HUB_CACHE') or str(Path(env['HF_HOME']) / 'hub'))
    env.setdefault('HF_HUB_OFFLINE', '1')
    env.setdefault('TRANSFORMERS_OFFLINE', '1')


def writable_directories(env: dict) -> list[Path]:
    paths = [Path(env['CAMPUSAI_STATE_ROOT'])]
    for key in STATE_PATHS:
        if env[key] == ':memory:':
            continue
        path = Path(env[key])
        paths.append(path.parent if key.endswith(('_DB', '_PATH')) else path)
    return list(dict.fromkeys(paths))


def existing_parent(path: Path) -> Path:
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def resolve_device(env: dict) -> tuple[str, str | None]:
    requested = env.get('CAMPUSAI_DEVICE', 'cpu')
    if requested not in {'cpu', 'cuda', 'cuda:0'}:
        raise ValueError('unsupported_device')
    if requested == 'cpu':
        return 'cpu', None
    try:
        import torch
        available = torch.cuda.is_available()
    except (ImportError, OSError, RuntimeError):
        available = False
    return (requested, None) if available else ('cpu', 'cuda_unavailable_using_cpu')


def inspect_local(env: dict, *, port: int = 8000, min_free_bytes: int = 1024**3) -> dict:
    """Check only local prerequisites. Write permissions are advisory until start."""
    checks = []
    def record(name, ok, code):
        checks.append({'check': name, 'ok': bool(ok), 'code': 'ok' if ok else code})
    for index, path in enumerate(writable_directories(env)):
        parent = existing_parent(path)
        record(f'state_path_{index}', parent.is_dir() and os.access(parent, os.W_OK), 'state_not_writable')
        try:
            record(f'disk_{index}', shutil.disk_usage(parent).free >= min_free_bytes, 'insufficient_disk_space')
        except OSError:
            record(f'disk_{index}', False, 'disk_check_failed')
    try:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', port))
    except OSError:
        record('port', False, 'port_in_use')
    else:
        record('port', True, '')
    model = env.get('CAMPUSAI_DENSE_MODEL', 'BAAI/bge-m3')
    snapshot = env.get('CAMPUSAI_DENSE_SNAPSHOT')
    if snapshot:
        available = (Path(snapshot) / 'modules.json').is_file()
    else:
        snapshots = Path(env['HF_HUB_CACHE']) / ('models--' + model.replace('/', '--')) / 'snapshots'
        available = snapshots.is_dir() and any((p / 'modules.json').is_file() for p in snapshots.iterdir())
    record('dense_model', available, 'dense_model_missing_run_setup')
    backend = env.get('CAMPUSAI_OCR_BACKEND', 'rapidocr')
    if backend in {'tesseract', 'vietocr'}:
        from campusai.ingestion.ocr_assets import validate_tesseract_assets, validate_vietocr_assets
        validate = validate_tesseract_assets if backend == 'tesseract' else validate_vietocr_assets
        try:
            validate(env.get('CAMPUSAI_OCR_DATA_DIR'))
        except ValueError:
            record('ocr_assets', False, 'ocr_assets_missing_or_checksum_mismatch')
        else:
            record('ocr_assets', True, '')
    elif backend != 'rapidocr':
        record('ocr_backend', False, 'unsupported_ocr_backend')
    try:
        device, fallback = resolve_device(env)
    except ValueError:
        device, fallback = None, None
        record('device', False, 'unsupported_device')
    return {'status': 'PREREQUISITES_PASS' if all(c['ok'] for c in checks) else 'NOT_READY',
            'checks': checks, 'provider_calls': 0, 'filesystem_writes': 0,
            'device': device, 'fallback': fallback,
            'permission_check': 'advisory; startup verifies actual file creation',
            'release_accepted': False}


def prepare_state(env: dict) -> None:
    """Create state on start only; validate actual write access before model load."""
    for path in writable_directories(env):
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path) as handle:
            handle.write(b'local-state-preflight')
            handle.flush()
            os.fsync(handle.fileno())
