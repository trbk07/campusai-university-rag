"""Authoritative M0-M12 artifact validation and sequential stage transitions."""
from __future__ import annotations

from argparse import Namespace
import json
import hashlib
import math
from pathlib import Path
import subprocess

from evaluation.common.release_artifacts import sha256, source_identity, verify_index_files, read_json

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = {
    "baseline": "retrieval_baseline_manifest.json", "baseline_report": "retrieval_baseline_comparison.json",
    "human_review": "human_benchmark_review.json", "human_manifest": "human_benchmark_manifest.json",
    "candidate": "candidate_coverage.json", "smoke": "model_snapshot_smoke.json",
    "provider_contract": "reranker_provider_contract.json", "route": "hard_query_route_calibration.json",
    "route_confusion": "hard_query_route_confusion.json", "calibration": "reranker_score_calibration.json",
    "sensitivity": "reranker_cap_sensitivity.json", "quality": "retrieval_quality_comparison.json",
    "performance": "reranker_performance.json", "capacity": "reranker_capacity.json",
    "resource_budget": "reranker_resource_budget.json", "http_end_to_end": "reranker_http_end_to_end.json",
    "grounding": "reranker_grounding_regression.json",
    "security": "reranker_security.json", "failure_matrix": "reranker_failure_matrix.json",
    "rollback": "reranker_rollback.json", "staging": "reranker_staging.json", "canary": "canary_observations.json",
}
GATE_ARTIFACTS = [
    ("baseline", "baseline_report"), ("human_review", "human_manifest"), ("candidate",),
    ("smoke", "provider_contract"), ("route", "route_confusion"), ("calibration", "sensitivity"),
    ("quality",), ("performance", "capacity", "resource_budget", "http_end_to_end"), ("grounding", "security"),
    ("failure_matrix",), ("rollback",), ("staging", "canary"), (),
]
OWNERS = ["baseline reviewer", "human annotator and independent reviewer", "retrieval reviewer",
          "runtime reviewer", "routing reviewer", "calibration reviewer", "quality reviewer",
          "deployment owner", "security and grounding reviewer", "runtime reviewer",
          "operations owner", "staging owner", "release owner"]
FAILURES = {"model_missing", "model_hash_mismatch", "calibration_missing", "calibration_hash_mismatch",
            "timeout", "queue_full", "invalid_score", "wrong_candidate_id", "wrong_doc_id", "wrong_page",
            "empty_output", "oom", "provider_exception", "cache_key_mismatch", "model_revision_mismatch"}
PROVIDER_CASES = {"model_unavailable", "invalid_model_hash", "timeout", "queue_full", "malformed_score",
                  "wrong_provenance", "wrong_doc_scope", "empty_query", "exact_code_query", "abstention_query"}


def default_args(results_dir: Path = Path("evaluation/results")) -> Namespace:
    return Namespace(**{name: results_dir / filename for name, filename in ARTIFACTS.items()},
                     index_dir=Path(".tmp/hybrid-index"), benchmark_dir=Path("data/benchmark"),
                     phase6_calibration=results_dir / "hybrid_retrieval_calibration.json",
                     deployment_ram_bytes=None, through="M12")


def obj(value) -> dict:
    return value if isinstance(value, dict) else {}


def num(value, default=float("inf")) -> float:
    return float(value) if type(value) in (int, float) and math.isfinite(value) else default


