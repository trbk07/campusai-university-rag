"""Validate a Phase 5 report without hand-editable pass flags."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.benchmarks.benchmark_schema import validate_release_records
from evaluation.grounding.grounding_metrics import evaluate_grounding, evaluable_prediction_rows
from campusai.rag.schemas import validate_release_response
from evaluation.grounding.review_evidence import validate_independent_review


def validate(report: dict, *, root: Path | None = None,
             acceptance_scope: str = "public_release") -> list[str]:
    """Fail closed for malformed reports and independently recompute quality."""
    if not isinstance(report, dict):
        return ["report_not_object"]
    try:
        errors = _validate(report, acceptance_scope=acceptance_scope)
        if acceptance_scope not in {"public_release", "phase5_acceptance"}:
            errors.append("acceptance_scope_invalid")
        if acceptance_scope == "public_release" and report.get("acceptance_scope") == "phase5_acceptance":
            errors.append("phase5_acceptance_is_not_public_release")
        rows = report.get("rows")
        metrics = report.get("metrics", {})
        if isinstance(rows, list):
            errors.extend(validate_independent_review(report.get("annotation_signoff"), rows,
                          benchmark_sha256=report.get("benchmark_sha256", ""), root=root,
                          acceptance_scope=acceptance_scope))
            for index, row in enumerate(rows):
                public = row.get("public_response")
                valid, _schema_errors = validate_release_response(public)
                if not valid or row.get("schema_valid") is not True:
                    errors.append(f"row_{index}_public_schema_invalid")
                elif (public.get("answer") != row.get("answer")
                      or public.get("abstained") != row.get("abstained")
                      or public.get("citations") != row.get("citations")
                      or [(claim["claim_id"], claim["text"], claim["citation_ids"]) for claim in public.get("claims", [])]
                      != [(claim["claim_id"], claim["text"], claim["citation_ids"]) for claim in row.get("claims", [])]):
                    errors.append(f"row_{index}_public_output_mismatch")
            calculated = evaluate_grounding(rows, allow_reviewed_source_subspan=True)
            for field, value in calculated.items():
                if metrics.get(field) != value:
                    errors.append(f"metrics_recomputed_mismatch_{field}")
            for group, key in (("split_metrics", "split"), ("category_metrics", "category")):
                expected_groups = {row.get(key) for row in rows}
                declared = report.get(group, {})
                if set(declared) != expected_groups:
                    errors.append(f"{group}_population_mismatch")
                for value in expected_groups:
                    expected = evaluate_grounding([row for row in rows if row.get(key) == value],
                        allow_reviewed_source_subspan=True)
                    if declared.get(value) != expected:
                        errors.append(f"{group}_recomputed_mismatch_{value}")
        generation = report.get("generation", {})
        if generation.get("kind") not in {"native", "replay", "native_checkpoint"} or generation.get("gold_seeded") is not False:
            errors.append("release_requires_non_gold_generation")
        checkpoint=generation.get('kind')=='native_checkpoint'
        if checkpoint:
            if acceptance_scope!='phase5_acceptance':
                errors.append('checkpoint_is_internal_acceptance_only')
            if generation.get('protocol')!='native-http-checkpoint-v1':
                errors.append('checkpoint_protocol_invalid')
            if root is None:
                errors.append('checkpoint_requires_physical_verification')
        elif generation.get("kind") != "native":
            errors.append("release_requires_native_inference")
        elif not generation.get("native_runs") and (not generation.get("native_run_path") or not generation.get("native_run_sha256")):
            errors.append("native_capture_binding_missing")
        if root is not None:
            if checkpoint:
                from evaluation.grounding.checkpoint_release import verify_checkpoint_report
                errors.extend(verify_checkpoint_report(report,root))
            else:
                errors.extend(_verify_bindings(report, root))
        return sorted(set(errors))
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError, OSError):
        return ["report_structure_invalid"]


def _verify_bindings(report: dict, root: Path) -> list[str]:
    """Check physical inputs and current source, never a report's pass flags."""
    import hashlib
    from evaluation.common.release_artifacts import source_identity
    from campusai.rag.calibration import load_calibration_artifact, IsotonicCalibrator
    from evaluation.grounding.calibrate_confidence import evaluate_calibrator, risk_at_coverage, _score, _label
    from evaluation.grounding.native_artifacts import (
        BASE_RUN_IDENTITY_FIELDS, load_native_run, native_calibration_matches,
    )
    errors = []
    root = root.resolve()
    from evaluation.grounding.scoring_provenance import source_tree_dirty
    if source_tree_dirty(root):
        errors.append('working_tree_dirty')
    if report.get("source_identity") != source_identity(root):
        errors.append("current_source_identity_mismatch")
    paths = {"benchmark": report.get("benchmark"),
             "calibration_artifact": report.get("calibration_artifact_path"),
             "annotation_signoff": report.get("annotation_signoff_path")}
    resolved = {}
    for name, value in paths.items():
        if not isinstance(value, str) or not value:
            errors.append(f"{name}_path_missing")
            continue
        path = (root / value).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append(f"{name}_path_invalid")
            continue
        resolved[name] = path
    expected = {}
    if "benchmark" in resolved:
        expected = {row["id"]: row for row in
                    (json.loads(line) for line in resolved["benchmark"].read_text(encoding="utf-8").splitlines()
                     if line.strip())}
    generation = report.get("generation", {})
    expected_native_source = report.get('source_identity')
    if generation.get('scoring_source_binding') is not None:
        from evaluation.grounding.scoring_provenance import verify_scoring_source
        try:
            expected_native_source = verify_scoring_source(generation['scoring_source_binding'], root)
        except (OSError, ValueError, TypeError, KeyError):
            errors.append('scoring_source_binding_invalid')
    bindings = generation.get("native_runs")
    if bindings is None:
        bindings = [{"path": generation.get("native_run_path"), "sha256": generation.get("native_run_sha256")}]
    if not isinstance(bindings, list) or not bindings:
        errors.append("native_capture_binding_missing")
        bindings = []
    predictions = []
    calibrated_predictions = []
    native_runs = []
    native_paths = set()
    for binding in bindings:
        value = binding.get("path")
        if not isinstance(value, str) or not value:
            errors.append("native_run_path_missing")
            continue
        path = (root / value).resolve()
        if path.name != "run.json" or path in native_paths or not path.is_relative_to(root) or not path.is_file():
            errors.append("native_run_path_invalid_or_duplicate")
            continue
        native_paths.add(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != binding.get("sha256"):
            errors.append("physical_native_run_checksum_mismatch")
        try:
            native, batch_predictions, _raw, _posts = load_native_run(path.parent)
        except (ValueError, TypeError, KeyError, OSError):
            errors.append("native_capture_invalid")
            continue
        native_runs.append(native)
        predictions.extend(batch_predictions)
        packet_value = native.get('egress_packet_path')
        packet_path = (root / packet_value).resolve() if isinstance(packet_value, str) and packet_value else None
        if packet_path is None or not packet_path.is_relative_to(root) or not packet_path.is_file():
            errors.append('native_egress_packet_path_invalid')
        else:
            if hashlib.sha256(packet_path.read_bytes()).hexdigest() != native.get('egress_packet_sha256'):
                errors.append('native_egress_packet_checksum_mismatch')
            packet = json.loads(packet_path.read_text(encoding='utf-8'))
            for field in ('source_identity', 'benchmark_sha256', 'config_sha256',
                          'index_manifest_sha256', 'model', 'document_scope_policy'):
                if field not in packet or packet[field] != native.get(field):
                    errors.append(f'native_egress_packet_{field}_mismatch')
        if native.get('http503_recovery_policy'):
            authority = native.get('http503_recovery_authorization') or {}
            declared = authority.get('path')
            physical = (root / declared).resolve() if isinstance(declared, str) and declared else None
            if (physical is None or not physical.is_relative_to(root) or not physical.is_file()
                    or hashlib.sha256(physical.read_bytes()).hexdigest() != authority.get('sha256')
                    or json.loads(physical.read_text(encoding='utf-8')) != authority.get('decision')):
                errors.append('native_http503_recovery_authority_binding_invalid')
        if (report.get("calibration_artifact_sha256") is not None
                and native.get("calibration_artifact_sha256") == report.get("calibration_artifact_sha256")):
            calibrated_predictions.extend(batch_predictions)
        if native.get("benchmark_sha256") != report.get("benchmark_sha256"):
            errors.append("native_benchmark_checksum_mismatch")
        if native.get("source_identity") != expected_native_source:
            errors.append("native_source_identity_mismatch")
        if not native_calibration_matches(native, batch_predictions, expected,
                report.get("calibration_artifact_sha256"), generation.get("calibration_protocol")):
            errors.append("native_calibration_identity_mismatch")
        from evaluation.common.release_artifacts import verify_index_files
        for kind, path_field, hash_field in (("config", "config_path", "config_sha256"),
                ("index", "index_path", "index_manifest_sha256")):
            declared = native.get(path_field)
            if not isinstance(declared, str) or not declared:
                errors.append(f"native_{kind}_path_missing")
                continue
            physical = (root / declared).resolve()
            target = physical / "manifest.json" if kind == "index" else physical
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"native_{kind}_path_invalid")
            elif hashlib.sha256(target.read_bytes()).hexdigest() != native.get(hash_field):
                errors.append(f"native_{kind}_checksum_mismatch")
            elif kind == "index" and not verify_index_files(physical):
                errors.append("native_index_files_invalid")
            elif kind == "config":
                from campusai.llm.factory import _read_config
                if _read_config(physical).get("llm", {}).get("model") != native.get("model"):
                    errors.append("native_config_model_mismatch")
        if any(item.get("provider_failure") or "error_type" in item for item in batch_predictions):
            errors.append("native_provider_or_pipeline_failure")
        if native.get('stop_reason') is not None:
            errors.append('native_run_incomplete')
    if native_runs:
        if any(any(run.get(key) != native_runs[0].get(key) for key in BASE_RUN_IDENTITY_FIELDS) for run in native_runs[1:]):
            errors.append("native_batch_identity_mismatch")
        public_by_id = {item["id"]: item.get("public_response") for item in predictions}
        if (len(public_by_id) != len(predictions)
                or public_by_id != {row["id"]: row.get("public_response") for row in report.get("rows", [])}):
            errors.append("native_prediction_output_mismatch")
        by_id = {item["id"]: item for item in predictions}
        score_fields = ("confidence", "confidence_score", "raw_confidence_score", "evidence_status")
        if any(any(row.get(field) != by_id.get(row["id"], {}).get("internal_response", {}).get(field)
                   for field in score_fields) for row in report.get("rows", [])):
            errors.append("native_prediction_score_mismatch")
        counts = {key: sum(run[key] for run in native_runs) for key in ("pipeline_predictions", "provider_posts",
            "real_model_outputs_successful", "real_json_predictions_successful", "official_predictions")}
        if report.get("native_output_counts") is not None and report["native_output_counts"] != counts:
            errors.append("native_output_counts_mismatch")
    if "annotation_signoff" in resolved:
        path = resolved["annotation_signoff"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != report.get("annotation_signoff_sha256"):
            errors.append("physical_annotation_signoff_checksum_mismatch")
        if json.loads(path.read_text(encoding="utf-8")) != report.get("annotation_signoff"):
            errors.append("annotation_signoff_embedded_evidence_mismatch")
    if "benchmark" in resolved:
        path = resolved["benchmark"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != report.get("benchmark_sha256"):
            errors.append("physical_benchmark_checksum_mismatch")
        from evaluation.grounding.collect_native_predictions import inference_request
        if any(item["id"] not in expected or item.get("request") != inference_request(expected[item["id"]])
               for item in predictions):
            errors.append("native_request_projection_mismatch")
        rows = report.get("rows", [])
        if {row.get("id") for row in rows} != set(expected):
            errors.append("benchmark_row_population_mismatch")
        fields = ("question", "split", "language", "category", "answerable", "gold_claims",
                  "gold_abstention_reason", "source_group", "template_group", "semantic_topic", "adversarial_pattern")
        if any(any(row.get(field) != expected.get(row.get("id"), {}).get(field) for field in fields)
               for row in rows):
            errors.append("benchmark_annotations_mismatch")
    if "calibration_artifact" in resolved:
        try:
            calibrator, _digest = load_calibration_artifact(resolved["calibration_artifact"],
                expected_sha256=report.get("calibration_artifact_sha256"))
            for prediction in calibrated_predictions:
                public = prediction.get("public_response", {})
                internal = prediction.get("internal_response", {})
                if public.get("abstained") is not False:
                    continue
                raw_score = internal.get("raw_confidence_score")
                if (type(raw_score) not in {int, float} or not math.isfinite(raw_score)
                        or not 0 <= raw_score <= 1):
                    errors.append("native_calibrated_score_mismatch")
                    continue
                calibrated_score = calibrator.predict(raw_score)
                label = "high" if calibrated_score >= 0.85 else "medium" if calibrated_score >= 0.65 else "low"
                if (internal.get("confidence_score") != round(calibrated_score, 6)
                        or internal.get("confidence_policy_version") != calibrator.version
                        or internal.get("confidence") != label or public.get("confidence") != label):
                    errors.append("native_calibrated_score_mismatch")
            rows = report.get("rows", [])
            payload = json.loads(resolved["calibration_artifact"].read_text(encoding="utf-8"))
            if payload.get("fit_split") != "dev" or payload.get("benchmark_sha256") != report.get("benchmark_sha256"):
                errors.append("physical_calibration_provenance_invalid")
            valid_rows = evaluable_prediction_rows(rows)
            dev = [row for row in valid_rows if row.get("split") == "dev"]
            fitted = IsotonicCalibrator.fit([_score(row) for row in dev], [_label(row) for row in dev])
            if fitted.to_dict() != calibrator.to_dict():
                errors.append("calibration_dev_fit_mismatch")
            population = {split: {"count": len(subset), "positive": sum(_label(row) for row in subset),
                "negative": sum(not _label(row) for row in subset)} for split in ("dev", "test", "holdout")
                if (subset := [row for row in valid_rows if row.get("split") == split])}
            if report.get("calibration_population") != population:
                errors.append("calibration_label_population_mismatch")
            if report.get("calibration") != evaluate_calibrator(rows, calibrator):
                errors.append("calibration_recomputed_mismatch")
            for coverage in (0.8, 0.9):
                if report.get("risk_at_coverage", {}).get(str(coverage)) != risk_at_coverage(rows, calibrator, coverage):
                    errors.append(f"risk_recomputed_mismatch_{coverage}")
        except (ValueError, TypeError, KeyError):
            errors.append("physical_calibration_invalid")
    return errors


def _validate(report: dict, *, acceptance_scope: str = "public_release") -> list[str]:
    metrics = report.get("metrics", {})
    errors = []
    if not isinstance(metrics, dict):
        return ["metrics_not_object"]
    numeric_fields = (
        "unsupported_claim_leakage", "contradicted_claim_leakage", "citation_precision",
        "citation_recall", "citation_completeness", "citation_coordinate_validity",
        "claim_citation_precision", "claim_citation_recall", "claim_citation_f1",
        "grounded_claim_precision", "grounded_claim_recall", "schema_invalid_rate",
        "abstention_precision", "abstention_recall", "reason_accuracy", "ece", "brier_score",
        "calibration_count",
    )
    for field in numeric_fields:
        value = metrics.get(field)
        if type(value) not in {int, float} or not math.isfinite(value):
            errors.append(f"metric_{field}_missing_or_non_finite")
    if errors:
        # Preserve the named legacy gate errors as well as the type error.
        metrics = {field: value for field, value in metrics.items()
                   if type(value) in {int, float} and math.isfinite(value)}
    if report.get("mode") != "runtime":
        errors.append("release_requires_runtime_mode")
    if report.get("schema_version") != 2:
        errors.append("report_schema_version_invalid")
    if not report.get("policy_version"):
        errors.append("policy_version_missing")
    if not report.get("benchmark_sha256"):
        errors.append("benchmark_checksum_missing")
    if not report.get("metadata", {}).get("commit"):
        errors.append("commit_fingerprint_missing")
    if report.get("metadata", {}).get("working_tree") is not False:
        errors.append("working_tree_dirty")
    dataset = report.get("dataset", {})
    if dataset.get("sha256") and report.get("benchmark_sha256") != dataset.get("sha256"):
        errors.append("benchmark_checksum_mismatch")
    if report.get("calibration_artifact_version") and not report.get("calibration_artifact_sha256"):
        errors.append("calibration_checksum_missing")
    if report.get("mode") == "runtime" and not report.get("calibration_artifact_version"):
        errors.append("runtime_calibration_missing")
    if report.get("mode") == "runtime" and not report.get("calibration_artifact_sha256"):
        errors.append("runtime_calibration_checksum_missing")
    if report.get("mode") == "runtime":
        if report.get("calibration_benchmark_sha256") != report.get("benchmark_sha256"):
            errors.append("calibration_benchmark_checksum_mismatch")
        population = report.get("calibration_population") or {}
        for split in ("dev", "test", "holdout"):
            labels = population.get(split, {})
            if labels.get("positive", 0) <= 0 or labels.get("negative", 0) <= 0:
                errors.append(f"calibration_{split}_label_degenerate")
    rows = report.get("rows")
    if report.get("mode") == "runtime":
        if not isinstance(rows, list):
            errors.append("report_rows_missing")
        else:
            errors.extend(f"dataset_{error}" for error in validate_release_records(rows, acceptance_scope=acceptance_scope))
            if report.get("dataset_count") != len(rows):
                errors.append("dataset_count_rows_mismatch")
    if metrics.get("unsupported_claim_leakage", 1) != 0:
        errors.append("unsupported_claim_leakage")
    if metrics.get("contradicted_claim_leakage", 1) != 0:
        errors.append("contradicted_claim_leakage")
    if metrics.get("citation_precision", 0) < 0.99:
        errors.append("citation_precision")
    if metrics.get("citation_recall", 0) < 0.98:
        errors.append("citation_recall")
    if metrics.get("citation_completeness", 0) < 0.98:
        errors.append("citation_completeness")
    if metrics.get("citation_coordinate_validity", 0) < 1.0:
        errors.append("citation_coordinate_validity")
    if metrics.get("claim_citation_precision", 0) < 0.95:
        errors.append("claim_citation_precision")
    if metrics.get("claim_citation_recall", 0) < 0.95:
        errors.append("claim_citation_recall")
    if metrics.get("claim_citation_f1", 0) < 0.95:
        errors.append("claim_citation_f1")
    if metrics.get("grounded_claim_precision", 0) < 0.99:
        errors.append("grounded_claim_precision")
    if metrics.get("grounded_claim_recall", 0) < 0.95:
        errors.append("grounded_claim_recall")
    if metrics.get("schema_invalid_rate", 1) != 0:
        errors.append("schema_invalid_rate")
    if metrics.get("abstention_precision", 0) < 0.99:
        errors.append("abstention_precision")
    if metrics.get("abstention_recall", 0) < 0.98:
        errors.append("abstention_recall")
    if metrics.get("reason_accuracy", 0) < 0.95:
        errors.append("reason_accuracy")
    if metrics.get("ece", 1) > 0.05:
        errors.append("ece")
    if metrics.get("brier_score", 1) > 0.08:
        errors.append("brier_score")
    if metrics.get("calibration_count", 0) < 400:
        errors.append("calibration_sample_too_small")
    if report.get("dataset_count", 0) < 400:
        errors.append("dataset_too_small_for_release")
    calibration = report.get("calibration", {})
    if report.get("mode") == "runtime" and report.get("risk_population") != "holdout":
        errors.append("risk_population_must_be_holdout")
    for split in ("dev", "test", "holdout"):
        split_metrics = calibration.get(split, {})
        for field in ("ece", "brier_score"):
            value = split_metrics.get(field)
            if type(value) not in {int, float} or not math.isfinite(value):
                errors.append(f"calibration_{split}_{field}_invalid")
        if split_metrics.get("count", 0) <= 0:
            errors.append(f"calibration_{split}_missing")
        if split not in report.get("split_metrics", {}):
            errors.append(f"split_metrics_{split}_missing")
    if not isinstance(report.get("category_metrics"), dict) or not report.get("category_metrics"):
        errors.append("category_metrics_missing")
    if calibration.get("holdout", {}).get("ece", 1) > 0.05:
        errors.append("holdout_ece")
    if calibration.get("holdout", {}).get("brier_score", 1) > 0.08:
        errors.append("holdout_brier_score")
    for coverage, maximum in ((0.80, 0.01), (0.90, 0.02)):
        risk = report.get("risk_at_coverage", {}).get(str(coverage))
        if type(risk) not in {int, float} or not math.isfinite(risk):
            errors.append(f"risk_at_{int(coverage * 100)}_coverage_missing")
        elif risk > maximum:
            errors.append(f"risk_at_{int(coverage * 100)}_coverage")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--acceptance-scope", choices=("public_release", "phase5_acceptance"), default="public_release")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    errors = validate(report, root=Path(__file__).resolve().parents[2], acceptance_scope=args.acceptance_scope)
    print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
