from argparse import Namespace
from datetime import datetime, timedelta, timezone

import pytest

from evaluation.reranker.audit_canary_staging import audit_staging
from evaluation.reranker.release_workflow import main, measurement_environment
from evaluation.common.release_artifacts import (assert_tuning_allowed, freeze_before_evaluation,
                                          read_json, write_json)
from campusai.retrieval.canary_rollout import CanaryController
from campusai.retrieval.cross_encoder_provider import ModelIdentity, snapshot_sha256
from tests.test_reranker_stage_gates import healthy_window, human_rows, observed_window
from evaluation.benchmarks.freeze_human_benchmark import validate_rows


def test_failed_heldout_attempt_freezes_policy_and_rejects_refit_or_changed_rerun(tmp_path):
    policy = tmp_path / "policy.json"
    write_json(policy, {"threshold": 1})
    lock = freeze_before_evaluation(tmp_path, {"calibration": policy})
    assert freeze_before_evaluation(tmp_path, {"calibration": policy}) == lock
    with pytest.raises(ValueError, match="already started"):
        assert_tuning_allowed(tmp_path)
    write_json(policy, {"threshold": 2})
    with pytest.raises(ValueError, match="changed"):
        freeze_before_evaluation(tmp_path, {"calibration": policy})
    assert read_json(tmp_path / "reranker_policy_freeze.json") == lock


def test_route_freeze_allows_score_fit_but_blocks_route_refit(tmp_path):
    route = tmp_path / "route.json"
    write_json(route, {"threshold": .5})
    freeze_before_evaluation(tmp_path, {"route": route}, route=True)
    assert_tuning_allowed(tmp_path)
    with pytest.raises(ValueError, match="already started"):
        assert_tuning_allowed(tmp_path, route=True)


@pytest.mark.parametrize("bad_window", [
    {"p99_ms": 2001}, {"p95_ms": 1001, "p99_ms": 1200},
    {"hard_query_coverage": .89}, {"easy_unnecessary_rerank_rate": .26},
])
def test_final_staging_step_cannot_hide_unhealthy_windows(bad_window):
    windows = []
    start = datetime(2026, 10, 2, tzinfo=timezone.utc)
    for step in (0, 1, 5, 10, 25):
        for _ in range(3):
            windows.append(observed_window({**healthy_window(step), "started_at": start.isoformat(),
                            "ended_at": (start + timedelta(minutes=5)).isoformat()}))
            start += timedelta(minutes=5)
    windows[-1].update(bad_window)
    with pytest.raises(ValueError, match="every healthy"):
        audit_staging({"environment": "staging", "environment_id": "fixture", "collector": "unit", "windows": windows}, {})


def test_staging_requires_three_windows_at_the_last_step_even_with_fifteen_total():
    windows, start = [], datetime(2026, 10, 2, tzinfo=timezone.utc)
    for step, count in ((0, 5), (1, 3), (5, 3), (10, 3), (25, 1)):
        for _ in range(count):
            windows.append(observed_window({**healthy_window(step), "started_at": start.isoformat(),
                            "ended_at": (start + timedelta(minutes=5)).isoformat()}))
            start += timedelta(minutes=5)
    with pytest.raises(ValueError, match="including 25"):
        audit_staging({"environment": "staging", "environment_id": "fixture", "collector": "unit", "windows": windows}, {})


def test_p99_latency_triggers_real_controller_rollback():
    called = []
    controller = CanaryController(rollback=called.append)
    bad = {**healthy_window(), "p99_ms": 2001}
    assert controller.observe(bad) is None
    assert controller.observe(bad) is None
    assert controller.observe(bad) == "latency_budget_three_windows"
    assert called == ["latency_budget_three_windows"]
    assert controller.traffic_percent == 0


def test_measurement_environment_binds_snapshot_and_overrides_ambient_production(tmp_path, monkeypatch):
    snapshot = tmp_path / ("a" * 40)
    snapshot.mkdir()
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", snapshot.name, snapshot_sha256(snapshot), snapshot.name)
    results = tmp_path / "results"
    write_json(results / "model_snapshot_smoke.json", {"model_identity": identity.to_dict()})
    args = Namespace(model_dir=snapshot, results_dir=results, device="cpu", model_name=identity.model_name)
    monkeypatch.setenv("RERANKER_DEPLOYMENT", "production")
    monkeypatch.setenv("RERANKER_TIMEOUT_MS", "60000")
    env = measurement_environment(args)
    assert env["RERANKER_DEPLOYMENT"] == "experimental"
    assert env["RERANKER_TIMEOUT_MS"] == "1000"
    assert env["RERANKER_MODEL_SHA256"] == identity.model_sha256
    (snapshot / "config.json").write_text('{"changed": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        measurement_environment(args)


def test_stage_failure_stops_before_any_measurement_process(tmp_path, monkeypatch):
    from evaluation.reranker import release_workflow
    calls = []
    original_run = release_workflow.subprocess.run
    def observe_run(command, **kwargs):
        if command[0] == "git":
            return original_run(command, **kwargs)
        calls.append(command)
        raise AssertionError("measurement must not run before prerequisite gates pass")
    monkeypatch.setattr(release_workflow.subprocess, "run", observe_run)
    assert main(["candidate", "--results-dir", str(tmp_path / "results"),
                 "--index-dir", str(tmp_path / "index"), "--benchmark-dir", str(tmp_path / "benchmark")]) == 1
    assert calls == []


@pytest.mark.parametrize("stage,extra", [("model", []), ("performance", ["--model-dir", "model"]),
                                        ("staging", []), ("staging-collect", []), ("release", [])])
def test_missing_deployment_inputs_rejected(stage, extra):
    with pytest.raises(SystemExit) as error:
        main([stage, *extra])
    assert error.value.code == 2


def test_human_review_requires_scope_expected_behavior_and_no_regression_paraphrase():
    rows = human_rows()
    rows[0]["review_checks"].pop("expected_behavior")
    rows[1]["doc_ids"] = ["outside"]
    regression = [{"qid": "r1", "question": rows[2]["question"] + " extra"}]
    report = validate_rows(rows, {("doc", "c0"): {"page": 1}}, regression)
    assert "row_1:incomplete_review_checks" in report["errors"]
    assert "row_2:invalid_doc_scope" in report["errors"]
    assert "row_2:evidence_scope_mismatch" in report["errors"]
    assert any(e.startswith("regression_paraphrase_leakage:r1:") for e in report["errors"])


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e309"])
def test_release_json_rejects_non_finite_constants(tmp_path, value):
    path = tmp_path / "report.json"
    path.write_text('{"status": "pass", "metric": ' + value + '}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        read_json(path)
