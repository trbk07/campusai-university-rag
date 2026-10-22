"""Score captured CampusAI predictions in a separate process from inference."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

from campusai.rag.schemas import validate_response, validate_release_response
from campusai.rag.calibration import load_calibration_artifact, IsotonicCalibrator
from evaluation.common.release_artifacts import source_identity, write_json
from evaluation.grounding.collect_native_predictions import inference_request
from evaluation.grounding.calibrate_confidence import evaluate_calibrator, risk_at_coverage, _score, _label
from evaluation.grounding.grounding_metrics import evaluate_grounding, is_native_evaluation_failure
from evaluation.grounding.native_artifacts import (
    BASE_RUN_IDENTITY_FIELDS, CALIBRATION_PROTOCOL, load_native_run, native_calibration_matches,
)
from evaluation.grounding.repair_benchmark import load_rows
from evaluation.grounding.validate_grounding_release import validate


def score(benchmark: Path, native_dir: Path | list[Path], root: Path, signoff: Path | None = None,
          calibration: Path | None = None, calibration_sha256: str | None = None,
          *, acceptance_scope: str = "public_release") -> dict:
    directories = [native_dir] if isinstance(native_dir, Path) else list(native_dir)
    if not directories or len({path.resolve() for path in directories}) != len(directories):
        raise ValueError("native batches must be non-empty and unique")
    batches = [load_native_run(path) for path in directories]
    run = batches[0][0]
    if any(any(batch[0].get(key) != run.get(key) for key in BASE_RUN_IDENTITY_FIELDS) for batch in batches[1:]):
        raise ValueError("native batches have different benchmark/source/model/config/index identities")
    benchmark_hash = hashlib.sha256(benchmark.read_bytes()).hexdigest()
    if benchmark_hash != run.get("benchmark_sha256"):
        raise ValueError("native benchmark checksum mismatch")
    gold = {row["id"]: row for row in load_rows(benchmark)}
    rows = []
    seen = set()
    predictions = [item for batch in batches for item in batch[1]]
    for prediction in predictions:
        identifier = prediction["id"]
        if identifier in seen or identifier not in gold:
            raise ValueError("native prediction population invalid")
        seen.add(identifier)
        if prediction["request"] != inference_request(gold[identifier]):
            raise ValueError("native request differs from user-input-only benchmark projection")
        public = prediction.get("public_response", {})
        internal = prediction.get("internal_response", {})
        claims = [claim for claim in internal.get("claims", [])
                  if claim["claim_id"] in {item["claim_id"] for item in public.get("claims", [])}]
        rows.append({**deepcopy(gold[identifier]), **internal,
            "answer": public.get("answer"), "abstained": public.get("abstained"),
            "claims": claims, "citations": public.get("citations", []),
            "abstention_reason": public.get("abstention_reason"),
            "public_response": public, "internal_trace": internal,
            "native_failure": (prediction.get("provider_failure")
                or ({"error_type": prediction.get("error_type")} if prediction.get("error_type") else None)),
            "schema_valid": validate_release_response(public)[0] and validate_response(internal, include_internal=True)[0],
            "citation_valid": validate_release_response(public)[0],
            "retrieved_pages": sorted({f"{item['doc_id']}:{item['page']}" for item in prediction.get("retrieved_evidence", [])})})
    evaluable_ids = {row["id"] for row in rows if not is_native_evaluation_failure(row)}
    failed_ids = sorted(row["id"] for row in rows if is_native_evaluation_failure(row))
    current = source_identity(root)
    native_bindings = [{"path": str(path / "run.json"),
                        "sha256": hashlib.sha256((path / "run.json").read_bytes()).hexdigest()}
                       for path in directories]
    calibrator = None
    calibration_payload = {}
    if calibration is not None:
        calibration_payload = json.loads(calibration.read_text(encoding="utf-8"))
        calibrator, calibration_sha256 = load_calibration_artifact(calibration, expected_sha256=calibration_sha256)
        if calibration_payload.get("fit_split") != "dev" or calibration_payload.get("benchmark_sha256") != benchmark_hash:
            raise ValueError("native calibration must bind this benchmark and declare dev-only fitting")
        dev = [row for row in rows if row["split"] == "dev" and not is_native_evaluation_failure(row)]
        fitted = IsotonicCalibrator.fit([_score(row) for row in dev], [_label(row) for row in dev])
        if fitted.to_dict() != calibrator.to_dict():
            raise ValueError("native calibration differs from dev-only fit on captured predictions")
    elif calibration_sha256 is not None:
        raise ValueError("calibration checksum requires an artifact")
    calibration_protocol = CALIBRATION_PROTOCOL if calibrator else None
    if (len({batch[0].get("calibration_artifact_sha256") for batch in batches}) > 1
            and not all(native_calibration_matches(batch[0], batch[1], gold,
                        calibration_sha256, calibration_protocol) for batch in batches)):
        raise ValueError("native batches have different benchmark/source/model/config/index identities")
    report = {"schema_version": 2, "phase": "grounding", "mode": "runtime",
        "benchmark": str(benchmark), "benchmark_sha256": benchmark_hash,
        "dataset_count": len(rows), "benchmark_population": len(gold),
        "collection_complete": evaluable_ids == set(gold),
        "missing_prediction_ids": sorted(set(gold) - evaluable_ids),
        "failed_prediction_ids": failed_ids,
        "dataset": {"sha256": benchmark_hash}, "policy_version": "grounding-v1",
        "metadata": {"commit": current["commit"], "working_tree": bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True).strip())},
        "source_identity": current, "inference_source_identity": run.get("source_identity"),
        "generation": {"kind": "native", "gold_seeded": False, "model": run.get("model"),
                       "calibration_protocol": calibration_protocol,
                       "native_runs": native_bindings,
                       "native_run_path": native_bindings[0]["path"] if len(batches) == 1 else None,
                       "native_run_sha256": native_bindings[0]["sha256"] if len(batches) == 1 else None},
        "metrics": evaluate_grounding(rows, allow_reviewed_source_subspan=True), "rows": rows,
        "split_metrics": {value: evaluate_grounding([row for row in rows if row["split"] == value],
            allow_reviewed_source_subspan=True)
                          for value in sorted({row["split"] for row in rows})},
        "category_metrics": {value: evaluate_grounding([row for row in rows if row["category"] == value],
            allow_reviewed_source_subspan=True)
                             for value in sorted({row["category"] for row in rows})},
        "calibration": evaluate_calibrator(rows, calibrator) if calibrator else {},
        "risk_at_coverage": {str(value): risk_at_coverage(rows, calibrator, value)
            for value in (0.8, 0.9)} if calibrator and any(row["split"] == "holdout" for row in rows) else {},
        "calibration_artifact_path": str(calibration) if calibration else None,
        "calibration_artifact_version": calibrator.version if calibrator else None,
        "calibration_artifact_sha256": calibration_sha256,
        "calibration_benchmark_sha256": calibration_payload.get("benchmark_sha256"),
        "calibration_population": {split: {"count": len(subset), "positive": sum(_label(row) for row in subset),
            "negative": sum(not _label(row) for row in subset)} for split in ("dev", "test", "holdout")
            if (subset := [row for row in rows if row["split"] == split and not is_native_evaluation_failure(row)])} if calibrator else None,
        "risk_population": "holdout",
        "annotation_signoff": json.loads(signoff.read_text(encoding="utf-8")) if signoff else None,
        "annotation_signoff_path": str(signoff) if signoff else None,
        "annotation_signoff_sha256": hashlib.sha256(signoff.read_bytes()).hexdigest() if signoff else None,
        "native_output_counts": {key: sum(batch[0][key] for batch in batches) for key in
            ("pipeline_predictions", "provider_posts", "real_model_outputs_successful",
             "real_json_predictions_successful", "official_predictions")}}
    report["acceptance_scope"] = acceptance_scope
    report["release_errors"] = validate(report, root=root, acceptance_scope=acceptance_scope)
    report["release_status"] = "BLOCKED" if report["release_errors"] else "PASS"
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/grounding_reviewed.jsonl"))
    parser.add_argument("--native-dir", type=Path, action="append", required=True,
                        help="Repeat for disjoint batches with identical source/model/config/index bindings")
    parser.add_argument("--annotation-signoff", type=Path)
    parser.add_argument("--calibration-artifact", type=Path)
    parser.add_argument("--calibration-sha256")
    parser.add_argument("--acceptance-scope", choices=("public_release", "phase5_acceptance"), default="public_release")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = score(args.benchmark, args.native_dir, Path.cwd(), args.annotation_signoff,
                   args.calibration_artifact, args.calibration_sha256, acceptance_scope=args.acceptance_scope)
    write_json(args.output, report)
    print(json.dumps({"release_status": report["release_status"], "predictions": report["dataset_count"],
                      "population": report["benchmark_population"], "release_errors": report["release_errors"]}, indent=2))


if __name__ == "__main__":
    main()
