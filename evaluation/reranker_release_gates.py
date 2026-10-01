"""Authoritative M0-M12 artifact validation and sequential stage transitions."""
from __future__ import annotations

from argparse import Namespace
import json
import math
from pathlib import Path
import subprocess

from evaluation.release_artifacts import sha256, source_identity, verify_index_files

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "baseline": "retrieval_baseline_manifest.json", "baseline_report": "retrieval_baseline_comparison.json",
    "human_review": "human_benchmark_review.json", "human_manifest": "human_benchmark_manifest.json",
    "candidate": "candidate_coverage.json", "smoke": "model_snapshot_smoke.json",
    "provider_contract": "reranker_provider_contract.json", "route": "hard_query_route_calibration.json",
    "route_confusion": "hard_query_route_confusion.json", "calibration": "reranker_score_calibration.json",
    "sensitivity": "reranker_cap_sensitivity.json", "quality": "retrieval_quality_comparison.json",
    "performance": "reranker_performance.json", "capacity": "reranker_capacity.json",
    "resource_budget": "reranker_resource_budget.json", "grounding": "reranker_grounding_regression.json",
    "security": "reranker_security.json", "failure_matrix": "reranker_failure_matrix.json",
    "rollback": "reranker_rollback.json", "staging": "reranker_staging.json", "canary": "canary_observations.json",
}
GATE_ARTIFACTS = [
    ("baseline", "baseline_report"), ("human_review", "human_manifest"), ("candidate",),
    ("smoke", "provider_contract"), ("route", "route_confusion"), ("calibration", "sensitivity"),
    ("quality",), ("performance", "capacity", "resource_budget"), ("grounding", "security"),
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
                     index_dir=Path(".tmp/phase6-index"), benchmark_dir=Path("data/benchmark"),
                     phase6_calibration=results_dir / "phase6_retrieval_calibration.json",
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
            data = json.loads(path.read_text(encoding="utf-8"))
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
        bind(0, obj(base.get("benchmark_sha256")), split, file_hash(Path(cfg["benchmark_dir"]) / f"phase6_retrieval_{split}.jsonl"))
    bind(0, base, "index_sha256", file_hash(Path(cfg["index_dir"]) / "manifest.json"))
    check(0, verify_index_files(Path(cfg["index_dir"])), "baseline_physical_index_gate")
    bind(0, base, "calibration_sha256", file_hash(cfg["phase6_calibration"]))
    bind(0, base, "corpus_sha256", file_hash(ROOT / "data/corpus/university/manifest.json"))
    check(0, is_hash(obj(base.get("dense_model")).get("sha256"))
          and bool(obj(base.get("dense_model")).get("revision")) and bool(obj(base.get("dense_model")).get("name"))
          and is_hash(base.get("reference_report_sha256"))
          and isinstance(base.get("rerun_report_sha256"), list) and len(base["rerun_report_sha256"]) == 2
          and all(is_hash(value) for value in base["rerun_report_sha256"]), "baseline_identity_gate")
    bind(0, base, "reference_report_sha256", file_hash(Path(cfg["baseline"]).parent / "phase6_holdout_report.json"))
    bind(0, base, "performance_report_sha256", file_hash(Path(cfg["baseline"]).parent / "phase6_performance_report.json"))
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
        from evaluation.freeze_human_benchmark import frozen_evidence, validate_rows
        rows = rows_at(dataset)
        regression = [row for split in ("dev", "test", "holdout")
                      for row in rows_at(Path(cfg["benchmark_dir"]) / f"phase6_retrieval_{split}.jsonl")]
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
    smoke, contract = reports["smoke"], reports["provider_contract"]
    try:
        from campusai.retrieval.cross_encoder_provider import ModelIdentity
        identity = ModelIdentity(**smoke["model_identity"])
        bind(3, smoke, "model_identity_sha256", identity.fingerprint)
    except (KeyError, TypeError, ValueError):
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
            from evaluation.calibrate_hard_query_route import route_metrics
            actual = route_metrics(part["samples"], route["easy_confidence_threshold"], route["easy_margin_threshold"],
                                   route.get("minimum_agreement", 0), route.get("constraint_threshold", 0))
            check(4, all(part.get(key) == value for key, value in actual.items()), f"route_{split}_recomputed_gate")
            if split == "dev":
                check(4, route.get("routing_metrics") == actual, "route_dev_calibration_metrics_gate")
            labels = {r["qid"]: r["difficulty"] for r in rows_at(Path(cfg["benchmark_dir"]) / f"human_retrieval_{split}.jsonl")}
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
    trials = sensitivity.get("trials", [])
    check(5, isinstance(trials, list) and {8, 10, 12, 16, 20} <= {p.get("rerank_cap") for p in trials if isinstance(p, dict)}
          and sensitivity.get("calibration_split") == "dev" and sensitivity.get("test_used") is False
          and sensitivity.get("holdout_used") is False, "reranker_sensitivity_gate")
    for key in ("fallback_rate", "timeout_rate", "invalid_score_rate"):
        check(5, 0 <= num(calibration.get(key)) <= 1, f"calibration_{key}_gate")
    check(5, calibration.get("invalid_score_rate") == 0, "calibration_invalid_scores_gate")
    try:
        from evaluation.calibrate_reranker_scores import _quality
        observed = calibration["calibration_observations"]
        rows = rows_at(Path(cfg["benchmark_dir"]) / "human_retrieval_dev.jsonl")
        outputs = dict(observed["baseline"])
        check(5, set(outputs) == {row["qid"] for row in rows} and set(observed["proposals"]) <= set(outputs), "calibration_pair_identity_gate")
        for qid, proposal in observed["proposals"].items():
            if proposal["top_score"] >= calibration["threshold"] and proposal["margin"] >= calibration["margin_threshold"]:
                outputs[qid] = proposal["results"]
        actual = _quality(rows, outputs)
        check(5, abs(actual["answerable_recall_at_5"] - calibration["recall"]) < 1e-9
              and actual["negative_fpr"] == calibration["false_positive_rate"], "calibration_recomputed_gate")
        for trial in trials:
            relative = Path(trial["artifact"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("invalid sensitivity artifact path")
            bind(5, trial, "artifact_sha256", file_hash(Path(cfg["sensitivity"]).parent / relative))
    except (ValueError, KeyError, TypeError, OSError):
        problems[5].append("calibration_evidence_gate")
    quality = reports["quality"]
    try:
        from evaluation.freeze_human_benchmark import frozen_evidence
        from evaluation.compare_retrieval_quality import compare_split, quality_errors
        evidence = frozen_evidence(Path(cfg["index_dir"])) if quality else {}
        docs = json.loads((Path(cfg["index_dir"]) / "manifest.json").read_text(encoding="utf-8"))["documents"] if quality else []
        recomputed = {}
        for split in ("test", "holdout", "human_test", "human_holdout"):
            path = Path(cfg["benchmark_dir"]) / (f"human_retrieval_{split.removeprefix('human_')}.jsonl" if split.startswith("human_") else f"phase6_retrieval_{split}.jsonl")
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
    ram = cfg["deployment_ram_bytes"] or budget.get("deployment_ram_bytes")
    peak = num(performance.get("peak_rss_bytes"), 0)
    check(7, num(ram, 0) > 0 and peak > 0 and peak <= .75 * num(ram, 0), "deployment_ram_headroom_gate")
    try:
        from evaluation.measure_reranker_capacity import summarize_samples
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
            actual = summarize_samples(profile["samples"])
            check(7, actual == profile.get("summary") and actual["requests"] >= 100 and actual["errors"] == 0,
                  "capacity_recomputed_gate")
        release_cap = calibration.get("rerank_candidate_cap")
        serving_profiles = [p for p in matrix if p.get("rerank_cap") == release_cap]
        check(7, capacity.get("release_rerank_cap") == release_cap
              and capacity.get("deployment_device") == obj(smoke.get("model_identity")).get("device")
              and {1, 5, 20} <= {p.get("concurrency") for p in serving_profiles}, "capacity_deployment_profile_gate")
        for profile in serving_profiles:
            metrics = summarize_samples(profile["samples"])
            check(7, metrics["hard_p95_ms"] <= 1000 and metrics["hard_p99_ms"] <= 2000
                  and metrics["timeout_rate"] <= .005, "capacity_deployment_latency_gate")
        if str(obj(smoke.get("model_identity")).get("device", "")).startswith("cuda"):
            check(7, (20, 5) in {(p.get("rerank_cap"), p.get("concurrency")) for p in matrix}, "capacity_gpu_matrix_gate")
    except (ValueError, KeyError, TypeError):
        problems[7].append("capacity_evidence_gate")
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
        from evaluation.evaluate_reranker_security import CATEGORIES
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
    except (ValueError, KeyError, TypeError, OSError):
        problems[8].append("security_evidence_gate")
    check(8, reports["grounding"].get("phase4_5_regression") == "pass" and bool(reports["grounding"].get("checks")), "grounding_regression_gate")
    check(8, all(value is True for value in obj(reports["grounding"].get("checks")).values()), "grounding_checks_gate")
    checks = obj(reports["failure_matrix"].get("checks"))
    check(9, FAILURES <= set(checks) and all(checks.get(key) is True for key in FAILURES), "failure_matrix_gate")
    for gate, name, required in ((3, "provider_contract", PROVIDER_CASES), (9, "failure_matrix", FAILURES)):
        observed = reports[name].get("observations", [])
        check(gate, isinstance(observed, list) and bool(observed)
              and all(isinstance(row, dict) and row.get("passed") is True and row.get("error_type") is None for row in observed)
              and reports[name].get("evidence_type") == "controlled_fault_injection", f"{name}_evidence_gate")
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
        from evaluation.audit_canary_staging import audit_staging
        actual = audit_staging(staging, {"exercises": staging["fault_exercises"]})
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
            for key, expected in (("source_sha256", source["source_sha256"]), ("index_sha256", base.get("index_sha256")),
                                  ("phase6_calibration_sha256", base.get("calibration_sha256")),
                                  ("model_identity_sha256", smoke.get("model_identity_sha256"))):
                bind(gate, report, key, expected)
            if gate >= 6:
                bind(gate, report, "calibration_sha256", file_hash(cfg["calibration"]))
    try:
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        dirty = True
    check(12, not dirty, "working_tree_dirty")
    hashes = {name: file_hash(cfg[name]) for name in ARTIFACTS}
    check(12, all(is_hash(value) for value in hashes.values()), "release_artifact_hash_gate")
    gates, prior_failed = {}, False
    for index in range(13):
        absent = any(name in missing for name in GATE_ARTIFACTS[index])
        evidence_status = "BLOCKED" if absent else "FAIL" if problems[index] else "PASS"
        status = "BLOCKED" if prior_failed else evidence_status
        gates[f"M{index}"] = {"status": status, "evidence_status": evidence_status, "owner": OWNERS[index],
                             "errors": sorted(set(problems[index])), "requires": [f"M{index-1}"] if index else [],
                             "artifacts": [ARTIFACTS[name] for name in GATE_ARTIFACTS[index]],
                             "verify_command": f"python -m evaluation.validate_reranker_release --through M{index}"}
        prior_failed |= status != "PASS"
    through = int(cfg["through"][1:])
    errors = sorted({error for index in range(through + 1) for error in problems[index]})
    passed = all(gates[f"M{index}"]["status"] == "PASS" for index in range(through + 1))
    return {"schema_version": 2, "phase": 7, "status": "pass" if passed else "conditional",
            "score": 10.0 if passed and through == 12 else None, "errors": errors, "gates": gates,
            "through": cfg["through"], **source, "working_tree_clean": not dirty, "base_release": "phase6-rc3",
            "baseline_commit": base.get("commit"), "model_identity_sha256": smoke.get("model_identity_sha256"),
            "index_sha256": base.get("index_sha256"), "calibration_sha256": file_hash(cfg["calibration"]),
            "artifact_sha256": hashes, "deployment_ram_bytes": ram}
