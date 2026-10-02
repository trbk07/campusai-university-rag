from argparse import Namespace
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random

import pytest

from evaluation.check_reranker_faults import run_fault_checks, fixture_retriever
from evaluation.reranker_release_gates import default_args, validate, FAILURES, PROVIDER_CASES
from evaluation.freeze_human_benchmark import validate_rows
from evaluation.measure_reranker_capacity import summarize_samples
from evaluation.compare_retrieval_quality import compare_split, paired_bootstrap, quality_errors
from evaluation.audit_canary_staging import audit_staging, ROLLBACK_REASONS
from evaluation.canary_telemetry import summarize_window
from campusai.retrieval.canary_rollout import CanaryController, rollback_retriever
from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator


def human_rows():
    rng = random.Random(41)
    rows = []
    for i in range(150):
        # Artificial unit-test records; never written to the release benchmark.
        tokens = [f"word{rng.randrange(1000000)}" for _ in range(8)]
        rows.append({"qid": f"hn-{i}", "question": " ".join(tokens), "split": ("dev", "test", "holdout")[i % 3],
                     "paraphrase_group": f"group-{i}", "answerable": i < 120,
                     "difficulty": "hard" if i % 6 < 3 else "easy",
                     "doc_ids": ["doc"], "filters": {},
                     "gold_evidence": [{"doc_id": "doc", "chunk_id": "c0", "page": 1}] if i < 120 else [],
                     "tags": ["natural"] + (["exact_code"] if i < 18 else []) + (["ambiguous"] if i >= 135 else []),
                     "author_type": "human", "author": "annotator", "reviewer": "reviewer",
                     "review_status": "approved", "source_url": "https://example.org/faq",
                     "source_retrieved_at": "2026-09-01T12:00:00+07:00", "evidence_source": "frozen_pdf",
                     "review_checks": {key: True for key in ("natural", "answerability", "evidence_sufficient", "corpus_temporal_scope", "difficulty", "no_paraphrase_leakage", "expected_behavior")}})
    return rows


def test_human_review_freeze_accepts_only_complete_independent_frozen_evidence():
    rows = human_rows()
    evidence = {("doc", "c0"): {"page": 1}}
    assert validate_rows(rows, evidence)["status"] == "pass"
    rows[0]["reviewer"] = " ANNOTATOR "
    rows[1]["gold_evidence"][0]["page"] = 999
    rows[2]["paraphrase_group"] = rows[0]["paraphrase_group"]
    rows[3]["question"] = rows[0]["question"]
    report = validate_rows(rows, evidence)
    assert report["status"] == "conditional"
    assert any("independent_human_review" in e for e in report["errors"])
    assert any("evidence_provenance" in e for e in report["errors"])
    assert any("paraphrase_group_leakage" in e for e in report["errors"])
    assert any("duplicate_or_empty_question" in e for e in report["errors"])


def test_human_review_blocks_regression_leakage_and_live_evidence():
    rows = human_rows()
    rows[0]["evidence_source"] = "live_website"
    result = validate_rows(rows, {("doc", "c0"): {"page": 1}}, [{"qid": "regression", "question": rows[2]["question"]}])
    assert "regression_query_leakage:regression" in result["errors"]
    assert any("frozen_pdf" in error for error in result["errors"])


def test_paired_statistics_distinguish_improvement_tie_and_negative_regression():
    evidence = {("doc", name): {"doc_id": "doc", "chunk_id": name, "page": i+1, "content": name}
                for i, name in enumerate(("gold", "wrong"))}
    gold, wrong = list(evidence.values())
    rows = [{"qid": f"q{i}", "question": "query", "answerable": True, "gold_evidence": [gold]} for i in range(8)]
    rows += [{"qid": "negative", "question": "negative", "answerable": False, "gold_evidence": []}]
    before = {r["qid"]: [wrong, gold] if r["answerable"] else [] for r in rows}
    after = {r["qid"]: [gold, wrong] if r["answerable"] else [] for r in rows}
    test = compare_split(rows, before, after, evidence, ["doc"])
    holdout = compare_split(rows, after, after, evidence, ["doc"])
    report = {"test": test, "holdout": holdout, "human_test": test, "human_holdout": holdout}
    assert quality_errors(report) == []  # Holdout only requires no regression.
    assert test["paired_statistics"]["mrr"]["ci95"] == [.5, .5]
    assert test["paired_statistics"]["mrr"]["win_tie_loss"] == {"win": 8, "tie": 0, "loss": 0}
    assert paired_bootstrap([0.0] * 8)["significant"] is False
    after["negative"] = [gold]
    bad = compare_split(rows, before, after, evidence, ["doc"])
    assert "quality_test_gate" in quality_errors({**report, "test": bad})
    with pytest.raises(ValueError, match="exactly"):
        compare_split(rows, before, {"wrong-qid": []}, evidence, ["doc"])


