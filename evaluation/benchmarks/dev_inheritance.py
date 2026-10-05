"""Verify legacy benchmark origin and preserve consumed records strictly in dev.

Historical authorizations keep their original index and timestamps. Expanded
indexes qualify only when every historical document byte is unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PureWindowsPath

from evaluation.common.release_artifacts import read_json, sha256
from .human_benchmark_intake import digest_record


def rows_at(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def safe_reference(root: Path, name: str) -> Path:
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or PureWindowsPath(name).drive or PureWindowsPath(name).root
            or '..' in PureWindowsPath(name).parts or '..' in Path(name).parts):
        raise ValueError('unsafe inheritance reference')
    result=(root/name).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('inheritance reference escapes workspace')
    return result


def file_bindings(directory: Path) -> dict[str, str]:
    return {path.relative_to(directory).as_posix():sha256(path)
            for path in sorted(directory.rglob('*'))
            if path.is_file() and path.name not in {'.gitattributes','.gitignore'}}


def preserved_index(old: Path, current: Path, bindings: dict[str, str]) -> None:
    if file_bindings(old) != bindings:
        raise ValueError('historical index changed')
    old_manifest, current_manifest = read_json(old/'manifest.json'), read_json(current/'manifest.json')
    if not set(old_manifest['documents']) <= set(current_manifest['documents']):
        raise ValueError('expanded index lost historical documents')
    for name,digest in bindings.items():
        if name != 'manifest.json' and sha256(current/name) != digest:
            raise ValueError('historical document bytes changed in expanded index')


def consumed_candidate_rows(benchmark: Path, report_path: Path, index_sha: str) -> list[dict]:
    """Completion consumes exact inputs even when a candidate gate fails."""
    report=read_json(report_path)
    if report.get('status') not in {'pass','conditional'} or report.get('index_sha256') != index_sha:
        raise ValueError('candidate exposure report is incomplete or bound to another index')
    result=[]
    for split in ('dev','test','holdout'):
        dataset=benchmark/f'human_retrieval_{split}.jsonl'
        rows=rows_at(dataset)
        part=report['splits']['human_'+split]
        observations=part['caps']['40']['per_query']
        qids=[row['qid'] for row in rows]
        observed=[item['qid'] for item in observations]
        if (not rows or any(row.get('split') != split for row in rows)
                or part.get('benchmark_sha256') != sha256(dataset)
                or len(qids) != len(set(qids)) or len(observed) != len(set(observed))
                or set(qids) != set(observed)
                or any(not isinstance(item.get('candidates'),list) or len(item['candidates'])>40
                       for item in observations)):
            raise ValueError('candidate exposure does not cover exact frozen split inputs')
        result.extend(rows)
    canonical=rows_at(benchmark/'human_retrieval.jsonl')
    if (len(result) != len(canonical) or len({row['qid'] for row in result}) != len(result)
            or {row['qid']:row for row in result} != {row['qid']:row for row in canonical}):
        raise ValueError('candidate split union differs from frozen canonical dataset')
    return sorted(result,key=lambda row:row['qid'])


def validate_inheritance(manifest: dict, current_index: Path, policy: dict, *, root: Path) -> dict:
    from .freeze_human_benchmark import frozen_evidence
    from .owner_generation import load_generation
    from .owner_review import load_confirmation
    from evaluation.reranker.supplemental_gates import review_audit_errors

    stamp=datetime.fromisoformat(manifest['recorded_at'])
    if (manifest.get('schema_version') != 1 or manifest.get('profile') != 'legacy_source_checked_dev_inheritance_v1'
            or manifest.get('dev_only') is not True or manifest.get('new_heldout_claim') is not False
            or manifest.get('owner_identity') != policy.get('owner_identity')
            or policy.get('owner_self_review_allowed') is not True
            or policy.get('project_scope') != 'single_owner_personal_project'
            or manifest.get('index_sha256') != sha256(current_index/'manifest.json')
            or stamp.tzinfo is None or stamp>datetime.now(timezone.utc)
            or not isinstance(manifest.get('parents'),list) or not manifest['parents']):
        raise ValueError('invalid dev inheritance profile or current index binding')
    frozen_evidence(current_index)
    expected, origins, authorizations = {}, {}, {}
    for parent in manifest['parents']:
        benchmark=safe_reference(root,parent['benchmark_dir'])
        old_index=safe_reference(root,parent['index_dir'])
        if (benchmark/'phase7_dev_inheritance.json').exists():
            raise ValueError('legacy inheritance requires original non-inherited parent records')
        if file_bindings(benchmark) != parent['benchmark_files']:
            raise ValueError('historical benchmark changed')
        preserved_index(old_index,current_index,parent['index_files'])
        old_index_sha=sha256(old_index/'manifest.json')
        confirmation,sources=load_confirmation(benchmark)
        auth,generated=load_generation(benchmark,old_index)
        if (not auth or auth.get('owner_identity') != manifest['owner_identity']
                or confirmation.get('owner_identity') != manifest['owner_identity']
                or ('recorded_at' in confirmation and datetime.fromisoformat(confirmation['recorded_at'])>=stamp)
                or datetime.fromisoformat(auth['recorded_at'])>=stamp):
            raise ValueError('historical owner authorization is missing or does not precede inheritance')
        if parent['mode']=='consumed_candidate_splits':
            report=safe_reference(root,parent['candidate_report'])
            if sha256(report) != parent['candidate_report_sha256']:
                raise ValueError('historical candidate exposure report changed')
            selected=consumed_candidate_rows(benchmark,report,old_index_sha)
        elif parent['mode']=='dev_only_absent_fields':
            selected=[row for row in rows_at(benchmark/'human_retrieval_dev.jsonl')
                      if row['qid'] in generated and row.get('source_validation',{}).get('kind')=='dev_absent_field']
            dev_auth=auth.get('_validated_dev_authorization')
            if (not dev_auth or dev_auth.get('dev_only') is not True or not selected
                    or any(row != generated[row['qid']] or row.get('split') != 'dev'
                           or row.get('generation_authorization_sha256') != digest_record(dev_auth) for row in selected)):
                raise ValueError('historical absence extension is not validated dev-only source material')
        else:
            raise ValueError('unsupported dev inheritance exposure mode')
        if sorted(row['qid'] for row in selected) != parent.get('qids'):
            raise ValueError('inheritance selection differs from complete declared exposure class')
        selected_qids={row['qid'] for row in selected}
        audit=[item for item in rows_at(benchmark/'human_retrieval_review_audit.jsonl')
               if item['qid'] in selected_qids]
        errors=review_audit_errors(selected,audit,old_index,
            owner_identity=manifest['owner_identity'],owner_confirmation=confirmation,
            confirmed_sources=sources,generation_authorization=auth,generated_records=generated)
        if errors:
            raise ValueError('historical selected-record review audit failed: '+', '.join(errors))
        for row in selected:
            qid=row['qid']
            if qid in expected:
                raise ValueError('duplicate inherited qid')
            expected[qid]={**row,'split':'dev'}
            origins[qid]={'benchmark_dir':parent['benchmark_dir'],'original_record_sha256':digest_record(row),
                          'original_split':row['split'],'original_index_sha256':old_index_sha}
        for declaration in (auth.get('_validated_dev_authorization'),
                            {k:v for k,v in auth.items() if k != '_validated_dev_authorization'}):
            if declaration:
                if datetime.fromisoformat(declaration['recorded_at'])>=stamp:
                    raise ValueError('historical authorization must precede inheritance')
                authorizations[digest_record(declaration)]=declaration
    if len(expected) != manifest.get('records'):
        raise ValueError('dev inheritance record count differs')
    return {'rows':expected,'origins':origins,'authorizations':authorizations,
            'manifest_sha256':digest_record(manifest),'dev_only':True,'new_heldout_claim':False}


def load_dev_inheritance(benchmark: Path, index: Path, policy: dict, auth: dict) -> dict | None:
    path=benchmark/'phase7_dev_inheritance.json'
    binding=auth.get('dev_inheritance_sha256')
    if not path.exists() and binding is None:
        return None
    if not path.exists() or binding != sha256(path):
        raise ValueError('dev inheritance manifest is missing or changed')
    root=Path(__file__).resolve().parents[2]
    result=validate_inheritance(read_json(path),index,policy,root=root)
    result['artifact_sha256']=sha256(path)
    return result


def inheritance_audit(bundle: dict) -> list[dict]:
    return [{'qid':qid,'review_evidence_kind':'validated_dev_inheritance',
             'inheritance_manifest_sha256':bundle['manifest_sha256'],
             'original_record_sha256':bundle['origins'][qid]['original_record_sha256'],
             'exported_record_sha256':digest_record(row)} for qid,row in sorted(bundle['rows'].items())]


def inheritance_review_error(row: dict, item: dict, authorization: dict | None) -> bool:
    bundle=(authorization or {}).get('_validated_dev_inheritance')
    if not bundle or bundle.get('dev_only') is not True:
        return True
    qid=row['qid']; expected=bundle['rows'].get(qid); origin=bundle['origins'].get(qid)
    return (row.get('split') != 'dev' or not expected or not origin or row != expected
            or item.get('inheritance_manifest_sha256') != bundle['manifest_sha256']
            or item.get('original_record_sha256') != origin['original_record_sha256']
            or item.get('exported_record_sha256') != digest_record(expected))
