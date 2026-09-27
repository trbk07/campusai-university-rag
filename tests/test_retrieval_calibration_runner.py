from evaluation.calibrate_retrieval import select_threshold


def test_calibration_runner_uses_shared_calibrator():
    result = select_threshold([0.9, 0.8, 0.1, 0.0], [True, True, False, False], min_recall=1.0, max_false_positive_rate=0.0)
    assert result.threshold == 0.8