def healthy_window(percent=0):
    return {"traffic_percent": percent, "requests": 100, "p50_ms": 100, "p95_ms": 500, "p99_ms": 900,
            "timeout_rate": 0, "negative_fpr": 0, "error_rate": 0, "baseline_error_rate": 0,
            "fallback_rate": 0, "selection_rate": .1, "easy_unnecessary_rerank_rate": .1,
            "hard_query_coverage": .95, "peak_rss_bytes": 1000, "ram_limit_bytes": 10000,
            "queue_depth": 0, "provenance_errors": 0, "scope_errors": 0, "citation_errors": 0}


def observed_window(window):
    """Artificial observations used only to test replay/tamper detection."""
    window["routing_metrics_scope"] = "frozen_policy_shadow_on_all_requests"
    window["request_observations"] = [
        {"request_id": f"fixture-{i}", "started_at": window["started_at"], "ended_at": window["ended_at"],
         "answerable": i < 40, "difficulty": "easy" if i < 20 else "hard" if i < 40 else "medium",
         "doc_ids": ["doc"], "filters": {}, "output": [{"doc_id": "doc", "chunk_id": "c0", "page": 1,
              "content": "tuition policy fees student semester 0 MAI101", "metadata": {"page_range": [1, 1], "language": "en"}}] if i < 40 else [],
         "route_selected": i < 2 or 20 <= i < 39, "rerank_selected": i < 10,
         "latency_ms": 100 if i < 50 else 500 if i < 95 else 900,
         "error": False, "baseline_error": False, "has_results": i < 40, "fallback": False, "timeout": False,
         "queue_depth": 0, "provenance_errors": 0, "scope_errors": 0, "citation_errors": 0, "peak_rss_bytes": 1000}
        for i in range(100)]
    return window


def fault_exercises(changes):
    exercises = []
    for name in changes:
        windows = []
        for number in range(3 if name.startswith("latency") else 1):
            start = datetime(2026, 9, 3, tzinfo=timezone.utc) + timedelta(minutes=5 * number)
            window = observed_window({**healthy_window(25), "started_at": start.isoformat(),
                                      "ended_at": (start + timedelta(minutes=5)).isoformat()})
            samples = window["request_observations"]
            if name == "provenance_error":
                samples[0]["output"][0]["content"] += "corrupted"
                samples[0].update(provenance_errors=1, citation_errors=1)
            elif name == "scope_leakage":
                samples[0]["output"][0]["doc_id"] = "other"
                samples[0]["scope_errors"] = 1
            elif name == "citation_error":
                samples[0]["output"][0]["metadata"]["page_range"] = [999, 999]
                samples[0]["citation_errors"] = 1
            elif name == "timeout_budget":
                for sample in samples[:2]: sample["timeout"] = True
            elif name == "negative_fpr_budget":
                samples[-1]["output"] = deepcopy(samples[0]["output"])
                samples[-1]["has_results"] = True
            elif name == "error_rate_regression":
                samples[0]["error"] = True
            elif name == "memory_budget":
                for sample in samples: sample["peak_rss_bytes"] = 7600
            elif name.startswith("latency"):
                for sample in samples: sample["latency_ms"] = 1100
            windows.append(summarize_window(samples, traffic_percent=25, ram_limit_bytes=10000,
                                             started_at=window["started_at"], ended_at=window["ended_at"]))
        exercises.append({"expected_reason": name, "observed_reason": name, "windows": windows,
                          "service_phase7_enabled_after": False, "provider_closed_after": True,
                          "provider_calls_before_followup": 1, "provider_calls_after_followup": 1,
                          "new_reranker_calls_after": 0, "injected_service_calls": 100 * len(windows),
                          "followup_probes": [{"output": [], "baseline": []} for _ in range(3)]})
    return {"exercises": exercises}


