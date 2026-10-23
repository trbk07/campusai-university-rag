"""Release evidence must remain bound to the measured and reviewed inputs."""
from argparse import Namespace
from copy import deepcopy
import inspect
import json
from pathlib import Path

import pytest

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.context import benchmark_request
from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.common import release_artifacts
from evaluation.reranker.paired_answer_quality import (
    answer_digest, evaluate_answer_observations, main as answer_report_main,
)
from evaluation.reranker.supplemental_gates import ANSWER_BINDINGS, answer_errors, context_errors
from evaluation.reranker import validate_reranker_release as release
from tests.test_phase7_completion_contract import paired_answers


def test_source_identity_hashes_physical_code_and_ignores_stale_candidate_report(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    source = root / "src" / "campusai" / "service.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 1\n", encoding="utf-8")
    results = root / "evaluation" / "results"
    results.mkdir(parents=True)
    write_json(results / "candidate_coverage.json", {"source_sha256": "a" * 64})
    monkeypatch.setattr(release_artifacts.subprocess, "check_output", lambda *args, **kwargs: "fixture-commit")
    first = release_artifacts.source_identity(root)
    write_json(results / "candidate_coverage.json", {"source_sha256": "b" * 64})
    assert release_artifacts.source_identity(root) == first
    source.write_text("value = 2\n", encoding="utf-8")
    second = release_artifacts.source_identity(root)
    assert second["source_sha256"] != first["source_sha256"]
    assert second["runtime_sha256"] == first["runtime_sha256"]


@pytest.mark.parametrize("mutation", ["gold_on_abstention", "partial_gold", "contradictory_support", "affirmative_abstention"])
def test_semantic_review_cannot_inflate_metrics_with_contradictory_verdicts(mutation):
    rows = paired_answers()
    row = rows[1]
    if mutation == "gold_on_abstention":
        row["answer"] = deepcopy(rows[3]["answer"])
        row["review"].update(answer_sha256=answer_digest(row["answer"]), claims=[])
    elif mutation == "partial_gold":
        row["review"]["covered_gold_claim_ids"] = []
    elif mutation == "contradictory_support":
        row["review"]["claims"][0]["supported"] = False
    else:
        rows[3]["review"]["unsupported_affirmative_answer"] = True
    with pytest.raises(ValueError):
        evaluate_answer_observations(rows)