def is_hash(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def file_hash(path) -> str | None:
    try:
        return sha256(path)
    except OSError:
        return None


def validate(args: Namespace) -> dict:
    cfg = {**vars(default_args()), **vars(args)}
    reports, missing, invalid = {}, set(), set()
    for name in ARTIFACTS:
        path = Path(cfg[name])
        try:
            data = read_json(path)
            if not isinstance(data, dict):
                raise ValueError("object required")
            reports[name] = data
        except FileNotFoundError:
            missing.add(name)
            reports[name] = {}
        except (OSError, ValueError):
            invalid.add(name)
            reports[name] = {}
    problems = [[] for _ in range(13)]
    def check(gate, condition, error):
        if not condition:
            problems[gate].append(error)
    def bind(gate, report, key, expected):
        check(gate, is_hash(expected) and report.get(key) == expected, f"{key}_binding")
    for gate, names in enumerate(GATE_ARTIFACTS):
        for name in names:
            if name in missing:
                problems[gate].append(f"missing_{name}")
            elif name in invalid:
                problems[gate].append(f"invalid_{name}")
            check(gate, reports[name].get("status") == "pass" and not reports[name].get("errors"), f"{name}_report_gate")
    base, baseline = reports["baseline"], reports["baseline_report"]
    frozen = obj(baseline.get("historical"))
    check(0, base.get("working_tree_clean") is True, "phase6_baseline_gate")
    check(0, bool(frozen) and frozen == baseline.get("rerun_a") == baseline.get("rerun_b"), "baseline_reproducibility_gate")
    for split, floor in (("test", .98), ("holdout", .95)):
        check(0, num(obj(obj(frozen.get(f"{split}_quality")).get("answerable_recall")).get("5"), 0) >= floor
              and obj(frozen.get(f"{split}_negative")).get("false_positive_rate") == 0, f"baseline_{split}_gate")
        bind(0, obj(base.get("benchmark_sha256")), split, file_hash(Path(cfg["benchmark_dir"]) / f"hybrid_retrieval_{split}.jsonl"))
    bind(0, base, "index_sha256", file_hash(Path(cfg["index_dir"]) / "manifest.json"))
    check(0, verify_index_files(Path(cfg["index_dir"])), "baseline_physical_index_gate")
    bind(0, base, "calibration_sha256", file_hash(cfg["phase6_calibration"]))
    bind(0, base, "corpus_sha256", file_hash(ROOT / "data/corpus/university/manifest.json"))
    check(0, is_hash(obj(base.get("dense_model")).get("sha256"))
          and bool(obj(base.get("dense_model")).get("revision")) and bool(obj(base.get("dense_model")).get("name"))
          and is_hash(base.get("reference_report_sha256"))
          and isinstance(base.get("rerun_report_sha256"), list) and len(base["rerun_report_sha256"]) == 2
          and all(is_hash(value) for value in base["rerun_report_sha256"]), "baseline_identity_gate")
    bind(0, base, "reference_report_sha256", file_hash(Path(cfg["baseline"]).parent / "hybrid_holdout_report.json"))
    bind(0, base, "performance_report_sha256", file_hash(Path(cfg["baseline"]).parent / "hybrid_performance_report.json"))
    human, review = reports["human_manifest"], reports["human_review"]
    dataset = Path(cfg["benchmark_dir"]) / "human_retrieval.jsonl"
    bind(1, human, "dataset_sha256", file_hash(dataset))
    bind(1, review, "dataset_sha256", file_hash(dataset))
    bind(1, human, "index_sha256", base.get("index_sha256"))
    bind(1, human, "review_sha256", file_hash(cfg["human_review"]))
    check(1, human.get("frozen") is True and review.get("independent_review_complete") is True, "human_review_gate")
    def rows_at(path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence, validate_rows
        rows = rows_at(dataset)
        regression = [row for split in ("dev", "test", "holdout")
                      for row in rows_at(Path(cfg["benchmark_dir"]) / f"hybrid_retrieval_{split}.jsonl")]
        actual = validate_rows(rows, frozen_evidence(Path(cfg["index_dir"])), regression)
        check(1, actual["status"] == "pass" and review.get("counts") == actual["counts"]
              and review.get("records") == actual["records"], "human_dataset_content_gate")
        for split in ("dev", "test", "holdout"):
            check(1, rows_at(Path(cfg["benchmark_dir"]) / f"human_retrieval_{split}.jsonl")
                  == [row for row in rows if row.get("split") == split], f"human_{split}_content_gate")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        problems[1].append("human_dataset_input_gate")
    for split in ("dev", "test", "holdout"):
        bind(1, obj(human.get("split_sha256")), split, file_hash(Path(cfg["benchmark_dir"]) / f"human_retrieval_{split}.jsonl"))
    candidate = reports["candidate"]
    bind(2, candidate, "index_sha256", base.get("index_sha256"))
    bind(2, candidate, "phase6_calibration_sha256", base.get("calibration_sha256"))
    for split, floor in (("test", .99), ("holdout", .97), ("human_dev", .95), ("human_test", .95), ("human_holdout", .95)):
        part = obj(obj(candidate.get("splits")).get(split))
        metrics = obj(obj(part.get("caps")).get("40"))
        check(2, num(metrics.get("answerable"), 0) > 0 and num(metrics.get("candidate_recall"), 0) >= floor
              and all(metrics.get(key) == 0 for key in ("provenance_errors", "scope_errors", "duplicate_result_sets")), f"candidate_{split}_gate")
        expected = obj(human.get("split_sha256")).get(split.removeprefix("human_")) if split.startswith("human_") else obj(base.get("benchmark_sha256")).get(split)
        bind(2, part, "benchmark_sha256", expected)
        try:
            from evaluation.retrieval.evaluate_candidate_coverage import audit_outputs, coverage_errors
            from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
            path = Path(cfg["benchmark_dir"]) / (f"human_retrieval_{split.removeprefix('human_')}.jsonl" if split.startswith("human_")
                                                 else f"hybrid_retrieval_{split}.jsonl")
            pairs = metrics["per_query"]
            check(2, len({pair["qid"] for pair in pairs}) == len(pairs), "candidate_pair_identity_gate")
            observed = {pair["qid"]: pair["candidates"] for pair in pairs}
            docs = read_json(Path(cfg["index_dir"]) / "manifest.json")["documents"]
            actual = audit_outputs(rows_at(path), observed, docs, 40, frozen_evidence(Path(cfg["index_dir"])))
            check(2, not coverage_errors(actual, floor), f"candidate_{split}_stratified_coverage_gate")
            # JSON encodes provenance coordinate tuples as lists.
            check(2, json.loads(json.dumps(actual)) == metrics, f"candidate_{split}_recomputed_gate")
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            problems[2].append(f"candidate_{split}_evidence_gate")
    smoke, contract = reports["smoke"], reports["provider_contract"]
    try:
        from campusai.retrieval.cross_encoder_provider import ModelIdentity
        identity = ModelIdentity(**smoke["model_identity"])
        bind(3, smoke, "model_identity_sha256", identity.fingerprint)
        import re
        check(3, bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", identity.model_revision)), "model_immutable_revision_gate")
        files = smoke["model_files_sha256"]
        check(3, isinstance(files, dict) and bool(files)
              and all(isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts
                      and is_hash(digest) for name, digest in files.items()), "model_file_manifest_gate")
        digest = hashlib.sha256(json.dumps(sorted(files.items()), separators=(",", ":")).encode()).hexdigest()
        check(3, digest == identity.model_sha256, "model_snapshot_manifest_binding")
        if cfg.get("model_dir") is not None:
            from campusai.retrieval.cross_encoder_provider import snapshot_sha256
            snapshot = Path(cfg["model_dir"])
            check(3, snapshot.name == identity.model_revision and snapshot_sha256(snapshot) == identity.model_sha256,
                  "model_physical_snapshot_gate")
    except (KeyError, TypeError, ValueError, AttributeError, OSError, RuntimeError):
        problems[3].append("offline_model_gate")
    checks = obj(contract.get("checks"))
    check(3, PROVIDER_CASES <= set(checks) and all(checks.get(key) is True for key in PROVIDER_CASES), "provider_contract_gate")
    check(3, smoke.get("deterministic") is True and num(smoke.get("max_score_delta")) <= 1e-5, "model_determinism_gate")
    for key in ("singleton_loading", "bounded_queue", "warmup", "private_scores", "candidate_set_preserved"):
        check(3, contract.get(key) is True, f"provider_{key}_gate")
    route, confusion = reports["route"], reports["route_confusion"]
    metrics = obj(route.get("routing_metrics"))
    check(4, route.get("calibration_split") == "dev" and route.get("holdout_used") is False
          and route.get("test_used") is False and route.get("feature_leakage_review") == "pass"
          and num(metrics.get("hard_recall"), 0) >= .95 and num(metrics.get("easy_unnecessary_rerank_rate")) <= .20, "hard_route_gate")
    from campusai.retrieval.route_probability import FEATURES as ROUTE_FEATURES
    check(4, route.get("feature_allowlist") == list(ROUTE_FEATURES)
          and isinstance(route.get("route_model"), dict), "route_feature_allowlist_gate")
    try:
        from evaluation.reranker.calibrate_route_probabilities import fit_route_probabilities
        fitted, diagnostics, feasible = fit_route_probabilities(
            route["samples"], rows_at(Path(cfg["benchmark_dir"]) / "human_retrieval_dev.jsonl"))
        check(4, feasible and fitted == route.get("route_model")
              and diagnostics == route.get("route_diagnostics"), "route_grouped_probability_recomputed_gate")
    except (ValueError, KeyError, TypeError, OSError):
        problems[4].append("route_grouped_probability_evidence_gate")
    bind(4, route, "training_split_sha256", obj(human.get("split_sha256")).get("dev"))
    bind(4, confusion, "route_calibration_sha256", file_hash(cfg["route"]))
    for split, hard, easy in (("dev", .95, .20), ("test", .90, .25), ("holdout", .90, .25)):
        part = obj(obj(confusion.get("splits")).get(split))
        check(4, num(part.get("hard_count"), 0) > 0 and num(part.get("easy_count"), 0) > 0
              and num(part.get("hard_recall"), 0) >= hard and num(part.get("easy_unnecessary_rerank_rate")) <= easy
              and part.get("exact_code_rerank_rate") == 0 and part.get("abstention_rerank_rate") == 0
              and part.get("deterministic") is True, f"route_{split}_gate")
        bind(4, part, "benchmark_sha256", obj(human.get("split_sha256")).get(split))
        try:
            from evaluation.reranker.calibrate_hard_query_route import route_metrics
            actual = route_metrics(part["samples"], route["easy_confidence_threshold"], route["easy_margin_threshold"],
                                   route.get("minimum_agreement", 0), route.get("constraint_threshold", 0),
                                   route.get("route_model"))
            check(4, all(part.get(key) == value for key, value in actual.items()), f"route_{split}_recomputed_gate")
            if split == "dev":
                check(4, route.get("routing_metrics") == actual, "route_dev_calibration_metrics_gate")
            labels = {r["qid"]: r["difficulty"] for r in rows_at(Path(cfg["benchmark_dir"]) / f"human_retrieval_{split}.jsonl")}
            sampled = [s["qid"] for s in part["samples"]]
            bypass = part["bypass"]
            check(4, len(sampled) == len(set(sampled)) and set(sampled) <= set(labels)
                  and set(bypass) == {"exact_or_abstained", "single_candidate"}
                  and all(type(value) is int and value >= 0 for value in bypass.values())
                  and len(sampled) + sum(bypass.values()) == len(labels), f"route_{split}_coverage_gate")
            check(4, all(labels.get(s["qid"]) == s["difficulty"] for s in part["samples"]), f"route_{split}_labels_gate")
        except (ValueError, KeyError, TypeError, OSError):
            problems[4].append(f"route_{split}_evidence_gate")
    calibration, sensitivity = reports["calibration"], reports["sensitivity"]
    check(5, calibration.get("calibration_split") == "dev" and calibration.get("holdout_used") is False
          and calibration.get("test_used") is False and calibration.get("candidate_cap") == 40
          and calibration.get("rerank_candidate_cap") in (8, 10, 12, 16, 20)
          and num(calibration.get("recall"), 0) >= .95 and num(calibration.get("false_positive_rate")) <= .01, "reranker_calibration_gate")
    for key, expected in (("route_calibration_sha256", file_hash(cfg["route"])),
                          ("training_split_sha256", obj(human.get("split_sha256")).get("dev")),
                          ("model_identity_sha256", smoke.get("model_identity_sha256"))):
        bind(5, calibration, key, expected)
    check(5, calibration.get("route_model") == route.get("route_model"), "calibration_route_model_binding_gate")
    trials = sensitivity.get("trials", [])
    check(5, isinstance(trials, list) and {8, 10, 12, 16, 20} <= {p.get("rerank_cap") for p in trials if isinstance(p, dict)}
          and sensitivity.get("calibration_split") == "dev" and sensitivity.get("test_used") is False
          and sensitivity.get("holdout_used") is False, "reranker_sensitivity_gate")
    for key in ("fallback_rate", "timeout_rate", "invalid_score_rate"):
        check(5, 0 <= num(calibration.get(key)) <= 1, f"calibration_{key}_gate")
    check(5, calibration.get("invalid_score_rate") == 0, "calibration_invalid_scores_gate")
    check(5, 0 <= num(calibration.get("timeout_rate")) <= .01
          and 0 <= num(calibration.get("fallback_rate")) <= 1
          and calibration.get("low_score_action", "phase6") in ("phase6", "abstain")
          and calibration.get("evidence_policy") == "probability"
          and isinstance(calibration.get("evidence_model"), dict)
          and math.isfinite(num(calibration.get("threshold")))
          and 0 <= num(calibration.get("margin_threshold")), "calibration_policy_domain_gate")
    try:
        from evaluation.reranker.calibrate_reranker_scores import _quality, calibrated_outputs
        observed = calibration["calibration_observations"]
        rows = rows_at(Path(cfg["benchmark_dir"]) / "human_retrieval_dev.jsonl")
        outputs = dict(observed["baseline"])
        check(5, set(outputs) == {row["qid"] for row in rows} and set(observed["proposals"]) <= set(outputs), "calibration_pair_identity_gate")
        outputs = calibrated_outputs(outputs, observed["proposals"], calibration, rows=rows)
        if calibration.get("evidence_model") is not None:
            from evaluation.reranker.calibrate_evidence_probabilities import calibrate_probabilities
            refit, diagnostics = calibrate_probabilities(rows, observed["baseline"], observed["proposals"])
            check(5, refit["evidence_model"] == calibration["evidence_model"] and diagnostics == calibration["comparison"]
                  and diagnostics["feasible"], "calibration_grouped_probability_recomputed_gate")
        actual = _quality(rows, outputs)
        check(5, abs(actual["answerable_recall_at_5"] - calibration["recall"]) < 1e-9
              and actual["negative_fpr"] == calibration["false_positive_rate"], "calibration_recomputed_gate")
        for trial in trials:
            relative = Path(trial["artifact"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("invalid sensitivity artifact path")
            bind(5, trial, "artifact_sha256", file_hash(Path(cfg["sensitivity"]).parent / relative))
            trial_report = read_json(Path(cfg["sensitivity"]).parent / relative)
            check(5, trial_report.get("low_score_action", "phase6") == calibration.get("low_score_action", "phase6"),
                  "sensitivity_low_score_action_binding")
            check(5, trial_report.get("evidence_policy", "score") == calibration.get("evidence_policy", "score"), "sensitivity_evidence_policy_binding")
            for key, expected in (("status", trial_report.get("status")), ("rerank_cap", trial_report.get("rerank_candidate_cap")),
                                  ("recall", trial_report.get("recall")), ("negative_fpr", trial_report.get("false_positive_rate")),
                                  ("p95_ms", obj(trial_report.get("rerank_latency_ms")).get("p95")),
                                  ("mrr", obj(obj(trial_report.get("comparison")).get("selected")).get("mrr"))):
                check(5, trial.get(key) == expected and expected is not None, "sensitivity_trial_metrics_gate")
        passing = [trial for trial in trials if trial["status"] == "pass" and num(trial.get("eligible_requests"), 0) > 0
                   and 0 <= num(trial.get("p95_ms")) <= num(sensitivity.get("p95_budget_ms"), 0)
                   and num(trial.get("timeout_rate")) <= .005]
        selected = max(passing, key=lambda trial: (trial["mrr"], trial["recall"], -trial["p95_ms"], -trial["rerank_cap"])) if passing else {}
        check(5, bool(selected) and sensitivity.get("selected_cap") == calibration.get("rerank_candidate_cap") == selected.get("rerank_cap")
              and file_hash(cfg["calibration"]) == selected.get("artifact_sha256")
              and 0 < num(sensitivity.get("p95_budget_ms"), 0) <= 1000, "sensitivity_selected_policy_gate")
    except (ValueError, KeyError, TypeError, OSError):
        problems[5].append("calibration_evidence_gate")
    quality = reports["quality"]
    try:
        from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
        from evaluation.retrieval.compare_retrieval_quality import compare_split, quality_errors
        evidence = frozen_evidence(Path(cfg["index_dir"])) if quality else {}
        docs = json.loads((Path(cfg["index_dir"]) / "manifest.json").read_text(encoding="utf-8"))["documents"] if quality else []
        recomputed = {}
        for split in ("test", "holdout", "human_test", "human_holdout"):
            path = Path(cfg["benchmark_dir"]) / (f"human_retrieval_{split.removeprefix('human_')}.jsonl" if split.startswith("human_") else f"hybrid_retrieval_{split}.jsonl")
            part = obj(quality.get(split))
            pairs = part["per_query"]
            check(6, len(pairs) == len({p["qid"] for p in pairs}), f"quality_{split}_pair_identity_gate")
            recomputed[split] = compare_split(rows_at(path), {p["qid"]: p["baseline_evidence"] for p in pairs},
                                            {p["qid"]: p["phase7_evidence"] for p in pairs}, evidence, docs,
                                            seed=part["paired_statistics"]["mrr"]["seed"])
            check(6, recomputed[split] == part, f"quality_{split}_recomputed_gate")
            bind(6, obj(quality.get("benchmark_sha256")), split, file_hash(path))
        problems[6].extend(quality_errors(recomputed))
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        problems[6].extend(["quality_evidence_gate", "statistical_significance_gate"])
    for split in ("test", "holdout"):
        check(6, bool(obj(quality.get(split))), f"quality_{split}_gate")
    performance, budget, capacity = reports["performance"], reports["resource_budget"], reports["capacity"]
    limits = performance.get("resource_limits")
    check(7, isinstance(limits, dict) and set(limits) == {"timeout_ms", "queue_limit", "failure_limit", "score_cache_size"}
          and all(type(value) is int for value in limits.values())
          and limits.get("timeout_ms") == 1000 and 0 <= limits.get("queue_limit", -1) <= 99
          and limits.get("failure_limit") == 3 and limits.get("score_cache_size") == 0
          and limits == capacity.get("resource_limits"), "capacity_resource_limits_binding")
    ram = cfg["deployment_ram_bytes"] or budget.get("deployment_ram_bytes")
    peak = num(performance.get("peak_rss_bytes"), 0)
    check(7, num(ram, 0) > 0 and peak > 0 and peak <= .75 * num(ram, 0), "deployment_ram_headroom_gate")
    try:
        from evaluation.reranker.measure_reranker_capacity import summarize_samples
        actual = summarize_samples(performance["samples"])
        check(7, actual == performance.get("summary"), "performance_recomputed_gate")
        check(7, actual["requests"] >= 100 and actual["hard_requests"] >= 30
              and actual["hard_rerank_requests"] >= 30
              and actual["hard_p50_ms"] <= 500 and actual["hard_p95_ms"] <= 1000 and actual["hard_p99_ms"] <= 2000
              and actual["timeout_rate"] <= .005 and actual["timeout_fallback_rate"] <= .01 and actual["errors"] == 0, "performance_gate")
    except (ImportError, TypeError, ValueError, KeyError):
        problems[7].append("performance_gate")
    matrix = capacity.get("profiles", [])
    check(7, isinstance(matrix, list) and {(8, 1), (10, 1), (20, 1), (10, 5), (10, 20)}
          <= {(p.get("rerank_cap"), p.get("concurrency")) for p in matrix if isinstance(p, dict)}
          and capacity.get("queue_overflow_request_failures") == 0, "capacity_gate")
    try:
        for profile in matrix:
            check(7, profile.get("resource_limits") == limits, "capacity_profile_limits_binding")
            actual = summarize_samples(profile["samples"])
            check(7, actual == profile.get("summary") and actual["requests"] >= 100 and actual["errors"] == 0,
                  "capacity_recomputed_gate")
        release_cap = calibration.get("rerank_candidate_cap")
        serving_profiles = [p for p in matrix if p.get("rerank_cap") == release_cap]
        check(7, capacity.get("release_rerank_cap") == release_cap
              and capacity.get("deployment_device") == obj(smoke.get("model_identity")).get("device")
              and {1, 5, 10, 20} <= {p.get("concurrency") for p in serving_profiles}, "capacity_deployment_profile_gate")
        for profile in serving_profiles:
            metrics = summarize_samples(profile["samples"])
            check(7, metrics["hard_p95_ms"] <= 1000 and metrics["hard_p99_ms"] <= 2000
                  and metrics["timeout_rate"] <= .005, "capacity_deployment_latency_gate")
        if str(obj(smoke.get("model_identity")).get("device", "")).startswith("cuda"):
            check(7, (20, 5) in {(p.get("rerank_cap"), p.get("concurrency")) for p in matrix}, "capacity_gpu_matrix_gate")
    except (ValueError, KeyError, TypeError):
        problems[7].append("capacity_evidence_gate")
    http = reports["http_end_to_end"]
    try:
        import re
        from evaluation.reranker.measure_reranker_http import CONCURRENCIES, MAX_P95_BUDGET_MS, cohort, workload, summarize_http_samples
        from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
        test_rows = rows_at(Path(cfg["benchmark_dir"]) / "human_retrieval_test.jsonl")
        by_qid = {row["qid"]: row for row in test_rows}
        docs = read_json(Path(cfg["index_dir"]) / "manifest.json")["documents"]
        indexed = frozen_evidence(Path(cfg["index_dir"]))
        bind(7, http, "test_sha256", file_hash(Path(cfg["benchmark_dir"]) / "human_retrieval_test.jsonl"))
        check(7, http.get("llm_provider") in {"openai-compatible", "gemini"}
              and isinstance(http.get("llm_model"), str) and bool(http["llm_model"])
              and is_hash(http.get("llm_config_sha256"))
              and http.get("llm_cache_enabled") is False and http.get("answer_cache_enabled") is False
              and http.get("profile") == "threaded-wsgi-local-http", "http_live_llm_identity_gate")
        check(7, http.get("release_rerank_cap") == calibration.get("rerank_candidate_cap")
              and type(http.get("p95_budget_ms")) is int
              and 0 < http["p95_budget_ms"] <= MAX_P95_BUDGET_MS,
              "http_release_cap_and_slo_gate")
        check(7, num(http.get("cold_start_ms"), -1) >= 0
              and num(http.get("peak_rss_bytes"), 0) > 0
              and http.get("deployment_ram_bytes") == ram
              and num(http.get("peak_rss_bytes")) <= .75 * num(ram), "http_resource_gate")
        if obj(smoke.get("model_identity")).get("device", "").startswith("cuda"):
            check(7, num(http.get("peak_gpu_memory_bytes"), 0) > 0, "http_gpu_memory_gate")
        profiles = http["profiles"]
        check(7, isinstance(profiles, list) and len(profiles) == len(CONCURRENCIES)
              and {p.get("concurrency") for p in profiles} == set(CONCURRENCIES), "http_concurrency_matrix_gate")
        request_ids = set()
        for profile in profiles:
            samples = profile["samples"]
            actual = summarize_http_samples(samples, p95_budget_ms=http["p95_budget_ms"])
            check(7, actual == profile.get("summary") and actual["passed"]
                  and profile.get("requests") == len(samples), "http_profile_recomputed_gate")
            check(7, [sample["qid"] for sample in samples] ==
                  [row["qid"] for row in workload(test_rows, profile["requests"])],
                  "http_workload_sequence_gate")
            check(7, actual["grounded_answers"] >= 30, "http_grounded_response_gate")
            negatives = 0
            false_positives = 0
            for sample in samples:
                row = by_qid.get(sample["qid"])
                check(7, row is not None and sample["question_sha256"] == hashlib.sha256(row["question"].encode()).hexdigest()
                      and sample["cohort"] == cohort(row) and sample.get("scope_doc_ids") == row.get("doc_ids"),
                      "http_workload_binding_gate")
                check(7, sample["http_status"] == 200 and sample["error"] is False
                      and sample["cache_hit"] is False and isinstance(sample.get("abstained"), bool)
                      and re.fullmatch(r"[0-9a-f]{32}", sample["request_id"])
                      and sample["request_id"] not in request_ids
                      and sample["finished_at"] >= sample["started_at"]
                      and abs(sample["client_total_ms"] -
                              (sample["finished_at"] - sample["started_at"]) * 1000) <= .01
                      and sample["server_total_ms"] <= sample["client_total_ms"]
                      and sample.get("abstention_reason") != "llm_error", "http_raw_success_gate")
                request_ids.add(sample["request_id"])
                check(7, sample["stage_calls"].get("retrieval") == 1
                      and sample["stage_calls"].get("grounding") == 1
                      and sample["stage_calls"].get("serialization") == 1
                      and 0 <= sample["stage_calls"].get("llm", 0) <= 1,
                      "http_stage_observation_gate")
                check(7, all(c.get("doc_id") in (row.get("doc_ids") or docs)
                             for c in sample["citations"]), "http_scope_gate")
                check(7, sample["abstained"] or bool(sample["citations"]), "http_answer_citation_gate")
                for citation in sample["citations"]:
                    source = indexed.get((citation.get("doc_id"), citation.get("chunk_id")))
                    check(7, bool(source) and citation.get("page") == source["page"],
                          "http_citation_provenance_gate")
                if row["answerable"] is False:
                    negatives += 1
                    false_positives += sample["abstained"] is False
            check(7, negatives >= 5 and false_positives / negatives <= .01,
                  "http_negative_grounding_gate")
    except (ImportError, OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError):
        problems[7].append("http_end_to_end_evidence_gate")
    for key in ("cold_start_ms", "warmup_ms", "cpu_utilization_percent"):
        check(7, num(performance.get(key), -1) >= 0, f"performance_{key}_gate")
    security = reports["security"]
    cases = security.get("cases", [])
    check(8, isinstance(cases, list) and len(cases) >= 50
          and len({p.get("id") for p in cases if isinstance(p, dict)}) == len(cases)
          and all(isinstance(p, dict) and p.get("status") == "pass" for p in cases), "security_adversarial_gate")
    for key in ("provenance_leakage", "scope_leakage", "invalid_citation"):
        check(8, security.get(key) == 0, f"security_{key}_gate")
    check(8, num(security.get("negative_fpr")) <= .01, "security_negative_gate")
    try:
        from evaluation.reranker.evaluate_reranker_security import CATEGORIES, audit_cases
        docs = json.loads((Path(cfg["index_dir"]) / "manifest.json").read_text(encoding="utf-8"))["documents"]
        actual_security = audit_cases(cases, frozen_evidence(Path(cfg["index_dir"])), docs)
        check(8, actual_security["status"] == "pass"
              and all(security.get(key) == value for key, value in actual_security.items()), "security_recomputed_gate")
        check(8, CATEGORIES <= {case["category"] for case in cases}, "security_category_coverage_gate")
        negative = [case for case in cases if case["expected"] == "abstain"]
        actual_fpr = sum(bool(case["output"]) for case in negative) / len(negative) if negative else 1.0
        check(8, actual_fpr == security.get("negative_fpr"), "security_recomputed_fpr_gate")
        evidence = frozen_evidence(Path(cfg["index_dir"]))
        for case in cases:
            if case.get("attack"):
                check(8, num(case.get("attack_calls"), 0) > 0, "security_attack_executed_gate")
            for item in case["output"]:
                frozen_item = evidence.get((item["doc_id"], item["chunk_id"]))
                check(8, bool(frozen_item) and item["page"] == frozen_item["page"]
                      and item["content"] == frozen_item["content"], "security_recomputed_provenance_gate")
            if case["expected"] == "phase6_fallback":
                check(8, case["output"] == case["phase6_output"], "security_recomputed_fallback_gate")
    except (ValueError, KeyError, TypeError, OSError, AttributeError):
        problems[8].append("security_evidence_gate")
    check(8, reports["grounding"].get("phase4_5_regression") == "pass" and bool(reports["grounding"].get("checks")), "grounding_regression_gate")
    check(8, all(value is True for value in obj(reports["grounding"].get("checks")).values()), "grounding_checks_gate")
    try:
        import xml.etree.ElementTree as ET
        required_tests = {"tests/test_grounding_adversarial.py", "tests/test_grounding.py", "tests/test_reranker_integration.py"}
        test_hashes = reports["grounding"]["test_reports_sha256"]
        check(8, required_tests <= set(test_hashes), "grounding_raw_report_coverage_gate")
        for test in required_tests:
            path = Path(cfg["grounding"]).parent / "grounding_test_reports" / (Path(test).stem + ".xml")
            bind(8, test_hashes, test, file_hash(path))
            suites = ET.parse(path).getroot().iter("testsuite")
            counts = list(suites)
            check(8, bool(counts) and sum(int(s.get("tests", "0")) for s in counts) > 0
                  and all(int(s.get(key, "0")) == 0 for s in counts for key in ("errors", "failures", "skipped")),
                  "grounding_raw_report_gate")
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError):
        problems[8].append("grounding_raw_report_gate")
    checks = obj(reports["failure_matrix"].get("checks"))
    check(9, FAILURES <= set(checks) and all(checks.get(key) is True for key in FAILURES), "failure_matrix_gate")
    for gate, name, required in ((3, "provider_contract", PROVIDER_CASES), (9, "failure_matrix", FAILURES)):
        observed = reports[name].get("observations", [])
        check(gate, isinstance(observed, list) and bool(observed)
              and all(isinstance(row, dict) and row.get("passed") is True and row.get("error_type") is None for row in observed)
              and reports[name].get("evidence_type") == "controlled_fault_injection", f"{name}_evidence_gate")
        runtime_cases = {row.get("case"): row for row in observed if isinstance(row, dict)} if isinstance(observed, list) else {}
        permanent = {"provider_exception", "oom", "model_missing", "invalid_score", "wrong_candidate_id",
                     "wrong_doc_id", "wrong_page", "empty_output", "malformed_output", "wrong_original_rank", "infinite_score"}
        check(gate, all(runtime_cases.get(case, {}).get("permanent") is True
                        and runtime_cases[case].get("phase7_enabled_after") is False
                        and runtime_cases[case].get("provider_closed") is True
                        and runtime_cases[case].get("baseline_preserved") is True
                        and runtime_cases[case].get("provider_calls_at_fault") == 1
                        and runtime_cases[case].get("provider_calls_after_followup") == 1 for case in permanent),
              f"{name}_permanent_failure_gate")
    rollback = reports["rollback"]
    check(10, num(rollback.get("completion_seconds")) <= 300 and rollback.get("new_reranker_calls") == 0
          and rollback.get("phase6_output_preserved") is True and rollback.get("reranked_cache_reused") is False
          and rollback.get("index_rebuilt") is False and rollback.get("service_restarted") is True, "rollback_gate")
    try:
        first, second = rollback["probes"]
        check(10, first["outputs"] == first["baseline"] == second["outputs"] == second["baseline"]
              and first["pid"] != second["pid"] and first["phase7_cache_key"] != second["phase6_cache_key"]
              and first["new_reranker_calls"] == second["new_reranker_calls"] == 0
              and not first["reranked_cache_reused"] and not second["reranked_cache_reused"], "rollback_recomputed_gate")
    except (ValueError, KeyError, TypeError):
        problems[10].append("rollback_evidence_gate")
    staging, canary = reports["staging"], reports["canary"]
    check(11, staging.get("environment") == "staging" and staging.get("auto_rollback_tested") is True
          and staging.get("rollout_percentages") == [0, 1, 5, 10, 25], "staging_gate")
    bind(11, canary, "staging_sha256", file_hash(cfg["staging"]))
    try:
        from evaluation.reranker.audit_canary_staging import audit_staging
        actual = audit_staging(staging, {"exercises": staging["fault_exercises"]}, evidence=frozen_evidence(Path(cfg["index_dir"])))
        check(11, actual["auto_rollback_checks"] == staging.get("auto_rollback_checks")
              and staging["windows"] == canary.get("windows"), "staging_recomputed_gate")
    except (ValueError, TypeError, KeyError, AttributeError):
        problems[11].append("staging_evidence_gate")
    try:
        from campusai.retrieval.canary_rollout import CanaryController
        controller = CanaryController()
        windows = canary["windows"]
        check(11, len(windows) >= 15 and {0, 1, 5, 10, 25} <= {w.get("traffic_percent") for w in windows}, "canary_observation_gate")
        for window in windows:
            check(11, controller.observe(window) is None, "canary_budget_gate")
    except (ImportError, ValueError, TypeError, KeyError, AttributeError):
        problems[11].append("canary_observation_gate")
    source = source_identity(ROOT)
    for gate in range(3, 12):
        for name in GATE_ARTIFACTS[gate]:
            report = reports[name]
            for key, expected in (("source_sha256", source["source_sha256"]), ("runtime_sha256", source.get("runtime_sha256")),
                                  ("index_sha256", base.get("index_sha256")),
                                  ("phase6_calibration_sha256", base.get("calibration_sha256")),
                                  ("model_identity_sha256", smoke.get("model_identity_sha256"))):
                bind(gate, report, key, expected)
            if gate >= 6:
                bind(gate, report, "calibration_sha256", file_hash(cfg["calibration"]))
                bind(gate, report, "route_calibration_sha256", file_hash(cfg["route"]))
                bind(gate, report, "training_split_sha256", obj(human.get("split_sha256")).get("dev"))
                bind(gate, report, "human_benchmark_sha256", human.get("dataset_sha256"))
    for gate, filename, names in (
            (4, "reranker_route_freeze.json", ("route", "smoke", "human_manifest")),
            (6, "reranker_policy_freeze.json", ("route", "smoke", "human_manifest", "calibration", "sensitivity"))):
        try:
            lock = read_json(Path(cfg["route" if gate == 4 else "quality"]).parent / filename)
            check(gate, lock.get("artifact_sha256") == {name: file_hash(cfg[name]) for name in names}, "heldout_freeze_binding_gate")
            from datetime import datetime
            check(gate, datetime.fromisoformat(lock["heldout_started_at"]).tzinfo is not None, "heldout_freeze_time_gate")
        except (OSError, ValueError, TypeError, KeyError):
            problems[gate].append("missing_or_invalid_heldout_freeze")
    try:
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        dirty = True
    check(12, not dirty, "working_tree_dirty")
    hashes = {name: file_hash(cfg[name]) for name in ARTIFACTS}
    check(12, all(is_hash(value) for value in hashes.values()), "release_artifact_hash_gate")
    sidecars = ("retrieval_quality_comparison.md", "retrieval_ranking_regressions.jsonl",
                "reranker_route_freeze.json", "reranker_policy_freeze.json")
    directory = Path(cfg["quality"]).parent
    for filename in sidecars:
        hashes[filename] = file_hash(directory / filename)
        check(12, is_hash(hashes[filename]), "release_raw_artifact_gate")
    try:
        actual = rows_at(directory / "retrieval_ranking_regressions.jsonl")
        expected = [{"split": split, **row}
                    for split in ("test", "holdout", "human_test", "human_holdout")
                    for row in quality[split]["per_query"] if row["qid"] in quality[split]["regression_qids"]]
        check(12, actual == expected, "release_regressions_content_gate")
    except (OSError, ValueError, KeyError, TypeError):
        problems[12].append("release_regressions_content_gate")
    for trial in trials if isinstance(trials, list) else []:
        if isinstance(trial, dict) and isinstance(trial.get("artifact"), str):
            hashes[trial["artifact"]] = file_hash(Path(cfg["sensitivity"]).parent / trial["artifact"])
    for test, digest in obj(reports["grounding"].get("test_reports_sha256")).items():
        hashes["grounding_test_reports/" + Path(test).stem + ".xml"] = digest
    gates, prior_failed = {}, False
    for index in range(13):
        absent = any(name in missing for name in GATE_ARTIFACTS[index])
        evidence_status = "BLOCKED" if absent else "FAIL" if problems[index] else "PASS"
        status = "BLOCKED" if prior_failed else evidence_status
        gates[f"M{index}"] = {"status": status, "evidence_status": evidence_status, "owner": OWNERS[index],
                             "errors": sorted(set(problems[index])), "requires": [f"M{index-1}"] if index else [],
                             "artifacts": [ARTIFACTS[name] for name in GATE_ARTIFACTS[index]],
                             "verify_command": f"python -m evaluation.reranker.validate_reranker_release --through M{index}"}
        prior_failed |= status != "PASS"
    through = int(cfg["through"][1:])
    errors = sorted({error for index in range(through + 1) for error in problems[index]})
    passed = all(gates[f"M{index}"]["status"] == "PASS" for index in range(through + 1))
    return {"schema_version": 2, "phase": 7, "status": "pass" if passed else "conditional",
            "all_release_gates_pass": passed and through == 12,
            "score": 10.0 if passed and through == 12 else None, "errors": errors, "gates": gates,
            "through": cfg["through"], **source, "working_tree_clean": not dirty, "base_release": "phase6-rc3",
            "baseline_commit": base.get("commit"), "model_identity_sha256": smoke.get("model_identity_sha256"),
            "index_sha256": base.get("index_sha256"), "calibration_sha256": file_hash(cfg["calibration"]),
            "artifact_sha256": hashes, "deployment_ram_bytes": ram}
