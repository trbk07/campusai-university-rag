import pytest

from campusai.retrieval.calibration import CalibrationError, select_threshold


def test_calibrator_selects_threshold_meeting_recall_and_false_positive_rate():
    result = select_threshold([0.95, 0.9, 0.2, 0.1], [True, True, False, False], min_recall=1.0, max_false_positive_rate=0.0)
    assert result.threshold == 0.9
    assert result.recall == 1.0
    assert result.false_positive_rate == 0.0


def test_calibrator_rejects_impossible_constraints():
    with pytest.raises(CalibrationError):
        select_threshold([0.5, 0.6], [True, False], min_recall=1.0, max_false_positive_rate=0.0)
