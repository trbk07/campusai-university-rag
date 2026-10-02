import pytest
import json

from evaluation.grounding.calibrate_confidence import fit_report, risk_at_coverage
from evaluation.grounding.calibrate_confidence import _score
from campusai.rag.calibration import load_calibration_artifact


def test_calibration_fits_dev_and_keeps_test_holdout_separate():
    rows = []
    for split in ("dev", "test", "holdout"):
        rows.extend([
            {"split": split, "confidence_score": 0.1, "answerable": False, "abstained": True},
            {"split": split, "confidence_score": 0.9, "answerable": True, "abstained": False},
        ])
    result = fit_report({"rows": rows})
    assert result["version"] == "grounding-isotonic-v1"
    assert result["metrics"]["holdout"]["count"] == 2
    assert len(result["artifact_sha256"]) == 64


def test_calibration_requires_dev_split():
    with pytest.raises(ValueError, match="dev split"):
        fit_report({"rows": [{"split": "holdout", "confidence_score": 0.5}]})


def test_calibration_rejects_degenerate_holdout():
    rows = []
    for split in ("dev", "test"):
        rows.extend([
            {"split": split, "confidence_score": 0.1, "answerable": False, "abstained": True},
            {"split": split, "confidence_score": 0.9, "answerable": True, "abstained": False},
        ])
    rows.extend([
        {"split": "holdout", "confidence_score": 0.1, "answerable": False, "abstained": True},
        {"split": "holdout", "confidence_score": 0.2, "answerable": False, "abstained": True},
    ])
    with pytest.raises(ValueError, match="holdout split"):
        fit_report({"rows": rows})


def test_abstention_without_score_calibrates_as_zero_confidence():
    assert _score({"abstained": True, "confidence": "low"}) == 0.0


def test_calibration_rejects_non_monotonic_or_non_finite_artifact():
    from campusai.rag.calibration import IsotonicCalibrator
    with pytest.raises(ValueError, match="invalid calibration artifact"):
        IsotonicCalibrator.from_dict({
            "version": "grounding-isotonic-v1",
            "thresholds": [0.2, float("nan")],
            "values": [0.5, 0.4],
        })


def test_calibration_artifact_is_verified_before_runtime_use(tmp_path):
    result = fit_report({"rows": [
        {"split": "dev", "confidence_score": 0.1, "answerable": False, "abstained": True},
        {"split": "dev", "confidence_score": 0.9, "answerable": True, "abstained": False},
    ]})
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    calibrator, digest = load_calibration_artifact(path, expected_sha256=result["artifact_sha256"])
    assert calibrator.version == "grounding-isotonic-v1"
    assert digest == result["artifact_sha256"]
    result["artifact"]["values"][0] = 1.0
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_calibration_artifact(path)


def test_risk_at_coverage_isolated_to_holdout_and_tie_deterministic():
    from campusai.rag.calibration import IsotonicCalibrator

    calibrator = IsotonicCalibrator.fit([0.1, 0.9], [False, True])
    rows = [
        {"id": "dev-bad", "split": "dev", "confidence_score": 0.9,
         "answerable": False, "abstained": False},
        {"id": "holdout-a", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-b", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-c", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-d", "split": "holdout", "confidence_score": 0.9,
         "answerable": True, "abstained": False},
        {"id": "holdout-e", "split": "holdout", "confidence_score": 0.1,
         "answerable": False, "abstained": True},
    ]
    assert risk_at_coverage(rows, calibrator, 0.8) == 0.0
