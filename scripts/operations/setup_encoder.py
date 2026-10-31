"""Install the pinned BGE encoder explicitly, with streaming checksum checks."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import quote
from urllib.request import urlopen

from .encoder_assets import configure_encoder, verify_encoder

ROOT = Path(__file__).resolve().parents[2]


def install_encoder(manifest: dict, output: Path, *, source_dir: Path | None = None) -> dict:
    """Never overwrite corrupt files; partial downloads stay unpublished."""
    files, sizes = manifest['files'], manifest['file_bytes']
    if set(files) != set(sizes):
        raise ValueError('encoder_manifest_sizes_incomplete')
    # Validate the whole allowlist before doing any writes or network requests.
    for name, digest in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                or not name or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)
                or type(sizes[name]) is not int or sizes[name] < 0):
            raise ValueError('encoder_manifest_file_invalid')
    output = output.absolute()
    if output.resolve() != output:
        raise ValueError('encoder_output_redirected')
    output.mkdir(parents=True, exist_ok=True)
    network_files, reused_files = 0, 0
    for name, expected in files.items():
        target = output.joinpath(*PurePosixPath(name).parts)
        if target.resolve() != target:
            raise ValueError('encoder_output_redirected')
        if target.exists():
            with target.open('rb') as existing:
                digest = hashlib.file_digest(existing, 'sha256').hexdigest()
            if target.stat().st_size != sizes[name] or digest != expected:
                raise ValueError('existing_encoder_checksum_mismatch_keep_original')
            reused_files += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source_dir is not None:
            source = (source_dir/name).open('rb')
        else:
            url = f"https://huggingface.co/{manifest['model']}/resolve/{manifest['revision']}/{quote(name)}"
            source = urlopen(url, timeout=60)
            network_files += 1
        temporary = None
        try:
            with closing(source), tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temporary = Path(handle.name)
                digest, count = hashlib.sha256(), 0
                while block := source.read(1024*1024):
                    count += len(block)
                    if count > sizes[name]:
                        raise ValueError('encoder_download_size_mismatch')
                    digest.update(block)
                    handle.write(block)
                if count != sizes[name] or digest.hexdigest() != expected:
                    raise ValueError('encoder_download_checksum_mismatch')
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {'files':len(files), 'network_files':network_files, 'reused_files':reused_files,
            'installed_bytes':sum(sizes.values()), 'provider_calls':0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Separate encoder snapshot directory')
    parser.add_argument('--model-cache', type=Path, help='Defaults to local user state/models')
    parser.add_argument('--source-dir', type=Path, help='Copy cached pinned files without network')
    args = parser.parse_args(argv)
    env = dict(os.environ)
    base = Path(env.get('CAMPUSAI_STATE_ROOT') or Path(env.get('LOCALAPPDATA') or Path.home()/'.local/share')/'CampusAI')
    env['CAMPUSAI_MODEL_CACHE'] = str(args.model_cache or env.get('CAMPUSAI_MODEL_CACHE') or base/'models')
    if args.output:
        env['CAMPUSAI_DENSE_SNAPSHOT'] = str(args.output.resolve())
    try:
        manifest = configure_encoder(ROOT, env)
        result = install_encoder(manifest, Path(env['CAMPUSAI_DENSE_SNAPSHOT']), source_dir=args.source_dir)
        verify_encoder(env)
    except (OSError, ValueError) as error:
        # Never echo a URL response body, credential, or arbitrary filesystem error.
        code = str(error) if isinstance(error, ValueError) else 'encoder_setup_io_error_check_disk_permissions_or_network'
        parser.exit(1, f'Encoder setup failed: {code}\n')
    print(json.dumps({'status':'READY', 'model':manifest['model'], 'revision':manifest['revision'], **result}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
