import pytest

from evaluation.calibrate_phase5 import fit_report


def test_calibration_fits_dev_and_keeps_test_holdout_separate():
    rows = []
    for split in ("dev", "test", "holdout"):
        rows.extend([
            {"split": split, "confidence_score": 0.1, "answerable": False, "abstained": True},
            {"split": split, "confidence_score": 0.9, "answerable": True, "abstained": False},
        ])
    result = fit_report({"rows": rows})
    assert result["version"] == "phase5-isotonic-v1"
    assert result["metrics"]["holdout"]["count"] == 2


def test_calibration_requires_dev_split():
    with pytest.raises(ValueError, match="dev split"):
        fit_report({"rows": [{"split": "holdout", "confidence_score": 0.5}]})
