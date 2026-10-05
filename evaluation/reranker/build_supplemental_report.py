"""Assemble S reports from archived observations and recompute verdicts.

This command does not collect measurements, approve reviews or repair inputs.
S4 uses the separate paired-answer CLI to bind its frozen semantic rubric.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.reranker_release_gates import ARTIFACTS, default_args
from evaluation.reranker.supplemental_gates import (
    SUPPLEMENTAL, lineage_errors, context_errors, statistics_errors,
    complete_evidence_errors, observability_errors,
)


def archive_lineage_observations(review_audit: Path, results_dir: Path,
                                 benchmark_dir: Path) -> Path:
    """Bind an actual review audit to the current exposure registry without inference."""
    review_audit = review_audit.resolve()
    results_dir = results_dir.resolve()
    benchmark_dir = benchmark_dir.resolve()
    if not review_audit.is_file():
        raise ValueError("review audit does not exist")

    audit_bytes = review_audit.read_bytes()
    audit_sha = sha256(review_audit)
    raw_dir = results_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    audit_copy = raw_dir / f"lineage_review_audit_{audit_sha[:16]}.jsonl"
    if audit_copy.exists():
        if audit_copy.read_bytes() != audit_bytes:
            raise ValueError("content-addressed review audit path contains different bytes")
    else:
        audit_copy.write_bytes(audit_bytes)

    registry_path = benchmark_dir / "phase7_exposure_registry.json"
    registry = read_json(registry_path)
    records = registry.get("records")
    if not isinstance(records, list):
        raise ValueError("exposure registry has no record list")
    exposure = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("qid"), str):
            raise ValueError("exposure registry contains an invalid record")
        exposure.append({key: record.get(key) for key in
                         ("qid", "status", "connected_group", "heldout_eligible")})
    observations = {
        "review_audit": {"path": audit_copy.relative_to(results_dir).as_posix(),
                         "sha256": sha256(audit_copy)},
        "review_policy_sha256": sha256(benchmark_dir / "phase7_review_policy.json"),
        "exposure_registry_source_sha256": sha256(registry_path),
        "exposure_registry": exposure,
    }
    confirmation_path = benchmark_dir / "phase7_owner_confirmation.json"
    if confirmation_path.is_file():
        observations["owner_confirmation_source_sha256"] = sha256(confirmation_path)
    generation_path = benchmark_dir / "phase7_generation_authorization.json"
    if generation_path.is_file():
        observations["generation_authorization_source_sha256"] = sha256(generation_path)
    dev_generation_path = benchmark_dir/'phase7_dev_generation_authorization.json'
    if dev_generation_path.is_file():
        observations['dev_generation_authorization_source_sha256'] = sha256(dev_generation_path)
    registry_sha = sha256(registry_path)[:16]
    observation_path = raw_dir / f"lineage_observations_{audit_sha[:16]}_{registry_sha}.json"
    if observation_path.exists():
        if read_json(observation_path) != observations:
            raise ValueError("content-addressed lineage observations changed")
    else:
        write_json(observation_path, observations)
    return observation_path


def assemble(gate: str, cfg: dict, reports: dict, observations: Path | None = None) -> dict:
    stage, name, _ = SUPPLEMENTAL[gate]
    report = {'schema_version': 1, 'gate': gate, 'index_sha256': reports['baseline']['index_sha256']}
    if stage >= 3:
        report.update({field: reports['smoke'][field]
                       for field in ('source_sha256', 'runtime_sha256', 'model_identity_sha256')})
    if gate in {'S3', 'S5'}:
        report['quality_sha256'] = sha256(cfg['quality'])
        errors = statistics_errors(reports['quality']) if gate == 'S3' else complete_evidence_errors(reports['quality'])
    else:
        if observations is None:
            raise ValueError('archived observations are required')
        path, root = observations.resolve(), Path(cfg[name]).parent.resolve()
        if path == Path(cfg[name]).resolve():
            raise ValueError('supplemental report must not overwrite archived observations')
        if not path.is_relative_to(root):
            raise ValueError('archive raw observations under the report directory')
        report['raw'] = {'path': path.relative_to(root).as_posix(), 'sha256': sha256(path)}
        report['observations'] = read_json(path)
        if gate == 'S1':
            report['dataset_sha256'] = sha256(Path(cfg['benchmark_dir']) / 'human_retrieval.jsonl')
            errors = lineage_errors(report, cfg)
        elif gate == 'S2':
            errors = context_errors(report)
        else:
            errors = observability_errors(report, reports)
    report.update(status='conditional' if errors else 'pass', errors=errors)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', choices=('S1', 'S2', 'S3', 'S5', 'S6'), required=True)
    parser.add_argument('--results-dir', type=Path, default=Path('evaluation/results'))
    parser.add_argument('--index-dir', type=Path, default=Path('.tmp/hybrid-index'))
    parser.add_argument('--benchmark-dir', type=Path, default=Path('data/benchmark'))
    parser.add_argument('--observations', type=Path)
    parser.add_argument('--review-audit', type=Path,
                        help='actual owner/reviewer audit JSONL; archive and bind it for S1')
    args = parser.parse_args(argv)
    cfg = vars(default_args(args.results_dir)) | vars(args)
    reports = {name: read_json(Path(cfg[name])) for name in ARTIFACTS if Path(cfg[name]).is_file()}
    try:
        if args.review_audit is not None:
            if args.gate != 'S1' or args.observations is not None:
                raise ValueError('--review-audit is only for S1 and cannot be combined with --observations')
            args.observations = archive_lineage_observations(
                args.review_audit, Path(args.results_dir), Path(args.benchmark_dir))
        report = assemble(args.gate, cfg, reports, args.observations)
    except (OSError, KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        print(json.dumps({'status': 'blocked', 'gate': args.gate, 'error': str(error)}))
        return 1
    write_json(Path(cfg[SUPPLEMENTAL[args.gate][1]]), report)
    print(json.dumps({'status': report['status'], 'gate': args.gate, 'errors': report['errors']}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
