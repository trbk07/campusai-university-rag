"""Mandatory S1-S6 acceptance, recomputed from bound raw observations.

Reports never substitute a scalar PASS for reviews, paired evidence or probes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path, PureWindowsPath

from evaluation.common.release_artifacts import read_json, sha256
from evaluation.common.artifact_store import resolve_artifact

SUPPLEMENTAL = {
    "S1": (1, "lineage", "reranker_lineage.json"),
    "S2": (3, "context", "reranker_context_lifecycle.json"),
    "S3": (6, "statistics", "reranker_group_statistics.json"),
    "S4": (6, "answers", "reranker_answer_quality.json"),
    "S5": (6, "evidence", "reranker_complete_evidence.json"),
    "S6": (7, "observability", "reranker_observability.json"),
}
PRIMARY_SPLITS = ("human_test", "human_holdout")
MIN_INDEPENDENT_GROUPS = 10
ANSWER_BINDINGS = ("source_sha256", "runtime_sha256", "index_sha256", "model_identity_sha256",
                   "phase6_calibration_sha256", "calibration_sha256", "route_calibration_sha256",
                   "training_split_sha256", "human_benchmark_sha256", "review_policy_sha256")


def raw_reference(base: Path, reference: dict) -> Path:
    name = reference["path"]
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or PureWindowsPath(name).drive or PureWindowsPath(name).root or ".." in PureWindowsPath(name).parts
            or ".." in Path(name).parts):
        raise ValueError("unsafe raw artifact reference")
    target = (base / name).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError("unsafe raw artifact reference")
    target = resolve_artifact(target)
    if sha256(target) != reference["sha256"]:
        raise ValueError("missing or changed raw artifact")
    return target


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite numeric observation required")
    return value


def review_audit_errors(rows: list[dict], audit: list[dict], index_dir: Path,
                        *, owner_identity: str | None = None,
                        owner_confirmation: dict | None = None,
                        confirmed_sources: list[dict] | None = None,
                        generation_authorization: dict | None = None,
                        generated_records: dict[str, dict] | None = None,
                        delegation=None) -> list[str]:
    """Check intake packets before freeze and again against published canonical bytes."""
    from evaluation.benchmarks.human_benchmark_intake import digest_record, validate_review
    if (not isinstance(audit, list) or any(not isinstance(item, dict) for item in audit)
            or any(not isinstance(item.get("qid"), str) for item in audit)):
        return ["review_audit_coverage"]
    by_qid = {item["qid"]: item for item in audit}
    if (len(audit) != len(rows) or len(by_qid) != len(audit)
            or set(by_qid) != {row["qid"] for row in rows}):
        return ["review_audit_coverage"]
    errors = []
    sources = {row["qid"]: row for row in (confirmed_sources or [])}
    if owner_confirmation and owner_confirmation.get("dev_metadata_revision") is not None:
        from evaluation.benchmarks.difficulty_audit import revision_errors
        from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
        try:
            errors.extend(revision_errors(owner_confirmation, confirmed_sources or [], frozen_evidence(index_dir),
                                          sha256(index_dir / "manifest.json")))
        except (ValueError, KeyError, TypeError, OSError):
            errors.append("invalid_dev_metadata_revision")
    for row in rows:
        item = by_qid[row["qid"]]
        if item.get('review_evidence_kind') == 'validated_dev_inheritance':
            from evaluation.benchmarks.dev_inheritance import inheritance_review_error
            if (not owner_identity or not generation_authorization
                    or generation_authorization.get('owner_identity') != owner_identity
                    or inheritance_review_error(row, item, generation_authorization)):
                errors.append('invalid_dev_inheritance:' + row['qid'])
            continue
        if item.get("review_evidence_kind") == "owner_directed_generation":
            from evaluation.benchmarks.source_course_generation import export_matches
            expected = (generated_records or {}).get(row["qid"])
            if (not generation_authorization or not expected or not owner_identity
                    or generation_authorization.get("owner_identity") != owner_identity
                    or item.get("generation_authorization_sha256") != expected.get('generation_authorization_sha256')
                    or expected.get('generation_authorization_sha256') not in {
                        digest_record({k: v for k, v in generation_authorization.items()
                                       if k not in {'_validated_dev_authorization','_validated_dev_inheritance'}}),
                        digest_record(generation_authorization.get('_validated_dev_authorization', {}))}
                    or item.get("exported_record_sha256") != digest_record(expected)
                    or not export_matches(expected, row)):
                errors.append("invalid_owner_generation:" + row["qid"])
            continue
        if item.get("review_evidence_kind") == "owner_dataset_confirmation":
            from evaluation.benchmarks.owner_review import confirmed_row
            source = sources.get(row["qid"])
            if (not owner_confirmation or not source or not owner_identity
                    or owner_confirmation.get("owner_identity") != owner_identity
                    or item.get("owner_confirmation_sha256") != digest_record(owner_confirmation)
                    or item.get("source_record_sha256") != digest_record(source)):
                errors.append("invalid_owner_confirmation:" + row["qid"])
                continue
            expected = confirmed_row(source, owner_confirmation)
            exported_hash = digest_record(expected)
            expected["split"] = row["split"]
            if expected != row or item.get("exported_record_sha256") != exported_hash:
                errors.append("reviewed_content_changed:" + row["qid"])
            continue
        try:
            question, review = item["question_packet"], item["review_packet"]
            validate_review(question, review, index_dir, owner_identity=owner_identity,
                            delegation=delegation)
            if review["review_status"] != "approved":
                raise ValueError("canonical record is not approved")
            expected = {**question["record"], **{key: review[key] for key in
                                                ("reviewer", "reviewer_role", "review_status", "review_checks")},
                        "reviewed_at": review["reviewed_at"]}
            if review['reviewer_role'] == 'owner_delegated_ai':
                from evaluation.benchmarks.delegated_review import DELEGATED_FIELDS
                expected.update({key: review[key] for key in DELEGATED_FIELDS})
            # Split allocation must preserve every reviewed semantic field.
            exported = {**expected, "split": question["record"]["split"]}
            expected["split"] = row["split"]
            if expected != row or item["exported_record_sha256"] != digest_record(exported):
                errors.append("reviewed_content_changed:" + row["qid"])
        except (ValueError, KeyError, TypeError, AttributeError):
            errors.append("invalid_review_packet:" + row["qid"])
    return errors


def lineage_errors(report: dict, cfg: dict) -> list[str]:
    from evaluation.benchmarks.connected_groups import connected_groups
    benchmark = Path(cfg["benchmark_dir"])
    dataset = benchmark / "human_retrieval.jsonl"
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    groups = connected_groups(rows)
    raw = report["observations"]
    audit_path = raw_reference(Path(cfg["lineage"]).parent, raw["review_audit"])
    audit = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    policy_path = benchmark / "phase7_review_policy.json"
    policy = read_json(policy_path) if policy_path.is_file() else {}
    owner_identity = policy.get("owner_identity") if policy.get("owner_self_review_allowed") is True else None
    confirmation, sources = None, None
    confirmation_errors = []
    if any(isinstance(item, dict) and item.get("review_evidence_kind") == "owner_dataset_confirmation" for item in audit):
        from evaluation.benchmarks.owner_review import load_confirmation
        try:
            confirmation, sources = load_confirmation(benchmark)
            if raw.get("owner_confirmation_source_sha256") != sha256(benchmark / "phase7_owner_confirmation.json"):
                confirmation_errors.append("owner_confirmation_observation_binding")
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            confirmation_errors.append("owner_confirmation_invalid_or_unbound")
    from evaluation.benchmarks.owner_generation import load_generation
    authorization, generated = load_generation(benchmark, Path(cfg["index_dir"]))
    if authorization and raw.get("generation_authorization_source_sha256") != sha256(benchmark / "phase7_generation_authorization.json"):
        confirmation_errors.append("generation_authorization_observation_binding")
    dev_auth = benchmark/'phase7_dev_generation_authorization.json'
    if dev_auth.exists() and raw.get('dev_generation_authorization_source_sha256') != sha256(dev_auth):
        confirmation_errors.append('dev_generation_authorization_observation_binding')
    from evaluation.benchmarks.delegated_review import load_delegation
    delegation = load_delegation(policy, root=Path(__file__).resolve().parents[2],
                                 index_sha256=sha256(Path(cfg['index_dir']) / 'manifest.json'), scope='dataset')
    errors = confirmation_errors + review_audit_errors(
        rows, audit, Path(cfg["index_dir"]), owner_identity=owner_identity,
        owner_confirmation=confirmation, confirmed_sources=sources,
        generation_authorization=authorization, generated_records=generated, delegation=delegation)
    if (not policy or raw.get("review_policy_sha256") != sha256(policy_path)
            or policy.get("allow_independent_review") is not True):
        errors.append("review_policy_missing_or_unbound")
    # An assigned split says nothing about historical exposure. Bind every
    # decision to the separately audited source registry instead of deriving
    # "unexposed" from membership in test/holdout.
    source_registry_path = benchmark / "phase7_exposure_registry.json"
    source_registry = read_json(source_registry_path)
    source_rows = source_registry.get("records")
    source_records_valid = isinstance(source_rows, list)
    if not source_records_valid:
        source_rows = []
    source_lineage_path = benchmark / "human_candidate_lineage.json"
    source_lineage = read_json(source_lineage_path)
    source_groups = source_lineage.get("connected_groups", {})
    source_by_qid = {entry.get("qid"): entry for entry in source_rows if isinstance(entry, dict)}
    registry_status = source_registry.get("status")
    registry_bound = (
        registry_status in {"pass", "pending_complete_history_audit"}
        and source_registry.get("dataset_sha256") == sha256(benchmark / "human_candidate_pool.jsonl")
        and source_registry.get("lineage_sha256") == sha256(source_lineage_path)
        and source_registry.get("index_sha256") == sha256(Path(cfg["index_dir"]) / "manifest.json")
        and len(source_by_qid) == len(rows)
        and set(source_by_qid) == set(groups)
        and source_records_valid
    )
    if not registry_bound:
        errors.append("exposure_history_registry_unbound")
    elif registry_status != "pass":
        errors.append("exposure_history_audit_incomplete")
    observed_registry = raw.get("exposure_registry")
    if (not isinstance(observed_registry, list) or len(observed_registry) != len(rows)
            or raw.get("exposure_registry_source_sha256") != sha256(source_registry_path)):
        errors.append("exposure_observation_source_binding")
        observed_by_qid = {}
    else:
        observed_by_qid = {entry.get("qid"): entry for entry in observed_registry if isinstance(entry, dict)}
        if len(observed_by_qid) != len(rows) or set(observed_by_qid) != set(groups):
            errors.append("exposure_coverage")
    split_by_source_group = {}
    source_group_exposure = {}
    for row in rows:
        qid = row["qid"]
        history = source_by_qid.get(qid, {})
        group = history.get("connected_group")
        if not group or source_groups.get(qid) != group:
            errors.append("exposure_group_binding:" + qid)
        split_by_source_group.setdefault(group, set()).add(row["split"])
        source_group_exposure.setdefault(group, []).append(history)
        observed = observed_by_qid.get(qid, {})
        if (observed.get("status") != history.get("status")
                or observed.get("connected_group") != group
                or observed.get("heldout_eligible") != history.get("heldout_eligible")):
            errors.append("exposure_observation_mismatch:" + qid)
        if history.get("status") == "unknown_pending_history_audit":
            if row["split"] != "dev" or history.get("heldout_eligible") is not False:
                errors.append("heldout_exposure_unresolved:" + qid)
        elif isinstance(history.get("status"), str) and history["status"].startswith("known_exposed"):
            if row["split"] != "dev" or history.get("heldout_eligible") is not False:
                errors.append("known_exposure_not_dev_only:" + qid)
        elif history.get("status") == "unexposed_audited":
            audit = history.get("history_audit")
            if (history.get("heldout_eligible") is not True or not isinstance(audit, dict)
                    or audit.get("complete") is not True or not audit.get("archive_reference")
                    or not isinstance(audit.get("archive_sha256"), str)
                    or len(audit["archive_sha256"]) != 64 or not audit.get("study_manifest_sha256")):
                errors.append("unexposed_history_audit_proof_missing:" + qid)
        else:
            errors.append("invalid_exposure_status:" + qid)
    for group, members in source_group_exposure.items():
        if any(item.get("status") != "unexposed_audited" for item in members):
            if split_by_source_group[group] != {"dev"}:
                errors.append("ineligible_exposure_group_not_dev:" + str(group))
    if any(len(splits) > 1 for splits in split_by_source_group.values()):
        errors.append("connected_family_leakage")
    if report["dataset_sha256"] != sha256(dataset):
        errors.append("lineage_dataset_binding")
    return errors


def context_errors(report: dict) -> list[str]:
    from campusai.rag.context import resolve_query
    observations = report["observations"]
    if observations.get("schema_version") == 2:
        from evaluation.reranker.collect_context_lifecycle import lifecycle_summary
        if observations.get("evidence_type") != "physical_dev_context_lifecycle":
            return ["context_measurement_kind"]
        binding_errors = ["context_measurement_binding:" + key for key in
                          ("source_sha256", "runtime_sha256", "model_identity_sha256", "index_sha256")
                          if observations.get(key) != report.get(key)]
        if lifecycle_summary(observations["lifecycle_proof"]) != observations["lifecycle"]:
            binding_errors.append("lifecycle_counter_replay")
        if binding_errors:
            return binding_errors
    required = {"different_history", "different_selection", "empty_scope", "missing_history", "selection_not_evidence"}
    cases = observations["context_cases"]
    errors = []
    if not required <= {case["case"] for case in cases}:
        errors.append("context_case_coverage")
    for case in cases:
        if case.get("answer", {}).get("reason") in {"llm_error", "llm_not_configured"}:
            errors.append("context_live_grounding_failed:" + case["case"])
        if observations.get("schema_version") == 2:
            citations = case["answer"]["citations"]
            retrieved = {(item["doc_id"], item["chunk_id"], item["page"]) for item in case["retrieved"]}
            out_of_scope = sum(item["doc_id"] not in case["doc_ids"] for item in citations)
            unverified = sum((item["doc_id"], item["chunk_id"], item["page"]) not in retrieved for item in citations)
            if (out_of_scope != case["out_of_scope_citations"]
                    or unverified != case["unverified_selection_citations"]):
                errors.append("context_citation_counter_replay:" + case["case"])
        resolved = resolve_query(**case["request"])
        if resolved.resolved != case["resolved"] or resolved.needs_clarification != case["clarification"]:
            errors.append("context_replay:" + case["case"])
        counts = (case.get("out_of_scope_citations"), case.get("unverified_selection_citations"))
        if any(type(count) is not int or count < 0 for count in counts):
            errors.append("context_source_observations_required")
        elif any(counts):
            errors.append("context_source_leakage")
    # Cache probes carry complete key inputs; recompute instead of trusting a
    # declared "different" flag or arbitrary opaque keys.
    from campusai.rag.cache import build_rag_cache_key
    probes = observations["cache_probes"]
    if not {"history", "selection", "scope"} <= {probe["case"] for probe in probes}:
        errors.append("context_cache_probe_coverage")
    for probe in probes:
        if build_rag_cache_key(**probe["before"]) == build_rag_cache_key(**probe["after"]):
            errors.append("context_cache_collision:" + probe["case"])
        if observations.get("schema_version") == 2 and probe["keys"] != [
                build_rag_cache_key(**probe[name]) for name in ("before", "after")]:
            errors.append("context_cache_key_replay:" + probe["case"])
    lifecycle = observations["lifecycle"]
    integer_fields = ("startup_loads", "request_loads", "request_inference_calls", "closed_new_inference",
                      "warm_failure_new_inference", "pending_after_drain", "active_after_drain")
    if any(type(lifecycle.get(field)) is not int or lifecycle[field] < 0 for field in integer_fields):
        errors.append("non_integer_lifecycle_observation")
    if (lifecycle["startup_loads"] != 1 or lifecycle["request_loads"] != 0
            or lifecycle["request_inference_calls"] < 1 or lifecycle["closed_new_inference"] != 0
            or lifecycle["warm_failure_new_inference"] != 0 or lifecycle["pending_after_drain"] != 0
            or lifecycle["active_after_drain"] != 0 or lifecycle["warm_failure_phase6"] != lifecycle["baseline_phase6"]):
        errors.append("lifecycle_invariant")
    return errors


def statistics_errors(quality: dict) -> list[str]:
    errors = []
    for split in PRIMARY_SPLITS:
        metrics = quality[split]["paired_statistics"]["mrr"]
        if (metrics["sampling_unit"] != "connected_group" or metrics["bootstrap_resamples"] < 10000
                or metrics["independent_groups"] < MIN_INDEPENDENT_GROUPS):
            errors.append(split + ":insufficient_independent_groups")
        if split.endswith("test") and metrics["ci95"][0] <= 0:
            errors.append(split + ":group_mrr_significance")
    return errors


def complete_evidence_errors(quality: dict) -> list[str]:
    errors = []
    for split in PRIMARY_SPLITS:
        pairs = [item for item in quality[split]["per_query"] if item["answerable"]]
        hard = [item for item in pairs if item["difficulty"] == "hard" or "multi_hop" in item["tags"]]
        subsets = [("overall", pairs), ("hard_multi_hop", hard)]
        for tag in ('multi_hop', 'table', 'exact_code', 'contextual'):
            tagged = [item for item in pairs if tag in item['tags']]
            if tagged:
                subsets.append((tag, tagged))
        for name, subset in subsets:
            if not subset:
                errors.append(split + ":missing_" + name)
            elif sum(item["delta"]["all_gold_recall5"] for item in subset) < -1e-12:
                errors.append(split + ":all_gold_regression_" + name)
    return errors


def answer_errors(report: dict, cfg: dict) -> list[str]:
    from evaluation.reranker.paired_answer_quality import evaluate_answer_observations, answer_quality_errors
    from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
    from evaluation.benchmarks.human_benchmark_intake import digest_record
    from campusai.rag.grounding import validate_quote
    from campusai.rag.context import benchmark_request
    from evaluation.benchmarks.freeze_human_benchmark import PLACEHOLDER_IDENTITIES
    raw = read_json(raw_reference(Path(cfg["answers"]).parent, report["raw"]))
    protocol = read_json(Path(cfg["answers"]).parent / "reranker_answer_protocol.json")
    protocol_errors = ["answer_protocol_binding:" + field for field in
                       ("rubric_sha256", "llm_config_sha256", "llm_identity", "prompt_sha256", "context_budget",
                        "review_policy_sha256")
                       if field not in protocol or raw.get(field) != protocol[field] or report.get(field) != protocol[field]]
    rubric_path = raw_reference(Path(cfg["answers"]).parent, report["rubric"])
    rubric = read_json(rubric_path)
    if protocol.get("schema_version") != 1 or protocol.get("status") != "frozen":
        protocol_errors.append("answer_protocol_not_frozen")
    if protocol.get("rubric_sha256") != sha256(rubric_path):
        protocol_errors.append("answer_protocol_rubric_binding")
    from campusai.rag.grounding import GroundedAnswerGenerator
    import inspect
    if protocol.get("prompt_sha256") != sha256(Path(inspect.getfile(GroundedAnswerGenerator))):
        protocol_errors.append("answer_protocol_prompt_binding")
    policy_path = Path(cfg["benchmark_dir"]) / "phase7_review_policy.json"
    policy = read_json(policy_path) if policy_path.is_file() else {}
    owner_identity = (policy.get("owner_identity")
                      if policy.get("owner_self_review_allowed") is True
                      and policy.get("owner_semantic_review_allowed") is True else None)
    if (not policy or policy.get("allow_independent_review") is not True
            or report.get("review_policy_sha256") != sha256(policy_path)):
        protocol_errors.append("answer_review_policy_binding")
    from evaluation.benchmarks.human_record_contract import review_role_error
    from evaluation.benchmarks.delegated_review import load_delegation
    delegation = load_delegation(policy, root=Path(__file__).resolve().parents[2],
                                 index_sha256=sha256(Path(cfg['index_dir']) / 'manifest.json'), scope='semantic')
    if (rubric.get("status") != "approved"
            or review_role_error(rubric, owner_identity, delegation=delegation, scope='semantic')):
        return ["answer_rubric_review_required"]
    records = {}
    for split in PRIMARY_SPLITS:
        path = Path(cfg["benchmark_dir"]) / f"human_retrieval_{split.removeprefix('human_')}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                records[(split, row["qid"])] = row
    observed = raw["observations"]
    if {(row["split"], row["qid"], row["arm"]) for row in observed} != {
            (split, qid, arm) for split, qid in records for arm in ("baseline", "phase7")}:
        return ["answer_dataset_coverage"]
    evidence = frozen_evidence(Path(cfg["index_dir"]))
    docs = read_json(Path(cfg['index_dir']) / 'manifest.json')['documents']
    errors = protocol_errors
    expected_bindings = {
        "phase6_calibration_sha256": sha256(cfg["phase6_calibration"]),
        "calibration_sha256": sha256(cfg["calibration"]),
        "route_calibration_sha256": sha256(cfg["route"]),
        "training_split_sha256": sha256(Path(cfg["benchmark_dir"]) / "human_retrieval_dev.jsonl"),
        "human_benchmark_sha256": sha256(Path(cfg["benchmark_dir"]) / "human_retrieval.jsonl"),
    }
    for field in ANSWER_BINDINGS:
        if (not report.get(field) or raw.get(field) != report[field]
                or field in expected_bindings and report[field] != expected_bindings[field]):
            errors.append("answer_raw_" + field + "_binding")
    if raw.get('answer_cache_enabled') is not False or raw.get('llm_cache_enabled') is not False:
        errors.append('answer_caches_not_disabled')
    for item in observed:
        row = records[(item["split"], item["qid"])]
        request = benchmark_request(row, docs)
        if (item["record_sha256"] != digest_record(row) or item["answerable"] != row["answerable"]
                or item["rubric_sha256"] != sha256(rubric_path)
                or item["gold_claim_ids"] != rubric["gold_claim_ids"][row["qid"]]
                or item.get('author') != row['author'] or item.get('tags') != row['tags']
                or item.get('request') != request or item['request_sha256'] != digest_record(request)):
            errors.append("answer_frozen_input_binding")
        calls = item['llm_calls']
        if (not isinstance(calls, list) or not item['answer']['abstained'] and not calls
                or any(call.get('cached') is not False for call in calls)):
            errors.append('answer_live_call_observations')
        for citation in item["answer"]["citations"]:
            frozen = evidence.get((citation["doc_id"], citation["chunk_id"]))
            if (not frozen or citation["doc_id"] not in row["doc_ids"] or citation["page"] != frozen["page"]
                    or not validate_quote(citation["quote"], frozen["content"])
                    or any(str(frozen.get('metadata', {}).get(key, '')).casefold() != str(value).casefold()
                           for key, value in row.get('filters', {}).items())):
                errors.append("answer_citation_provenance")
    if (raw.get("llm_identity") != report.get("llm_identity")
            or not raw.get("llm_identity", {}).get("model") or raw.get("live_provider") is not True
            or not report.get("prompt_sha256") or not report.get("context_budget")):
        errors.append("answer_llm_prompt_context_binding")
    actual = evaluate_answer_observations(raw["observations"], owner_identity=owner_identity,
                                        delegation=delegation)
    if actual != report["metrics"]:
        errors.append("answer_metrics_changed")
    return errors + answer_quality_errors(actual)


def observability_errors(report: dict, reports: dict) -> list[str]:
    errors = []
    observations = report["observations"]
    if not observations.get("environment_id") or observations["device"] != reports["smoke"]["model_identity"]["device"]:
        errors.append("deployment_identity")
    profiles = reports["capacity"]["profiles"]
    from evaluation.reranker.measure_reranker_capacity import successful_throughput
    for profile in profiles:
        actual = successful_throughput(profile["samples"], profile["duration_seconds"])
        if actual != profile["successful_throughput_rps"]:
            errors.append("successful_throughput_changed")
    if not 0 < observations["http_p95_budget_ms"] <= 10000:
        errors.append("http_budget_not_frozen")
    if observations["http_p95_budget_ms"] != reports["http_end_to_end"]["p95_budget_ms"]:
        errors.append("http_budget_binding")
    resources = observations["resource_samples"]
    if len(resources) < 2:
        errors.append("resource_sample_coverage")
    for sample in resources:
        from datetime import datetime
        if datetime.fromisoformat(sample["at"].replace("Z", "+00:00")).tzinfo is None:
            errors.append("resource_timestamp_timezone")
        if type(sample["pid"]) is not int or sample["pid"] <= 0 or _finite(sample["rss_bytes"]) <= 0:
            errors.append("invalid_process_observation")
        if observations["device"].startswith("cuda") and _finite(sample["vram_allocated_bytes"]) <= 0:
            errors.append("missing_gpu_observation")
    return errors


def validate_supplemental(cfg: dict, reports: dict) -> dict:
    result = {}
    for gate, (stage, name, filename) in SUPPLEMENTAL.items():
        report = reports.get(name, {})
        errors = []
        try:
            if not report or report.get("schema_version") != 1 or report.get("gate") != gate:
                raise ValueError("missing supplemental observations")
            if gate in {'S1', 'S2', 'S6'}:
                raw_path = raw_reference(Path(cfg[name]).parent, report['raw'])
                if read_json(raw_path) != report['observations']:
                    raise ValueError('supplemental observations differ from archived raw bytes')
            if gate == "S1":
                errors = lineage_errors(report, cfg)
            elif gate == "S2":
                errors = context_errors(report)
            elif gate in {"S3", "S5"}:
                if report["quality_sha256"] != sha256(cfg["quality"]):
                    raise ValueError("quality observations changed")
                errors = statistics_errors(reports["quality"]) if gate == "S3" else complete_evidence_errors(reports["quality"])
            elif gate == "S4":
                errors = answer_errors(report, cfg)
            else:
                errors = observability_errors(report, reports)
            if report.get("status") != "pass" or report.get("errors") != []:
                errors.append("supplemental_report_not_pass")
            if report.get("index_sha256") != reports["baseline"].get("index_sha256"):
                errors.append("supplemental_index_binding")
            if stage >= 3:
                for field in ("source_sha256", "runtime_sha256", "model_identity_sha256"):
                    if not report.get(field) or report[field] != reports["smoke"].get(field):
                        errors.append("supplemental_" + field + "_binding")
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            errors.append("missing_or_invalid_supplemental_raw")
        result[gate] = {"status": "PASS" if not errors else "BLOCKED" if not report else "FAIL",
                        "errors": sorted(set(errors)), "required_at": f"M{stage}", "artifacts": [filename]}
    return result
