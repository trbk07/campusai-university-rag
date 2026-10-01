from argparse import Namespace
import json

from evaluation.validate_reranker_release import validate


def test_phase7_release_gate_fails_closed_when_evidence_is_missing(tmp_path):
    names = ("baseline", "candidate", "route", "smoke", "calibration", "quality",
             "performance", "grounding", "security", "failure_matrix", "rollback", "staging")
    args = Namespace(**{name: tmp_path / f"{name}.json" for name in names},
                     deployment_ram_bytes=None)
    report = validate(args)
    assert report["status"] == "conditional"
    assert report["score"] is None
    assert "missing_calibration" in report["errors"]
    assert "hard_route_gate" in report["errors"]
    assert "deployment_ram_headroom_gate" in report["errors"]


def test_phase7_release_gate_fails_closed_on_malformed_nested_metrics(tmp_path):
    names = ("baseline", "candidate", "route", "smoke", "calibration", "quality",
             "performance", "grounding", "security", "failure_matrix", "rollback", "staging")
    args = Namespace(**{name: tmp_path / f"{name}.json" for name in names},
                     deployment_ram_bytes=8 * 1024**3)
    for name in names:
        (tmp_path / f"{name}.json").write_text(json.dumps({"status": "pass"}), encoding="utf-8")
    args.candidate.write_text(json.dumps({"status": "pass", "splits": {"test": None}}),
                              encoding="utf-8")
    args.quality.write_text(json.dumps({"status": "pass", "test": None,
                                        "paired_statistics": {"bootstrap_resamples": "10000",
                                                              "mrr_ci95": []}}), encoding="utf-8")
    args.performance.write_text(json.dumps({"status": "pass", "peak_rss_bytes": "NaN"}),
                                encoding="utf-8")
    report = validate(args)
    assert report["status"] == "conditional"
    assert "statistical_significance_gate" in report["errors"]
    assert "candidate_test_gate" in report["errors"]
    assert "deployment_ram_headroom_gate" in report["errors"]