def test_canary_deterministic_cohort_sequential_promotion_and_rollback():
    reasons = []
    controller = CanaryController(rollback=reasons.append)
    assert not controller.admits("request-1")
    with pytest.raises(ValueError, match="three healthy"):
        controller.promote()
    for step in (0, 1, 5, 10):
        for _ in range(3):
            assert controller.observe(healthy_window(step)) is None
        assert controller.promote() in (1, 5, 10, 25)
    admissions = [controller.admits(str(i)) for i in range(500)]
    assert admissions == [controller.admits(str(i)) for i in range(500)]
    assert 90 < sum(admissions) < 160
    bad = {**healthy_window(25), "p95_ms": 1001, "p99_ms": 1200}
    assert controller.observe(bad) is None
    assert controller.observe(bad) is None
    assert controller.observe(bad) == "latency_budget_three_windows"
    assert reasons == ["latency_budget_three_windows"]
    assert controller.traffic_percent == 0 and not controller.admits("request-1")
    with pytest.raises(ValueError):
        controller.promote()


def test_canary_service_cannot_bypass_cohort_and_rolls_back_to_phase6(tmp_path):
    retriever, provider, *_ = fixture_retriever(tmp_path)
    controller = CanaryController()
    service = CampusAIQueryService(retriever, GroundedAnswerGenerator(), canary=controller)
    try:
        service.retrieve("tuition fees", ["doc"], mode="phase7", request_id="internal")
        assert provider.calls == 0
        assert service.observe_canary_window({**healthy_window(), "scope_errors": 1}) == "scope_leakage"
        assert not retriever.phase7_enabled
        service.retrieve("tuition fees", ["doc"])
        assert provider.calls == 0 and retriever.last_trace.route == "hybrid_rrf"
    finally:
        service.close()


def test_runtime_failure_matrix_checks_real_fallback_and_provider_guards(tmp_path):
    report = run_fault_checks(tmp_path)
    assert report["status"] == "pass"
    assert FAILURES | PROVIDER_CASES <= report["checks"].keys()
    assert all(report["checks"].values())


def test_performance_uses_finite_samples_and_counts_fallbacks():
    samples = [{"hard": True, "error": False, "latency_ms": n, "reason": None, "fallback": False}
               for n in range(1, 101)]
    samples[0].update(reason="reranker_timeout", fallback=True)
    report = summarize_samples(samples)
    assert report["hard_p95_ms"] == 95
    assert report["hard_p99_ms"] == 99
    assert report["timeout_rate"] == report["timeout_fallback_rate"] == .01
    with pytest.raises(ValueError):
        summarize_samples([])
    samples[2]["latency_ms"] = float("nan")
    with pytest.raises(ValueError):
        summarize_samples(samples)


def test_staging_requires_real_times_all_steps_and_all_rollback_exercises():
    started = datetime(2026, 9, 1, tzinfo=timezone.utc)
    windows = []
    for percent in (0, 1, 5, 10, 25):
        for _ in range(3):
            window = healthy_window(percent)
            window.update(started_at=started.isoformat(), ended_at=(started + timedelta(minutes=5)).isoformat())
            started += timedelta(minutes=5)
            windows.append(observed_window(window))
    changes = {"provenance_error": {"provenance_errors": 1}, "scope_leakage": {"scope_errors": 1},
               "citation_error": {"citation_errors": 1}, "timeout_budget": {"timeout_rate": .02},
               "negative_fpr_budget": {"negative_fpr": .02}, "error_rate_regression": {"error_rate": .01},
               "memory_budget": {"peak_rss_bytes": 7600}, "latency_budget_three_windows": {"p95_ms": 1100, "p99_ms": 1200}}
    faults = fault_exercises(changes)
    data = {"environment": "staging", "environment_id": "test-fixture", "collector": "test", "windows": windows}
    assert audit_staging(data, faults)["status"] == "pass"
    bad = deepcopy(data)
    bad["windows"][0]["traffic_percent"] = 25
    with pytest.raises(ValueError):
        audit_staging(bad, faults)
    faults["exercises"].pop()
    with pytest.raises(ValueError, match="incomplete"):
        audit_staging(data, faults)