def answer_fixture(tmp_path):
    from evaluation.reranker.check_reranker_faults import fixture_retriever
    retriever, provider, *_ = fixture_retriever(tmp_path / "fixture")
    provider.close()
    benchmark = tmp_path / "benchmark"
    benchmark.mkdir()
    cfg = {"index_dir": retriever.index_root, "benchmark_dir": benchmark,
           "answers": tmp_path / "answers_report.json"}
    policy_path = benchmark / "phase7_review_policy.json"
    write_json(policy_path, {"schema_version": 1, "owner_self_review_allowed": False,
                            "owner_semantic_review_allowed": False, "allow_independent_review": True})
    rows = paired_answers()
    records = []
    for split in ("human_test", "human_holdout"):
        selected = [row for row in rows if row["split"] == split]
        for row in selected:
            row["qid"] = split + "_" + row["qid"]
            record = {"qid": row["qid"], "question": "What is the tuition policy?", "author": row["author"],
                      "answerable": row["answerable"], "tags": [], "doc_ids": ["doc"], "split": split.removeprefix("human_")}
            if row["arm"] == "baseline":
                records.append(record)
            request = benchmark_request(record, ["doc", "other"])
            row.update(request=request, request_sha256=digest_record(request), record_sha256=digest_record(record), tags=[],
                       llm_calls=[{"cached": False}] if row["answerable"] else [])
            if row["answerable"]:
                row["answer"]["citations"][0].update(chunk_id="c0", quote="tuition policy fees student semester 0 MAI101")
                row["answer"]["claims"][0]["citation_ids"] = ["c0"]
                row["review"]["claims"][0]["citations"][0]["chunk_id"] = "c0"
            row["review"]["answer_sha256"] = answer_digest(row["answer"])
        path = benchmark / f"human_retrieval_{split.removeprefix('human_')}.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in records if row["split"] == split.removeprefix("human_")), encoding="utf-8")
    (benchmark / "human_retrieval.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    (benchmark / "human_retrieval_dev.jsonl").write_text("", encoding="utf-8")
    for name in ("phase6_calibration", "calibration", "route"):
        cfg[name] = tmp_path / (name + ".json")
        write_json(cfg[name], {"fixture": name})
    rubric_path = tmp_path / "rubric.json"
    write_json(rubric_path, {"status": "approved", "reviewer": "researcher-b", "reviewer_role": "independent_reviewer",
                            "gold_claim_ids": {row["qid"]: row["gold_claim_ids"] for row in rows}})
    protocol = {"schema_version": 1, "status": "frozen", "rubric_sha256": sha256(rubric_path),
                "llm_config_sha256": "a" * 64, "llm_identity": {"model": "fixture"},
                "prompt_sha256": sha256(inspect.getfile(GroundedAnswerGenerator)), "context_budget": {"max_chars": 12000},
                "review_policy_sha256": sha256(policy_path)}
    write_json(tmp_path / "reranker_answer_protocol.json", protocol)
    bindings = {name: "b" * 64 for name in ANSWER_BINDINGS}
    bindings.update(index_sha256=sha256(cfg["index_dir"] / "manifest.json"),
                    phase6_calibration_sha256=sha256(cfg["phase6_calibration"]), calibration_sha256=sha256(cfg["calibration"]),
                    route_calibration_sha256=sha256(cfg["route"]), training_split_sha256=sha256(benchmark / "human_retrieval_dev.jsonl"),
                    human_benchmark_sha256=sha256(benchmark / "human_retrieval.jsonl"),
                    review_policy_sha256=sha256(policy_path))
    for row in rows:
        row["rubric_sha256"] = protocol["rubric_sha256"]
    raw_path = tmp_path / "raw_answers.json"
    raw = {**bindings, **protocol, "observations": rows, "live_provider": True,
           "answer_cache_enabled": False, "llm_cache_enabled": False}
    write_json(raw_path, raw)
    report = {**bindings, **protocol, "metrics": evaluate_answer_observations(rows),
              "raw": {"path": raw_path.name, "sha256": sha256(raw_path)},
              "rubric": {"path": rubric_path.name, "sha256": sha256(rubric_path)}}
    return cfg, report, raw_path


def test_answer_raw_identity_is_checked_even_when_metrics_and_archive_hash_are_valid(tmp_path):
    cfg, report, raw_path = answer_fixture(tmp_path)
    assert answer_errors(report, cfg) == []
    raw = read_json(raw_path)
    raw["source_sha256"] = "d" * 64
    write_json(raw_path, raw)
    report["raw"]["sha256"] = sha256(raw_path)
    assert "answer_raw_source_sha256_binding" in answer_errors(report, cfg)


@pytest.mark.parametrize("field,error", [("rubric_sha256", "answer_protocol_rubric_binding"),
                                         ("prompt_sha256", "answer_protocol_prompt_binding")])
def test_protocol_cannot_claim_a_different_rubric_or_prompt(tmp_path, field, error):
    cfg, report, raw_path = answer_fixture(tmp_path)
    protocol_path = tmp_path / "reranker_answer_protocol.json"
    protocol = read_json(protocol_path)
    protocol[field] = report[field] = "d" * 64
    write_json(protocol_path, protocol)
    raw = read_json(raw_path)
    raw[field] = protocol[field]
    write_json(raw_path, raw)
    report["raw"]["sha256"] = sha256(raw_path)
    assert error in answer_errors(report, cfg)


def test_answer_report_rejects_output_overwriting_its_raw_input(tmp_path):
    raw = tmp_path / "raw.json"
    raw.write_bytes(b"original observations")
    with pytest.raises(SystemExit):
        answer_report_main(["--observations", str(raw), "--output", str(raw),
                            "--bindings", str(tmp_path / "bindings.json"), "--rubric", str(tmp_path / "rubric.json")])
    assert raw.read_bytes() == b"original observations"


def test_context_gate_requires_explicit_source_leakage_observations():
    key = {"question": "Credits?", "language": "en", "doc_ids": None, "filters": {}, "top_k": 5,
           "mode": "auto", "corpus_version": "fixture", "model": "fixture", "context_budget": {}}
    cases = [{"case": name, "request": {"question": "Credits?"}, "resolved": "Credits?", "clarification": True,
              "out_of_scope_citations": 0, "unverified_selection_citations": 0}
             for name in ("different_history", "different_selection", "empty_scope", "missing_history", "selection_not_evidence")]
    lifecycle = {"startup_loads": 1, "request_loads": 0, "request_inference_calls": 1, "closed_new_inference": 0,
                 "warm_failure_new_inference": 0, "pending_after_drain": 0, "active_after_drain": 0,
                 "warm_failure_phase6": [], "baseline_phase6": []}
    report = {"observations": {"context_cases": cases, "lifecycle": lifecycle, "cache_probes": [
        {"case": "history", "before": key, "after": {**key, "request_context": {"history": ["a"]}}},
        {"case": "selection", "before": key, "after": {**key, "request_context": {"selection": "a"}}},
        {"case": "scope", "before": key, "after": {**key, "doc_ids": []}},
    ]}}
    assert context_errors(report) == []
    cases[0].pop("out_of_scope_citations")
    assert "context_source_observations_required" in context_errors(report)


def manifest_fixture(tmp_path):
    args = Namespace(**{name: tmp_path / filename for name, filename in release.ALL_ARTIFACTS.items()},
                     phase6_calibration=tmp_path / "phase6.json",
                     answer_protocol=tmp_path / "reranker_answer_protocol.json")
    args.index_dir = tmp_path / "index"
    args.index_dir.mkdir()
    write_json(args.index_dir / "manifest.json", {"fixture": True})
    for name, path in vars(args).items():
        if name != "index_dir" and isinstance(path, Path):
            write_json(path, {})
    write_json(args.smoke, {"model_identity": {"model_name": "fixture", "model_revision": "revision",
                                              "model_sha256": "a" * 64, "tokenizer_revision": "revision", "device": "cpu",
                                              "dtype": "float32"}})
    write_json(args.calibration, {"rerank_candidate_cap": 8})
    write_json(args.baseline, {"benchmark_sha256": {}})
    write_json(args.performance, {"resource_limits": {}})
    write_json(args.human_manifest, {"dataset_sha256": "b" * 64})
    report = {"status": "pass", "score": 10., "through": "M12", "working_tree_clean": True,
              "all_release_gates_pass": True, "gates": {f"M{i}": {"status": "PASS", "artifacts": []} for i in range(13)},
              "supplemental_gates": {f"S{i}": {"status": "PASS"} for i in range(1, 7)},
              "artifact_sha256": {name: sha256(getattr(args, name)) for name in release.ALL_ARTIFACTS}}
    return args, report


def test_manifest_packaging_rechecks_inputs_and_does_not_mutate_validated_report(tmp_path, monkeypatch):
    args, report = manifest_fixture(tmp_path)
    before = deepcopy(report)
    monkeypatch.setattr(release, "validate", lambda args: deepcopy(before))
    manifest = release.build_manifest(args, report)
    assert report == before
    assert manifest["gates"]["M0"]["artifact_sha256"] == {}
    monkeypatch.setattr(release, "validate", lambda args: {**before, "status": "conditional", "score": None})
    with pytest.raises(ValueError, match="changed after validation"):
        release.build_manifest(args, report)


def test_manifest_rejects_missing_gate_even_when_summary_claims_ten_out_of_ten(tmp_path):
    args, report = manifest_fixture(tmp_path)
    report["gates"].pop("M6")
    with pytest.raises(ValueError, match="all M0-M12"):
        release.build_manifest(args, report)
