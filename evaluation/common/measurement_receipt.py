"""Retain actual commands, times and physical bindings for release collectors."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import uuid

from .release_artifacts import sha256, source_identity


def _artifacts(directory: Path) -> dict[str, str]:
    return {path.relative_to(directory).as_posix(): sha256(path)
            for path in sorted(directory.rglob('*'))
            if path.is_file() and path.suffix in {'.json', '.jsonl', '.xml'}
            and 'measurement_receipts' not in path.relative_to(directory).parts}


def _inputs(command: list[str]) -> list[dict]:
    inputs = []
    for index, value in enumerate(command[1:], 1):
        if command[index-1] in {'--output', '--fault-output', '--readiness-output', '--release-manifest'}:
            continue
        path = Path(value)
        if (path.suffix.lower() in {'.json', '.jsonl', '.yaml', '.yml', '.xml', '.toml'}
                and path.name != 'gemini.yaml' and path.is_file()):
            entry = {'path': path.as_posix(), 'sha256': sha256(path)}
            if entry not in inputs:
                inputs.append(entry)
    return inputs


def run_recorded(command: list[str], *, env: dict[str, str], results_dir: Path,
                 cycle_id: str, stage: str, root: Path | None = None):
    """Execute one process and preserve its receipt even if it fails.

    Receipts bind changed report/raw files rather than altering existing
    canonical artifacts. Child environments and credentials are never logged.
    A source change during execution invalidates the measurement.
    """
    if any('API_KEY' in arg.upper() or arg.lower().startswith(('--api-key', '--key=')) for arg in command):
        raise ValueError('credentials must be passed in process environment, not recorded command arguments')
    root = root or Path(__file__).resolve().parents[2]
    before = source_identity(root)
    inputs = _inputs(command)
    previous = _artifacts(results_dir)
    started = datetime.now(timezone.utc).isoformat()
    failure = None
    result = None
    try:
        result = subprocess.run(command, env=env, check=False)
    except OSError as error:
        failure = error
    finally:
        ended = datetime.now(timezone.utc).isoformat()
        after = source_identity(root)
        current = _artifacts(results_dir)
        changed = [{'path': name, 'sha256': digest} for name, digest in current.items()
                   if previous.get(name) != digest]
        removed = sorted(set(previous) - set(current))
        stable = before['source_sha256'] == after['source_sha256']
        receipt = {'schema_version': 1, 'cycle_id': cycle_id, 'stage': stage,
                   'created_at': ended, 'started_at': started, 'ended_at': ended,
                   'command': command, 'working_directory': str(root.resolve()),
                   'source_before': before, 'source_after': after, 'source_stable': stable,
                   'inputs': inputs, 'changed_artifacts': changed, 'removed_artifacts': removed,
                   'exit_code': result.returncode if result is not None else None,
                   'error_type': type(failure).__name__ if failure else None,
                   'execution_status': 'pass' if result is not None and result.returncode == 0 and stable else 'fail',
                   'quality_gate_status': 'not_assessed_by_receipt'}
        target = results_dir / 'raw/measurement_receipts' / (stage + '_' + uuid.uuid4().hex + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    if failure is not None:
        raise failure
    if not stable:
        raise ValueError('source changed during measurement; failed receipt retained')
    return result