def test_stage_order_cannot_be_bypassed_by_scalar_pass_placeholders(tmp_path):
    args = default_args(tmp_path)
    for path in (value for value in vars(args).values() if isinstance(value, Path) and value.parent == tmp_path):
        path.write_text(json.dumps({"status": "pass", "errors": []}), encoding="utf-8")
    report = validate(args)
    assert report["status"] == "conditional" and report["score"] is None
    assert report["gates"]["M0"]["status"] == "FAIL"
    assert all(report["gates"][f"M{i}"]["status"] == "BLOCKED" for i in range(1, 13))
    assert "human_dataset_content_gate" in report["errors"] or "human_dataset_input_gate" in report["errors"]
    assert "failure_matrix_gate" in report["errors"]


def test_validator_can_pass_complete_bound_evidence_and_detect_tampering(tmp_path, monkeypatch):
    from evaluation import reranker_release_gates as gates
    from evaluation.release_artifacts import sha256, write_json, freeze_before_evaluation
    from evaluation.freeze_human_benchmark import frozen_evidence
    from evaluation.calibrate_reranker_scores import _quality
    from evaluation.calibrate_hard_query_route import route_metrics
    from evaluation.evaluate_reranker_security import CATEGORIES
    retriever, provider, *_ = fixture_retriever(tmp_path / "fixture")
    results, benchmark = tmp_path / "results", tmp_path / "benchmark"
    results.mkdir()
    benchmark.mkdir()
    corpus = tmp_path / "data/corpus/university/manifest.json"
    write_json(corpus, {"fixture": True})
    monkeypatch.setattr(gates, "ROOT", tmp_path)
    monkeypatch.setattr(gates, "source_identity", lambda _: {"commit": "fixture", "source_sha256": "a"*64, "runtime_sha256": "f"*64})
    monkeypatch.setattr(gates.subprocess, "check_output", lambda *a, **k: "")
    args = default_args(results)
    args.index_dir, args.benchmark_dir = retriever.index_root, benchmark
    write_json(args.phase6_calibration, {"fixture": True})
    rows = human_rows()
    def jsonl(path, records):
        path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    jsonl(benchmark / "human_retrieval.jsonl", rows)
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if row["split"] == split]
        jsonl(benchmark / f"human_retrieval_{split}.jsonl", subset)
        jsonl(benchmark / f"phase6_retrieval_{split}.jsonl", [{**row, "question": " ".join("regression" + word for word in row["question"].split())} for row in subset])
    from dataclasses import replace
    identity = replace(provider.model_identity, model_revision="e"*40, tokenizer_revision="e"*40)
    bindings = {"source_sha256": "a"*64, "runtime_sha256": "f"*64, "index_sha256": sha256(args.index_dir / "manifest.json"),
                "phase6_calibration_sha256": sha256(args.phase6_calibration), "model_identity_sha256": identity.fingerprint}
    def save(name, data):
        write_json(getattr(args, name), {"status": "pass", **bindings, **data})
    write_json(results / "phase6_holdout_report.json", {"fixture": True})
    write_json(results / "phase6_performance_report.json", {"fixture": True})
    base_metrics = {f"{split}_{kind}": ({"answerable_recall": {"5": 1}} if kind == "quality" else {"false_positive_rate": 0})
                    for split in ("test", "holdout") for kind in ("quality", "negative")}
    save("baseline_report", {"historical": base_metrics, "rerun_a": base_metrics, "rerun_b": base_metrics})
    save("baseline", {"working_tree_clean": True, "calibration_sha256": bindings["phase6_calibration_sha256"],
         "corpus_sha256": sha256(corpus), "dense_model": {"name": "fixture", "revision": "rev", "sha256": "b"*64},
         "reference_report_sha256": sha256(results / "phase6_holdout_report.json"),
         "rerun_report_sha256": ["c"*64, "d"*64], "performance_report_sha256": sha256(results / "phase6_performance_report.json"),
         "benchmark_sha256": {s: sha256(benchmark / f"phase6_retrieval_{s}.jsonl") for s in ("test", "holdout")}})
    evidence = frozen_evidence(args.index_dir)
    review = validate_rows(rows, evidence)
    save("human_review", {**review, "dataset_sha256": sha256(benchmark / "human_retrieval.jsonl")})
    split_hashes = {s: sha256(benchmark / f"human_retrieval_{s}.jsonl") for s in ("dev", "test", "holdout")}
    save("human_manifest", {"frozen": True, "dataset_sha256": sha256(benchmark / "human_retrieval.jsonl"),
                           "review_sha256": sha256(args.human_review), "split_sha256": split_hashes})
    candidate = {}
    from evaluation.evaluate_candidate_coverage import audit_outputs
    from campusai.retrieval.hybrid import RetrievalResult
    gold_item = evidence[("doc", "c0")]
    raw_candidate = RetrievalResult("c0", "doc", 1, gold_item["content"], "text", 1,
                                    "hybrid_rrf", {"page_range": [1, 1]}).to_dict()
    for split in ("test", "holdout", "human_dev", "human_test", "human_holdout"):
        digest = split_hashes[split.removeprefix("human_")] if split.startswith("human_") else sha256(benchmark / f"phase6_retrieval_{split}.jsonl")
        source = benchmark / (f"human_retrieval_{split.removeprefix('human_')}.jsonl" if split.startswith("human_") else f"phase6_retrieval_{split}.jsonl")
        records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
        observed = {row["qid"]: [raw_candidate] if row["answerable"] else [] for row in records}
        candidate[split] = {"benchmark_sha256": digest, "caps": {"40": audit_outputs(records, observed, ["doc"], 40, evidence)}}
    save("candidate", {"splits": candidate})
    save("smoke", {"model_identity": identity.to_dict(), "deterministic": True, "max_score_delta": 0,
                   "model_files_sha256": {"config.json": sha256(tmp_path / "fixture/rev/config.json")}})
    fault_report = run_fault_checks(tmp_path / "faults")
    save("provider_contract", fault_report)
    conf = {}
    for split in ("dev", "test", "holdout"):
        samples = [{"qid": row["qid"], "difficulty": row["difficulty"], "confidence": .1 if row["difficulty"] == "hard" else .9,
                    "margin": .1, "agreement": 1, "constraints": 0, "query_length": len(row["question"].split()),
                    "distinct_documents": 1, "concentration": .5}
                   for row in rows if row["split"] == split and row["answerable"]]
        conf[split] = {**route_metrics(samples, .5, 0), "samples": samples,
                       "bypass": {"exact_or_abstained": 50 - len(samples), "single_candidate": 0},
                       "benchmark_sha256": split_hashes[split],
                       "exact_code_rerank_rate": 0, "abstention_rerank_rate": 0, "deterministic": True}
    from evaluation.calibrate_route_probabilities import fit_route_probabilities
    route_model, route_diagnostics, route_feasible = fit_route_probabilities(
        conf["dev"]["samples"], [row for row in rows if row["split"] == "dev"])
    assert route_feasible
    for split in conf:
        conf[split].update(route_metrics(conf[split]["samples"], .5, 0, route_model=route_model))
    save("route", {"calibration_split": "dev", "test_used": False, "holdout_used": False, "feature_leakage_review": "pass",
                   "feature_allowlist": ["confidence", "margin", "agreement", "constraints", "query_length",
                                         "distinct_documents", "concentration"],
                   "route_model": route_model, "route_diagnostics": route_diagnostics,
                   "training_split_sha256": split_hashes["dev"],
                   "routing_metrics": route_metrics(conf["dev"]["samples"], .5, 0, route_model=route_model),
                   "easy_confidence_threshold": .5, "easy_margin_threshold": 0,
                   "samples": conf["dev"]["samples"]})
    save("route_confusion", {"splits": conf, "route_calibration_sha256": sha256(args.route)})
    freeze_before_evaluation(results, {name: getattr(args, name) for name in ("route", "smoke", "human_manifest")}, route=True)
    gold, wrong = evidence[("doc", "c0")], evidence[("doc", "c1")]
    subset = [row for row in rows if row["split"] == "dev"]
    before = {row["qid"]: [wrong, gold] if row["answerable"] else [] for row in subset}
    proposals = {}
    for index, row in enumerate(subset):
        negative = not row["answerable"]
        partial = index < 5
        scores = [-5, -6] if negative else [-2, -3] if partial else [2, 1]
        proposals[row["qid"]] = {"top_score": scores[0], "margin": 1,
                                  "results": [] if negative else [wrong] if partial else [gold, wrong],
                                  "evidence_inputs": {"ranked_candidates": [wrong, gold], "scores": scores}}
    from evaluation.calibrate_evidence_probabilities import calibrate_probabilities
    probability_policy, probability_comparison = calibrate_probabilities(subset, before, proposals)
    save("calibration", {"calibration_split": "dev", "test_used": False, "holdout_used": False, "candidate_cap": 40,
                         "rerank_candidate_cap": 10, "recall": probability_comparison["selected"]["answerable_recall_at_5"],
                         "false_positive_rate": probability_comparison["selected"]["negative_fpr"],
                         "route_calibration_sha256": sha256(args.route), "training_split_sha256": split_hashes["dev"],
                         "threshold": 0, "margin_threshold": 0, "low_score_action": "phase6",
                         "evidence_policy": "probability", "evidence_model": probability_policy["evidence_model"],
                         "route_model": route_model,
                         "fallback_rate": 0, "timeout_rate": 0, "invalid_score_rate": 0,
                         "rerank_latency_ms": {"p95": 50}, "eligible_requests": len(proposals), "comparison": probability_comparison,
                         "calibration_observations": {"baseline": before, "proposals": proposals}})
    trials = []
    for cap in (8, 10, 12, 16, 20):
        path = results / f"cap-{cap}.json"
        trial = json.loads(args.calibration.read_text(encoding="utf-8"))
        trial.update(rerank_candidate_cap=cap, rerank_latency_ms={"p95": 50 if cap == 10 else 100})
        write_json(path, trial)
        trials.append({"rerank_cap": cap, "artifact": path.name, "artifact_sha256": sha256(path),
                       "status": "pass", "recall": 1, "negative_fpr": 0, "p95_ms": trial["rerank_latency_ms"]["p95"],
                       "mrr": trial["comparison"]["selected"]["mrr"], "eligible_requests": len(proposals), "timeout_rate": 0})
    save("sensitivity", {"calibration_split": "dev", "test_used": False, "holdout_used": False, "trials": trials,
                         "selected_cap": 10, "p95_budget_ms": 1000})
    bindings["calibration_sha256"] = sha256(args.calibration)
    bindings.update(route_calibration_sha256=sha256(args.route), training_split_sha256=split_hashes["dev"],
                    human_benchmark_sha256=sha256(benchmark / "human_retrieval.jsonl"))
    freeze_before_evaluation(results, {name: getattr(args, name) for name in ("route", "smoke", "human_manifest", "calibration", "sensitivity")})
    quality, hashes = {}, {}
    for split in ("test", "holdout", "human_test", "human_holdout"):
        path = benchmark / (f"human_retrieval_{split.removeprefix('human_')}.jsonl" if split.startswith("human_") else f"phase6_retrieval_{split}.jsonl")
        records = [json.loads(line) for line in path.read_text().splitlines()]
        before = {r["qid"]: [wrong, gold] if r["answerable"] else [] for r in records}
        after = {r["qid"]: [gold, wrong] if r["answerable"] else [] for r in records}
        quality[split] = compare_split(records, before, after, evidence, ["doc"])
        hashes[split] = sha256(path)
    save("quality", {**quality, "benchmark_sha256": hashes})
    (results / "retrieval_quality_comparison.md").write_text("# Unit fixture\n", encoding="utf-8")
    (results / "retrieval_ranking_regressions.jsonl").write_text("", encoding="utf-8")
    samples = [{"hard": True, "error": False, "latency_ms": 100, "rerank_selected": True} for _ in range(100)]
    summary = summarize_samples(samples)
    limits = {"timeout_ms": 1000, "queue_limit": 19, "failure_limit": 3, "score_cache_size": 0}
    save("performance", {"resource_limits": limits, "samples": samples, "summary": summary, "peak_rss_bytes": 100,
                         "cold_start_ms": 1, "warmup_ms": 1, "cpu_utilization_percent": 5})
    save("capacity", {"resource_limits": limits, "release_rerank_cap": 10, "deployment_device": "cpu", "profiles": [{"resource_limits": limits, "rerank_cap": cap, "concurrency": n, "samples": samples, "summary": summary}
                                    for cap, n in ((8, 1), (10, 1), (20, 1), (10, 5), (10, 10), (10, 20))], "queue_overflow_request_failures": 0})
    save("resource_budget", {"deployment_ram_bytes": 10000})
    # Synthetic gate fixture: exercises recomputation and tamper detection.
    # These rows never become release measurements or a real LLM claim.
    from evaluation.measure_phase7_http import cohort, summarize_http_samples, workload
    test_rows = [row for row in rows if row["split"] == "test"]
    http_profiles = []
    for concurrency in (1, 5, 10, 20):
        http_samples = []
        for i in range(100):
            row = workload(test_rows, 100)[i]
            positive = row["answerable"]
            started = concurrency * 100 + i * .1
            http_samples.append({"qid": row["qid"], "question_sha256": __import__("hashlib").sha256(row["question"].encode()).hexdigest(),
                                 "cohort": cohort(row), "scope_doc_ids": row["doc_ids"],
                                 "started_at": started, "finished_at": started + .1,
                                 "client_total_ms": 100, "server_total_ms": 90,
                                 "request_id": f"{concurrency:02x}{i:030x}", "http_status": 200,
                                 "error": False, "error_type": None, "cache_hit": False,
                                 "abstained": not positive, "abstention_reason": None,
                                 "citations": [{"doc_id": "doc", "chunk_id": "c0", "page": 1}] if positive else [],
                                 "stages_ms": {"routing": 1, "retrieval": 20, "grounding": 50,
                                               "llm": 40 if positive else 0, "serialization": 1},
                                 "stage_calls": {"retrieval": 1, "grounding": 1,
                                                 "serialization": 1, "llm": int(positive)},
                                 "retrieval_trace": {"rerank_selected": positive}})
        http_profiles.append({"concurrency": concurrency, "requests": 100,
                              "samples": http_samples,
                              "summary": summarize_http_samples(http_samples, p95_budget_ms=10000)})
    save("http_end_to_end", {"test_sha256": split_hashes["test"],
         "llm_config_sha256": "7"*64, "llm_provider": "openai-compatible", "llm_model": "fixture-model",
         "llm_cache_enabled": False, "answer_cache_enabled": False,
         "profile": "threaded-wsgi-local-http", "release_rerank_cap": 10,
         "p95_budget_ms": 10000, "deployment_ram_bytes": 10000, "peak_rss_bytes": 100,
         "cold_start_ms": 1, "profiles": http_profiles})
    security_cases = [{"id": str(i), "category": sorted(CATEGORIES)[i % len(CATEGORIES)],
                       "expected": "abstain", "output": [], "status": "pass", "question": "negative fixture",
                       "doc_ids": ["doc"], "filters": {}, "gold_evidence": []} for i in range(50)]
    attacks = {"chunk_prompt_injection": "chunk_prompt_injection", "fake_citation": "fake_citation", "duplicate_chunks": "duplicate_output"}
    for case in security_cases:
        if case["category"] in attacks:
            case.update(attack=attacks[case["category"]], attack_calls=1)
    save("security", {"cases": security_cases, "adversarial_cases": 50, "duplicate_results": 0,
                      "negative_fpr": 0, "provenance_leakage": 0, "scope_leakage": 0, "invalid_citation": 0})
    test_hashes = {}
    for test in ("tests/test_phase5_adversarial.py", "tests/test_grounding.py", "tests/test_reranker_integration.py"):
        path = results / "grounding_test_reports" / (Path(test).stem + ".xml")
        path.parent.mkdir(exist_ok=True)
        path.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" /></testsuites>', encoding="utf-8")
        test_hashes[test] = sha256(path)
    save("grounding", {"phase4_5_regression": "pass", "checks": {test: True for test in test_hashes}, "test_reports_sha256": test_hashes})
    save("failure_matrix", {**fault_report, "model_identity_sha256": identity.fingerprint})
    probe = {"outputs": {"q": []}, "baseline": {"q": []}, "phase7_cache_key": "phase7", "phase6_cache_key": "phase6",
             "new_reranker_calls": 0, "reranked_cache_reused": False}
    save("rollback", {"completion_seconds": 1, "new_reranker_calls": 0, "phase6_output_preserved": True,
                      "reranked_cache_reused": False, "index_rebuilt": False, "service_restarted": True,
                      "probes": [{**probe, "pid": 1}, {**probe, "pid": 2}]})
    windows, time = [], datetime(2026, 9, 1, tzinfo=timezone.utc)
    for percent in (0, 1, 5, 10, 25):
        for _ in range(3):
            windows.append(observed_window({**healthy_window(percent), "started_at": time.isoformat(), "ended_at": (time + timedelta(minutes=5)).isoformat()}))
            time += timedelta(minutes=5)
    changes = {"provenance_error": {"provenance_errors": 1}, "scope_leakage": {"scope_errors": 1}, "citation_error": {"citation_errors": 1},
               "timeout_budget": {"timeout_rate": .02}, "negative_fpr_budget": {"negative_fpr": .02}, "error_rate_regression": {"error_rate": .01},
               "memory_budget": {"peak_rss_bytes": 7600}, "latency_budget_three_windows": {"p95_ms": 1100, "p99_ms": 1200}}
    faults = fault_exercises(changes)
    staging = audit_staging({"environment": "staging", "environment_id": "fixture", "collector": "test", "windows": windows}, faults)
    save("staging", staging)
    save("canary", {"windows": windows, "staging_sha256": sha256(args.staging)})
    report = validate(args)
    assert report["errors"] == []
    assert report["status"] == "pass" and report["score"] == 10.0
    from evaluation.validate_reranker_release import build_manifest
    manifest = build_manifest(args, report)
    assert manifest["model_revision"] == identity.model_revision
    assert manifest["route_policy_sha256"] == sha256(args.route)
    assert manifest["gates"]["M6"]["artifact_sha256"]["retrieval_quality_comparison.json"] == sha256(args.quality)
    route_evidence = json.loads(args.route.read_text(encoding="utf-8"))
    altered_route = deepcopy(route_evidence)
    altered_route["route_model"]["weights"][0] += 1
    write_json(args.route, altered_route)
    assert "route_grouped_probability_recomputed_gate" in validate(args)["errors"]
    write_json(args.route, route_evidence)
    http_evidence = json.loads(args.http_end_to_end.read_text(encoding="utf-8"))
    altered_http = deepcopy(http_evidence)
    altered_http["profiles"][0]["samples"][0]["qid"] = "unknown-query"
    write_json(args.http_end_to_end, altered_http)
    assert "http_workload_binding_gate" in validate(args)["errors"]
    write_json(args.http_end_to_end, http_evidence)
    calibration = json.loads(args.calibration.read_text(encoding='utf-8'))
    write_json(args.calibration, {**calibration, 'low_score_action': 'unknown_action'})
    assert 'calibration_policy_domain_gate' in validate(args)['errors']
    write_json(args.calibration, calibration)
    smoke = json.loads(args.smoke.read_text(encoding="utf-8"))
    write_json(args.smoke, {**smoke, "runtime_sha256": "0"*64})
    assert "runtime_sha256_binding" in validate(args)["errors"]
    write_json(args.smoke, smoke)
    raw = deepcopy(candidate)
    raw["test"]["caps"]["40"]["per_query"][0]["candidates"] = []
    save("candidate", {"splits": raw})
    assert "candidate_test_recomputed_gate" in validate(args)["errors"]
    save("candidate", {"splits": candidate})
    quality["test"]["mrr_improvement_relative"] = 100
    save("quality", {**quality, "benchmark_sha256": hashes})
    report = validate(args)
    assert report["score"] is None and "quality_test_recomputed_gate" in report["errors"]
