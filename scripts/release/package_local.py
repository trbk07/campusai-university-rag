"""Build a local source distribution from allowlisted immutable Git blobs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
EXACT={'.env.example','README.md','plan.md','pyproject.toml','uv.lock','start-campusai.cmd',
    'configs/free_llm.yaml','configs/free_multi_project.yaml',
    'configs/local/dense-manifest.json','configs/local/runtime-assets.json',
    'docs/operations/local-install.md','docs/operations/local-third-party.md','docs/PROJECT_OVERVIEW.md',
    'scripts/__init__.py','scripts/operations/__init__.py',
    *(f'scripts/operations/{name}.py' for name in (
        'local','local_state','encoder_assets','serve','with_gemini_key','setup_encoder','setup_ocr','setup_vietocr'))}
SOURCE_SUFFIXES={'.py','.html','.css','.js','.LICENSE'}
SECRET_PATTERNS=(re.compile(rb'AIza[0-9A-Za-z_-]{20,}'), re.compile(rb'\bsk-[A-Za-z0-9]{20,}\b'))


def selected(name):
    return name in EXACT or (name.startswith('src/campusai/') and PurePosixPath(name).suffix in SOURCE_SUFFIXES)


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args])


def build(root:Path,commit:str,output:Path) -> dict:
    """No working-tree bytes, untracked data or symlinks enter the ZIP."""
    identity=git(root,'rev-parse','--verify','--end-of-options',commit+'^{commit}').decode().strip()
    if not re.fullmatch('[0-9a-f]{40}',identity):
        raise ValueError('exact_source_commit_required')
    if output.exists():
        raise ValueError('output_exists_keep_previous_candidate')
    sidecar=output.with_suffix(output.suffix+'.json')
    if sidecar.exists():
        raise ValueError('sidecar_exists_keep_previous_identity')
    inventory={}
    blobs={}
    for item in git(root,'ls-tree','-rz','--full-tree',identity).split(b'\0'):
        if not item:continue
        metadata,raw_name=item.split(b'\t',1)
        mode,kind,oid=metadata.decode().split()
        name=raw_name.decode('utf-8')
        if not selected(name):continue
        if mode not in {'100644','100755'} or kind!='blob':
            raise ValueError('release_input_must_be_regular_blob')
        if any(part in {'.env','.git','.venv','__pycache__','node_modules'} for part in PurePosixPath(name).parts):
            raise ValueError('forbidden_release_path')
        payload=git(root,'cat-file','blob',oid)
        if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
            raise ValueError('release_secret_pattern_detected')
        blobs[name]=payload
        inventory[name]={'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
    if not EXACT<=set(blobs):
        raise ValueError('source_commit_missing_required_files: '+','.join(sorted(EXACT-set(blobs))))
    if not any(name.startswith('src/campusai/ui/') for name in blobs):
        raise ValueError('release_ui_missing')
    manifest={'schema_version':1,'kind':'local-source-bundle','source_commit':identity,
        'files':dict(sorted(inventory.items())),
        'not_included':['Python environment','model weights','credentials','personal PDFs','runtime state','historical raw evidence'],
        'scope':'Packaging identity only; not clean-install, QA PDF, RC or publication acceptance'}
    output.parent.mkdir(parents=True,exist_ok=True)
    # Fixed timestamps also make the ZIP deterministic on the same Python runtime.
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,payload in sorted({**blobs,'bundle-manifest.json':
            (json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode('utf-8')}.items()):
            info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100644<<16)
            archive.writestr(info,payload,compresslevel=9)
    summary={**manifest,'zip_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'zip_bytes':output.stat().st_size,'zip_filename':output.name}
    sidecar.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',required=True,help='Commit to bind; working tree is never packaged')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=build(ROOT,args.commit,args.output)
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        parser.exit(1,'Local bundle failed: '+(str(error) if isinstance(error,ValueError) else type(error).__name__)+'\n')
    print(json.dumps({k:result[k] for k in ('kind','source_commit','zip_sha256','zip_bytes')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
