"""Synthetic transport fixtures only; no benchmark approvals or live calls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from campusai.llm.client import GeminiClient
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from evaluation.common.release_artifacts import source_identity
from evaluation.grounding.calibrate_confidence import fit_report
from evaluation.grounding.collect_native_predictions import collect
from evaluation.grounding.native_artifacts import load_native_run
from evaluation.grounding.score_native_predictions import score
from evaluation.grounding.validate_grounding_release import validate
from tests.test_basic_rag import FakeRetriever, evidence, valid_payload
from tests.test_benchmark_schema import row


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def native_batches(tmp_path):
    records = []
    for split in ("dev", "test", "holdout"):
        for positive in (True, False):
            record = row(f"unit-{split}-{positive}", split=split, answerable=positive)
            record["question"] = f"Which prerequisite course? Unit {record['id']}"
            if positive:
                record["gold_claims"] = [{"text": "MATH101 is required.", "evidence": [
                    {"chunk_id": "c1", "doc_id": "doc-1", "page": 3, "quote": "MATH101 is required."}]}]
            records.append(record)
    benchmark = tmp_path / "benchmark.jsonl"
    benchmark.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
    digest = hashlib.sha256(benchmark.read_bytes()).hexdigest()
    directories = []
    for index in range(3):
        directory = tmp_path / f"batch-{index}"
        llm = GeminiClient(api_key="unit-test-placeholder", max_retries=0, cache=None)
        service = CampusAIQueryService(FakeRetriever([evidence()]), GroundedAnswerGenerator(llm))
        def transport(*_args, **_kwargs):
            payload = valid_payload()
            payload["citations"] = [{"chunk_id": "c1", "page": 3, "quote": "MATH101 is required."}]
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
                    "modelVersion": "unit-transport-only"}
        try:
            run = collect(service, records[index * 2:index * 2 + 2], llm,
                          max_provider_calls=2, output=directory, transport=transport)
        finally:
            service.close()
        run.update(benchmark_sha256=digest, source_identity=source_identity(tmp_path),
                   model="unit-transport-only", config_sha256="unit-config", index_manifest_sha256="unit-index")
        write_json(directory / "run.json", run)
        directories.append(directory)
    return tmp_path, benchmark, directories


def test_disjoint_native_batches_form_complete_population_without_inference(native_batches):
    root, benchmark, directories = native_batches
    before = {str(p): p.read_bytes() for d in directories for p in d.iterdir()}
    report = score(benchmark, directories, root)
    assert report["dataset_count"] == report["benchmark_population"] == 6
    assert report["collection_complete"] is True and report["missing_prediction_ids"] == []
    assert report["native_output_counts"]["real_model_outputs_successful"] == 6
    assert len(report["generation"]["native_runs"]) == 3
    assert "native_run_path_missing" not in report["release_errors"]
    assert "native_prediction_output_mismatch" not in report["release_errors"]
    assert report["release_status"] == "BLOCKED"  # Six fictional unit cases, no approval.
    assert {str(p): p.read_bytes() for d in directories for p in d.iterdir()} == before


@pytest.mark.parametrize("field", ["source_identity", "model", "config_sha256", "index_manifest_sha256",
                                  "calibration_artifact_sha256", "document_scope_policy"])
def test_scoring_rejects_mixed_native_batch_identities(native_batches, field):
    root, benchmark, directories = native_batches
    path = directories[1] / "run.json"
    run = json.loads(path.read_text())
    run[field] = "different-unit-identity"
    write_json(path, run)
    with pytest.raises(ValueError, match="different benchmark/source/model/config/index"):
        score(benchmark, directories, root)


@pytest.mark.parametrize('field', ['source_identity', 'benchmark_sha256', 'config_sha256',
                                 'index_manifest_sha256', 'model', 'document_scope_policy'])
def test_physical_validator_rejects_packet_for_a_different_native_runtime(native_batches, field):
    root, benchmark, directories = native_batches
    run_path = directories[0] / 'run.json'
    run = json.loads(run_path.read_text(encoding='utf-8'))
    keys = ('source_identity', 'benchmark_sha256', 'config_sha256',
            'index_manifest_sha256', 'model', 'document_scope_policy')
    packet = {key: run.get(key) for key in keys}
    packet[field] = 'different-fixture-binding'
    packet_path = directories[0] / 'egress.json'
    write_json(packet_path, packet)
    run.update(egress_packet_path=str(packet_path),
               egress_packet_sha256=hashlib.sha256(packet_path.read_bytes()).hexdigest())
    write_json(run_path, run)
    report = score(benchmark, directories, root)
    assert f'native_egress_packet_{field}_mismatch' in report['release_errors']


def test_scoring_rejects_duplicate_batch_and_duplicate_prediction_ids(native_batches):
    root, benchmark, directories = native_batches
    with pytest.raises(ValueError, match="unique"):
        score(benchmark, [directories[0], directories[0]], root)
    duplicate = root / "duplicate"
    shutil.copytree(directories[0], duplicate)
    with pytest.raises(ValueError, match="population invalid"):
        score(benchmark, [directories[0], duplicate], root)


@pytest.mark.parametrize("mutation", ["counter", "missing-artifact", "negative-index", "parsed-output"])
def test_native_capture_reconciliation_rejects_rebound_but_inconsistent_artifacts(native_batches, mutation):
    _root, _benchmark, directories = native_batches
    directory = directories[0]
    run = json.loads((directory / "run.json").read_text())
    if mutation == "counter":
        run["real_model_outputs_successful"] += 1
    elif mutation == "missing-artifact":
        del run["artifacts"]["raw-model.jsonl"]
    else:
        filename = "predictions.jsonl" if mutation == "negative-index" else "raw-model.jsonl"
        path = directory / filename
        values = [json.loads(line) for line in path.read_text().splitlines()]
        if mutation == "negative-index":
            values[0]["raw_capture_indices"] = [-1]
        else:
            values[0]["parsed_model_json"] = {"answer": "INJECTED_GOLD"}
        path.write_text("".join(json.dumps(item) + "\n" for item in values), encoding="utf-8")
        run["artifacts"][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(directory / "run.json", run)
    with pytest.raises(ValueError):
        load_native_run(directory)


def test_native_scorer_loads_dev_only_calibration_without_changing_captured_scores(native_batches):
    root, benchmark, directories = native_batches
    original = score(benchmark, directories, root)
    calibration = fit_report({"rows": [row for row in original["rows"] if row["split"] == "dev"],
                              "benchmark_sha256": original["benchmark_sha256"]})
    path = root / "calibration.json"
    write_json(path, calibration)
    report = score(benchmark, directories, root, calibration=path,
                   calibration_sha256=calibration["artifact_sha256"])
    assert report["calibration"]["holdout"]["count"] == 2
    assert set(report["risk_at_coverage"]) == {"0.8", "0.9"}
    assert report["calibration_population"]["holdout"]["positive"] == 1
    assert report["calibration_artifact_sha256"] == calibration["artifact_sha256"]
    assert [row["confidence_score"] for row in report["rows"]] == [row["confidence_score"] for row in original["rows"]]
    assert "calibration_dev_fit_mismatch" not in report["release_errors"]
    assert "native_calibration_identity_mismatch" in report["release_errors"]  # Captures were uncalibrated.
    with pytest.raises(ValueError, match="checksum"):
        score(benchmark, directories, root, calibration=path, calibration_sha256="stale")


def calibrated_evaluation_batches(native_batches):
    """Run the actual confidence pipeline with offline provider transport."""
    from campusai.rag.calibration import load_calibration_artifact
    root, benchmark, original = native_batches
    dev_report = score(benchmark, original[:1], root)
    fitted = fit_report(dev_report)
    artifact = root / "dev-fit.json"
    write_json(artifact, fitted)
    calibrator, digest = load_calibration_artifact(artifact, expected_sha256=fitted["artifact_sha256"])
    records = [json.loads(line) for line in benchmark.read_text(encoding="utf-8").splitlines()]
    directories = [original[0]]
    for index in (1, 2):
        directory = root / f"calibrated-{index}"
        llm = GeminiClient(api_key="unit-test-placeholder", max_retries=0, cache=None)
        service = CampusAIQueryService(FakeRetriever([evidence()]),
            GroundedAnswerGenerator(llm, calibrator=calibrator))
        def transport(*_args, **_kwargs):
            payload = valid_payload()
            payload["citations"] = [{"chunk_id": "c1", "page": 3, "quote": "MATH101 is required."}]
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
                    "modelVersion": "unit-transport-only"}
        metadata = json.loads((original[index] / "run.json").read_text(encoding="utf-8"))
        metadata.update(calibration_artifact_sha256=digest,
                        calibration_artifact_version=calibrator.version,
                        calibration_artifact_path=str(artifact))
        try:
            collect(service, records[index * 2:index * 2 + 2], llm,
                    max_provider_calls=2, output=directory, transport=transport, run_metadata=metadata)
        finally:
            service.close()
        directories.append(directory)
    return root, benchmark, directories, artifact, digest


def test_native_dev_fit_then_pinned_evaluation_keeps_original_predictions(native_batches):
    root, benchmark, directories, artifact, digest = calibrated_evaluation_batches(native_batches)
    before = {str(p): p.read_bytes() for d in directories for p in d.iterdir()}
    report = score(benchmark, directories, root, calibration=artifact, calibration_sha256=digest)
    assert report["generation"]["calibration_protocol"] == "dev-fit-then-pinned-evaluation-v1"
    assert "native_calibration_identity_mismatch" not in report["release_errors"]
    assert "native_batch_identity_mismatch" not in report["release_errors"]
    assert "calibration_dev_fit_mismatch" not in report["release_errors"]
    dev = next(r for r in report["rows"] if r["split"] == "dev")
    held = next(r for r in report["rows"] if r["split"] == "holdout")
    assert dev["confidence_policy_version"] == "grounding-v1"
    assert held["confidence_policy_version"] == "grounding-isotonic-v1"
    assert dev["confidence_score"] != held["confidence_score"]
    assert {str(p): p.read_bytes() for d in directories for p in d.iterdir()} == before
    assert report["release_status"] == "BLOCKED"  # Unit fixture has no real review/native evidence.


@pytest.mark.parametrize("mutation", ["wrong-heldout-calibrator", "uncalibrated-heldout",
    "dev-with-version", "removed-protocol", "report-split-laundering"])
def test_native_calibration_stage_exception_fails_closed(native_batches, mutation):
    root, benchmark, directories, artifact, digest = calibrated_evaluation_batches(native_batches)
    report = score(benchmark, directories, root, calibration=artifact, calibration_sha256=digest)
    if mutation == "removed-protocol":
        report["generation"].pop("calibration_protocol")
    else:
        index = 0 if mutation == "dev-with-version" else 2
        path = directories[index] / "run.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "wrong-heldout-calibrator":
            run["calibration_artifact_sha256"] = "wrong-calibrator"
        elif mutation == "dev-with-version":
            run["calibration_artifact_version"] = "grounding-isotonic-v1"
        else:
            run.update(calibration_artifact_sha256=None,
                       calibration_artifact_version=None, calibration_artifact_path=None)
        write_json(path, run)
        report["generation"]["native_runs"][index]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        if mutation == "report-split-laundering":
            for row in report["rows"]:
                if row["split"] == "holdout":
                    row["split"] = "dev"
    errors = validate(report, root=root)
    assert "native_calibration_identity_mismatch" in errors
    if mutation == "report-split-laundering":
        assert "benchmark_annotations_mismatch" in errors


def test_native_calibration_metadata_cannot_relabel_uncalibrated_predictions(native_batches):
    root, benchmark, directories, artifact, digest = calibrated_evaluation_batches(native_batches)
    original_holdout = native_batches[2][2]
    path = original_holdout / "run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    run.update(calibration_artifact_sha256=digest, calibration_artifact_version="grounding-isotonic-v1",
               calibration_artifact_path=str(artifact))
    write_json(path, run)
    report = score(benchmark, [*directories[:2], original_holdout], root,
                   calibration=artifact, calibration_sha256=digest)
    assert "native_calibrated_score_mismatch" in report["release_errors"]


@pytest.mark.parametrize("mutation", ["wrong-heldout-calibrator", "uncalibrated-heldout",
    "dev-with-version", "removed-protocol", "report-split-laundering"])
def test_native_calibration_stage_exception_fails_closed(native_batches, mutation):
    root, benchmark, directories, artifact, digest = calibrated_evaluation_batches(native_batches)
    report = score(benchmark, directories, root, calibration=artifact, calibration_sha256=digest)
    if mutation == "removed-protocol":
        report["generation"].pop("calibration_protocol")
    else:
        index = 0 if mutation == "dev-with-version" else 2
        path = directories[index] / "run.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "wrong-heldout-calibrator":
            run["calibration_artifact_sha256"] = "wrong-calibrator"
        elif mutation == "dev-with-version":
            run["calibration_artifact_version"] = "grounding-isotonic-v1"
        else:
            run.update(calibration_artifact_sha256=None,
                       calibration_artifact_version=None, calibration_artifact_path=None)
        write_json(path, run)
        report["generation"]["native_runs"][index]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        if mutation == "report-split-laundering":
            for row in report["rows"]:
                if row["split"] == "holdout":
                    row["split"] = "dev"
    errors = validate(report, root=root)
    assert "native_calibration_identity_mismatch" in errors
    if mutation == "report-split-laundering":
        assert "benchmark_annotations_mismatch" in errors


def test_native_calibration_rejects_false_dev_only_declaration(native_batches):
    from campusai.rag.calibration import calibration_payload_sha256
    root, benchmark, directories = native_batches
    original = score(benchmark, directories, root)
    calibration = fit_report({"rows": [row for row in original["rows"] if row["split"] == "dev"],
                              "benchmark_sha256": original["benchmark_sha256"]})
    calibration["artifact"]["values"] = [0.25]
    calibration["artifact_sha256"] = calibration_payload_sha256(calibration["artifact"])
    path = root / "bad-calibration.json"
    write_json(path, calibration)
    with pytest.raises(ValueError, match="differs from dev-only fit"):
        score(benchmark, directories, root, calibration=path)
    report = deepcopy(original)
    report.update(calibration_artifact_path=str(path), calibration_artifact_sha256=calibration["artifact_sha256"])
    assert "calibration_dev_fit_mismatch" in validate(report, root=root)


def test_native_validator_checks_captured_scores_and_failed_transport(native_batches):
    root, benchmark, directories = native_batches
    report = score(benchmark, directories, root)
    report["rows"][0]["confidence_score"] = 0.12
    assert "native_prediction_score_mismatch" in validate(report, root=root)
    runpath = directories[0] / "run.json"
    run = json.loads(runpath.read_text())
    prediction_path = directories[0] / "predictions.jsonl"
    predictions = [json.loads(line) for line in prediction_path.read_text().splitlines()]
    predictions[0]["provider_failure"] = {"category": "unit-provider-failure"}
    prediction_path.write_text("".join(json.dumps(item) + "\n" for item in predictions), encoding="utf-8")
    run["artifacts"][prediction_path.name] = hashlib.sha256(prediction_path.read_bytes()).hexdigest()
    write_json(runpath, run)
    scored = score(benchmark, directories, root)
    assert "native_provider_or_pipeline_failure" in scored["release_errors"]
    assert scored["metrics"]["records"] == 5
    assert scored["metrics"]["excluded_native_failures"] == 1
    assert scored["failed_prediction_ids"] == [predictions[0]["id"]]
    assert not scored["collection_complete"]


def test_collector_pins_calibration_before_any_provider_setup(native_batches):
    from evaluation.grounding.collect_native_predictions import pinned_calibrator
    root, benchmark, directories = native_batches
    original = score(benchmark, directories, root)
    calibration = fit_report({"rows": [row for row in original["rows"] if row["split"] == "dev"],
                              "benchmark_sha256": original["benchmark_sha256"]})
    path = root / "calibration.json"
    write_json(path, calibration)
    assert pinned_calibrator(None, None, benchmark) == (None, None)
    calibrator, digest = pinned_calibrator(path, calibration["artifact_sha256"], benchmark)
    assert digest == calibration["artifact_sha256"] and calibrator.predict(1.0) == 0.5
    for supplied_path, supplied_hash in ((path, None), (None, "stale"), (path, "stale")):
        with pytest.raises(ValueError):
            pinned_calibrator(supplied_path, supplied_hash, benchmark)
    calibration["fit_split"] = "holdout"
    write_json(path, calibration)
    with pytest.raises(ValueError, match="dev-only"):
        pinned_calibrator(path, digest, benchmark)


def test_package_does_not_skip_physical_native_bindings(tmp_path, monkeypatch):
    from evaluation.release import grounding_package as package
    report_path = tmp_path / "grounding.json"
    write_json(report_path, {"rows": []})
    write_json(tmp_path / "release_manifest.json", {"artifacts": {"grounding_report": {
        "path": report_path.name, "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest()}}})
    calls = []
    def validator(_report, *, root):
        calls.append(root)
        return ["unit-physical-binding-rejection"]
    monkeypatch.setattr(package, "validate_grounding_report", validator)
    result = package.validate_package(tmp_path, root=tmp_path, check_repository=False)
    assert calls == [tmp_path.resolve()]
    assert "grounding_unit-physical-binding-rejection" in result["errors"]


def test_native_validator_rejects_changed_physical_config_and_index(native_batches):
    root, benchmark, directories = native_batches
    config = root / "unit-config.yaml"
    config.write_text('llm:\n  model: unit-transport-only\n', encoding="utf-8")
    index = root / "index"
    index.mkdir()
    (index / "manifest.json").write_text('{}', encoding="utf-8")
    for directory in directories:
        path = directory / "run.json"
        run = json.loads(path.read_text())
        run.update(config_path=str(config), config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                   index_path=str(index), index_manifest_sha256=hashlib.sha256((index / "manifest.json").read_bytes()).hexdigest())
        write_json(path, run)
    report = score(benchmark, directories, root)
    config.write_text('llm:\n  model: changed-unit-model\n', encoding="utf-8")
    (index / "manifest.json").write_text('{"changed":true}', encoding="utf-8")
    errors = validate(report, root=root)
    assert "native_config_checksum_mismatch" in errors
    assert "native_index_checksum_mismatch" in errors
    # A bound arbitrary filename cannot stand in for the collector's run.json.
    other = root / "unrelated.json"
    other.write_text('{}', encoding="utf-8")
    report["generation"]["native_runs"][0] = {"path": str(other), "sha256": hashlib.sha256(other.read_bytes()).hexdigest()}
    assert "native_run_path_invalid_or_duplicate" in validate(report, root=root)
