"""Hash an existing BGE snapshot; does not download or load model weights."""
import argparse
import json
from pathlib import Path
import re

from campusai.deployment.config.preflight import sha


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--revision',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    snapshot = args.snapshot.resolve()
    if not snapshot.is_dir() or not re.fullmatch('[0-9a-f]{40}',args.revision):
        parser.error('Existing snapshot and full commit revision required')
    if args.output.exists():
        parser.error('Refusing to overwrite a previous identity manifest')
    files = {p.relative_to(snapshot).as_posix():sha(p) for p in sorted(snapshot.rglob('*'))
             if p.is_file() and '.cache' not in p.relative_to(snapshot).parts}
    manifest = {'schema_version':1,'model':'BAAI/bge-m3','revision':args.revision,'files':files}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(files),'manifest_sha256':sha(args.output),
                      'provider_calls':0,'model_loads':0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
