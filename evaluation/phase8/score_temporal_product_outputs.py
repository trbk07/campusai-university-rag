"""Score saved product outputs against the Phase 8 temporal draft.

This module has no provider client and never sends requests. It only consumes
paired internal/public product responses already captured by an authorized
runner. The draft remains regression-only until review and exposure work pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

from campusai.rag.abstention import canonicalize_abstention_reason
from campusai.rag.grounding import validate_citation
from campusai.rag.schemas import validate_release_response, validate_response
from evaluation.benchmarks.connected_groups import connected_groups
from evaluation.grounding.grounding_metrics import evaluate_grounding
from evaluation.phase8.build_temporal_review_draft import ROOT


DEFAULT_INDEX = ROOT / ".tmp/hybrid-index"
DEFAULT_BENCHMARK = ROOT / "evaluation/phase8/benchmark_candidate_v5.jsonl"
DEFAULT_OUTPUT = ROOT / "evaluation/results/phase8-product-quality-v5.json"
BOOTSTRAP_ITERATIONS = 2000
GROUNDING_CI_METRICS = (
    "grounded_claim_precision", "grounded_claim_recall", "unsupported_claim_leakage",
    "contradicted_claim_leakage", "citation_precision", "citation_recall",
    "citation_coordinate_validity",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_tree_sha256(index_dir: Path) -> str:
    entries = [{
        "path": path.relative_to(index_dir).as_posix(),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    } for path in sorted(index_dir.rglob("*")) if path.is_file()]
    encoded = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_execution_manifest(path: Path, *, benchmark_path: Path,
                                 predictions_path: Path, index_manifest_path: Path,
                                 index_tree_sha256: str) -> tuple[dict, str]:
    """Fail closed unless runtime memory evidence binds this exact scored run."""
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1 or payload.get("status") != "completed":
        raise ValueError("execution manifest must be completed schema_version 1")
    bindings = payload.get("bindings")
    expected = {
        "benchmark_sha256": sha256(benchmark_path),
        "predictions_sha256": sha256(predictions_path),
        "index_manifest_sha256": sha256(index_manifest_path),
        "index_tree_sha256": index_tree_sha256,
    }
    if not isinstance(bindings, dict) or any(bindings.get(key) != value for key, value in expected.items()):
        raise ValueError("execution manifest bindings do not match benchmark, predictions, and index")
    memory = payload.get("peak_working_set_bytes")
    if type(memory) is not int or memory <= 0:
        raise ValueError("execution manifest peak_working_set_bytes must be a positive integer")
    if not str(payload.get("measurement_method", "")).strip():
        raise ValueError("execution manifest must identify its peak working-set measurement method")
    return payload, sha256(path)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _expected_answer_present(row: dict, answer: str) -> bool:
    expected = str(row.get("gold_answer", "")).strip()
    return bool(expected and re.search(
        rf"(?<![A-Za-z0-9]){re.escape(expected)}(?![A-Za-z0-9])", answer, flags=re.I))


def _public_grounding_metrics(rows: list[dict]) -> dict:
    """Count all gold citation links, including unanswered/unmatched claims.

    Citation identity is independent of bilingual lexical claim matching.
    Hidden internal diagnostics never count as published answer evidence.
    """
    quality = evaluate_grounding(rows)
    citations = matched = coordinates = gold_links = recovered = 0
    for row in rows:
        items = row.get('citations', [])
        checks = row.get('_citation_checks', [bool(row.get('citation_valid'))] * len(items))
        valid = [item for item, ok in zip(items, checks) if ok]
        gold = [e for claim in row.get('gold_claims', []) for e in claim.get('evidence', [])]

        def same(citation, evidence):
            if evidence.get('chunk_id'):
                return citation.get('chunk_id') == evidence['chunk_id']
            interval = citation.get('page_range', [citation.get('page'), citation.get('page')])
            return (citation.get('doc_id') == evidence.get('doc_id')
                    and isinstance(interval, (list, tuple)) and len(interval) == 2
                    and interval[0] <= evidence.get('page', -1) <= interval[1])

        citations += len(items)
        coordinates += len(valid)
        matched += sum(any(same(item, e) for e in gold) for item in valid)
        gold_links += len(gold)
        recovered += sum(any(same(item, e) for item in valid) for e in gold)
    quality.update(citation_precision=round(matched / max(1, citations), 6),
                   citation_recall=round(recovered / max(1, gold_links), 6),
                   citation_coordinate_validity=round(coordinates / max(1, citations), 6))
    return quality


def _bootstrap_ci(rows: list[dict], values: dict[str, float], metric_name: str,
                  *, iterations: int, seed: int = 20261010) -> dict:
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    grouped: dict[str, list[float]] = defaultdict(list)
    for qid, value in values.items():
        grouped[groups[qid]].append(value)
    keys = sorted(grouped)
    if len(keys) < 2:
        return {"status": "not_estimable", "groups": len(keys), "ci95": None}
    import random

    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        sampled_keys = [keys[rng.randrange(len(keys))] for _ in keys]
        sample = [value for key in sampled_keys for value in grouped[key]]
        estimates.append(statistics.mean(sample))
    estimates.sort()
    return {
        "status": "measured",
        "metric": metric_name,
        "groups": len(keys),
        "iterations": iterations,
        "seed": seed,
        "ci95": [round(estimates[int(.025 * iterations)], 6),
                 round(estimates[min(iterations - 1, int(.975 * iterations))], 6)],
    }


def _bootstrap_ratio_ci(rows: list[dict], numerator_qids: set[str], denominator_qids: set[str],
                        metric_name: str, *, iterations: int,
                        seed: int = 20261010) -> dict:
    """Group-bootstrap a ratio whose denominator varies with predictions."""
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    grouped: dict[str, tuple[int, int]] = {}
    for group in set(groups.values()):
        members = [qid for qid, value in groups.items() if value == group]
        grouped[group] = (sum(qid in numerator_qids for qid in members),
                          sum(qid in denominator_qids for qid in members))
    keys = sorted(grouped)
    if len(keys) < 2 or not denominator_qids:
        return {"status": "not_estimable", "metric": metric_name, "groups": len(keys),
                "ci95": None, "reason": "ratio needs predicted positives across at least two groups"}
    import random

    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        sampled = [keys[rng.randrange(len(keys))] for _ in keys]
        numerator = sum(grouped[key][0] for key in sampled)
        denominator = sum(grouped[key][1] for key in sampled)
        if denominator:
            estimates.append(numerator / denominator)
    if len(estimates) < max(2, int(iterations * 0.9)):
        return {"status": "not_estimable", "metric": metric_name, "groups": len(keys),
                "valid_iterations": len(estimates), "iterations": iterations, "ci95": None,
                "reason": "too many bootstrap samples had a zero predicted-positive denominator"}
    estimates.sort()
    return {"status": "measured", "metric": metric_name, "groups": len(keys),
            "iterations": iterations, "valid_iterations": len(estimates), "seed": seed,
            "ci95": [round(estimates[int(.025 * len(estimates))], 6),
                     round(estimates[min(len(estimates) - 1, int(.975 * len(estimates)))], 6)]}


def _bootstrap_grounding_cis(rows: list[dict], metrics: tuple[str, ...], *,
                             iterations: int, seed: int = 20261010) -> dict[str, dict]:
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    members: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        members[groups[row["qid"]]].append(row)
    keys = sorted(members)
    if len(keys) < 2:
        return {metric: {"status": "not_estimable", "groups": len(keys), "ci95": None}
                for metric in metrics}
    import random

    rng = random.Random(seed)
    estimates = {metric: [] for metric in metrics}
    for _ in range(iterations):
        selected = [keys[rng.randrange(len(keys))] for _ in keys]
        sample = [row for key in selected for row in members[key]]
        result = _public_grounding_metrics(sample)
        for metric in metrics:
            estimates[metric].append(float(result[metric]))
    reports = {}
    for metric, values in estimates.items():
        values.sort()
        reports[metric] = {
            "status": "measured", "metric": metric, "groups": len(keys),
            "iterations": iterations, "seed": seed,
            "ci95": [round(values[int(.025 * iterations)], 6),
                     round(values[min(iterations - 1, int(.975 * iterations))], 6)],
        }
    return reports


def _bootstrap_latency_ci(rows: list[dict], values: dict[str, float], *,
                          iterations: int, seed: int = 20261010) -> dict:
    groups = connected_groups([{
        "qid": row["qid"], "question": row["question"],
        "source_group": row.get("source_group", ""),
        "paraphrase_group": row.get("paraphrase_group", ""),
    } for row in rows])
    grouped: dict[str, list[float]] = defaultdict(list)
    for qid, value in values.items():
        if qid in groups:
            grouped[groups[qid]].append(float(value))
    keys = sorted(grouped)
    if len(keys) < 2 or not values:
        return {"status": "not_estimable", "groups": len(keys), "iterations": iterations,
                "ci95": None, "reason": "warm latency needs observations in at least two connected groups"}
    import random

    rng = random.Random(seed)
    estimates = {"p50": [], "p95": [], "p99": []}
    for _ in range(iterations):
        sampled_keys = [keys[rng.randrange(len(keys))] for _ in keys]
        sample = sorted(value for key in sampled_keys for value in grouped[key])
        estimates["p50"].append(statistics.median(sample))
        for label, fraction in (("p95", .95), ("p99", .99)):
            estimates[label].append(sample[min(len(sample) - 1, int(fraction * len(sample)))])
    intervals = {}
    for label, samples in estimates.items():
        samples.sort()
        intervals[label] = [round(samples[int(.025 * iterations)], 3),
                            round(samples[min(iterations - 1, int(.975 * iterations))], 3)]
    return {"status": "measured", "groups": len(keys), "iterations": iterations,
            "seed": seed, "ci95_ms": intervals}


def _slice_metrics(rows: list[dict], *, answer_values: dict[str, float],
                   code_values: dict[str, float], reason_values: dict[str, float],
                   schema_error_qids: set[str], latency_values: dict[str, float],
                   iterations: int) -> dict:
    """Report the same denominator and group-bootstrap contract for a slice."""
    answerable = [row for row in rows if row.get("answerable") is True]
    unanswerable = [row for row in rows if row.get("answerable") is False]
    exact = {row["qid"]: value for row in rows if (value := answer_values.get(row["qid"])) is not None}
    codes = {row["qid"]: value for row in rows if (value := code_values.get(row["qid"])) is not None}
    reasons = {row["qid"]: value for row in rows if (value := reason_values.get(row["qid"])) is not None}
    abstained = {row["qid"] for row in rows if row.get("abstained")}
    true_abstentions = {row["qid"] for row in unanswerable if row.get("abstained")}
    false_abstention_values = {row["qid"]: float(bool(row.get("abstained"))) for row in answerable}
    false_positive_values = {row["qid"]: float(not bool(row.get("abstained"))) for row in unanswerable}
    abstention_recall_values = {row["qid"]: float(bool(row.get("abstained"))) for row in unanswerable}
    schema_values = {row["qid"]: float(row["qid"] not in schema_error_qids) for row in rows}
    slice_latency = {row["qid"]: latency_values[row["qid"]]
                     for row in rows if row["qid"] in latency_values}
    quality = _public_grounding_metrics(rows)
    grounding_cis = _bootstrap_grounding_cis(rows, GROUNDING_CI_METRICS, iterations=iterations)
    predicted_claims = quality["predicted_claim_count"]
    gold_claims = quality["gold_claim_count"]
    citations = sum(len(row.get("citations", [])) for row in rows)
    gold_links = sum(len(claim.get("evidence", [])) for row in rows
                     for claim in row.get("gold_claims", []))

    def mean_metric(values: dict[str, float], name: str, population: str,
                    aggregation: str) -> dict:
        return {
            "value": round(sum(values.values()) / len(values), 6) if values else None,
            "numerator": int(sum(values.values())), "denominator": len(values),
            "status": "measured" if values else "not_applicable_empty_population",
            "population": population, "aggregation": aggregation,
            "ci95": (_bootstrap_ci(rows, values, name, iterations=iterations) if values else
                     {"status": "not_applicable", "ci95": None}),
        }

    def grounding_metric(key: str, numerator: int, denominator: int, description: str) -> dict:
        return {
            "value": quality[key], "numerator": numerator, "denominator": denominator,
            "status": "measured" if denominator else "not_applicable_empty_population",
            "population": description, "aggregation": "micro ratio over the stated population",
            "ci95": (grounding_cis[key] if denominator else
                     {"status": "not_applicable", "ci95": None}),
        }

    predicted_abstentions = len(abstained)
    precision_ci = (_bootstrap_ratio_ci(rows, true_abstentions, abstained,
                                        "abstention_precision", iterations=iterations)
                    if predicted_abstentions else {"status": "not_applicable", "ci95": None})
    latency_sorted = sorted(slice_latency.values())
    latency_metrics = {
        "status": "measured" if latency_sorted else "not_measured",
        "measured_requests": len(latency_sorted), "denominator": len(latency_sorted),
        "population": "warm product requests in this slice; cold first request excluded",
        "aggregation": "nearest-rank p50/p95/p99 over per-request end-to-end latency in milliseconds",
        "warm_p50_ms": round(float(statistics.median(latency_sorted)), 3) if latency_sorted else None,
        "warm_p95_ms": round(latency_sorted[min(len(latency_sorted) - 1, int(.95 * len(latency_sorted)))], 3)
            if latency_sorted else None,
        "warm_p99_ms": round(latency_sorted[min(len(latency_sorted) - 1, int(.99 * len(latency_sorted)))], 3)
            if latency_sorted else None,
        "ci95": (_bootstrap_latency_ci(rows, slice_latency, iterations=iterations) if slice_latency else
                 {"status": "not_applicable", "ci95_ms": None}),
    }
    return {
        "records": len(rows), "answerable_denominator": len(answerable),
        "unanswerable_denominator": len(unanswerable),
        "latency": latency_metrics,
        "exact_gold_answer_match": mean_metric(exact, "exact_gold_answer_match",
            "rows with explicit gold_answer", "micro exact normalized answer-text match"),
        "required_code_accuracy": mean_metric(codes, "required_code_accuracy",
            "temporal/comparison rows with required codes", "micro exact code match"),
        "answerable_false_abstention_rate": mean_metric(false_abstention_values,
            "answerable_false_abstention_rate", "answerable rows", "micro fraction incorrectly abstained"),
        "unanswerable_false_positive_rate": mean_metric(false_positive_values,
            "unanswerable_false_positive_rate", "unanswerable rows", "micro fraction answered instead of abstained"),
        "unanswerable_abstention_rate": mean_metric(abstention_recall_values,
            "unanswerable_abstention_rate", "unanswerable rows", "micro fraction correctly abstained"),
        "abstention_precision": {
            "value": round(len(true_abstentions) / predicted_abstentions, 6) if predicted_abstentions else None,
            "numerator": len(true_abstentions), "denominator": predicted_abstentions,
            "status": "measured" if predicted_abstentions else "not_applicable_empty_population",
            "population": "predicted abstentions", "aggregation": "micro fraction that are unanswerable",
            "ci95": precision_ci,
        },
        "abstention_reason_accuracy": {
            **mean_metric(reasons, "abstention_reason_accuracy",
                "rows with owner-labeled gold_abstention_reason", "micro exact canonical reason match"),
            "status": "measured" if reasons else "not_measured_no_gold_abstention_reason_labels",
        },
        "semantic_answer_correctness": {
            "value": None, "numerator": 0, "denominator": 0,
            "status": "not_measured_human_labels_required",
            "population": "answerable product responses",
            "aggregation": "human-labeled semantic correctness; exact text match is insufficient",
        },
        "grounded_claim_precision": grounding_metric("grounded_claim_precision",
            round(quality["grounded_claim_precision"] * predicted_claims), predicted_claims, "predicted answer claims"),
        "grounded_claim_recall": grounding_metric("grounded_claim_recall",
            round(quality["grounded_claim_recall"] * gold_claims), gold_claims, "gold answer claims"),
        "unsupported_claim_leakage": grounding_metric("unsupported_claim_leakage",
            round(quality["unsupported_claim_leakage"] * predicted_claims), predicted_claims, "predicted answer claims"),
        "contradicted_claim_leakage": grounding_metric("contradicted_claim_leakage",
            round(quality["contradicted_claim_leakage"] * predicted_claims), predicted_claims, "predicted answer claims"),
        "citation_precision": grounding_metric("citation_precision",
            round(quality["citation_precision"] * citations), citations, "public citations"),
        "citation_recall": grounding_metric("citation_recall",
            round(quality["citation_recall"] * gold_links), gold_links, "gold claim-evidence links"),
        "citation_coordinate_validity": grounding_metric("citation_coordinate_validity",
            round(quality["citation_coordinate_validity"] * citations),
            citations, "public citations"),
        "schema_validity": mean_metric(schema_values, "schema_validity", "all product responses",
            "micro fraction passing internal and public response schemas"),
    }


def _load_index(index_dir: Path) -> dict[tuple[str, str], SimpleNamespace]:
    result = {}
    for doc_dir in index_dir.iterdir():
        dense_path = doc_dir / "dense.json"
        if not doc_dir.is_dir() or not dense_path.is_file():
            continue
        payload = json.loads(dense_path.read_text(encoding="utf-8-sig"))
        for item in payload.get("items", []):
            metadata = dict(item.get("metadata", {}))
            metadata.setdefault("page_range", item.get("page_range", [item.get("page"), item.get("page")]))
            result[(item.get("doc_id", doc_dir.name), item["chunk_id"])] = SimpleNamespace(
                doc_id=item.get("doc_id", doc_dir.name),
                chunk_id=item["chunk_id"],
                page=item.get("page"),
                metadata=metadata,
                content=item.get("content", ""),
            )
    return result


def score(benchmark_rows: list[dict], prediction_rows: list[dict], *,
          benchmark_path: Path = DEFAULT_BENCHMARK, index_dir: Path = DEFAULT_INDEX,
          execution_manifest_path: Path | None = None, predictions_path: Path | None = None,
          freeze_manifest_path: Path | None = None,
          bootstrap_iterations: int = BOOTSTRAP_ITERATIONS) -> dict:
    expected_ids = [row["qid"] for row in benchmark_rows]
    prediction_ids = [row.get("qid") for row in prediction_rows]
    if not benchmark_rows or len(set(expected_ids)) != len(benchmark_rows):
        raise ValueError("the bound benchmark must contain unique qids")
    if (len(prediction_rows) != len(benchmark_rows)
            or len(set(prediction_ids)) != len(prediction_rows)
            or prediction_ids != expected_ids):
        raise ValueError("predictions must contain exactly one record per benchmark qid in benchmark order")
    by_id = {row["qid"]: row for row in prediction_rows}
    index = _load_index(index_dir)
    scored_rows = []
    answer_values = {}
    code_values = {}
    schema_errors = {}
    for benchmark in benchmark_rows:
        pred = by_id[benchmark["qid"]]
        internal = pred.get("internal_response")
        public = pred.get("public_response")
        if not isinstance(internal, dict) or not isinstance(public, dict):
            raise ValueError(f"{benchmark['qid']}: internal_response and public_response are required")
        internal_ok, internal_errors = validate_response(internal, include_internal=True)
        public_ok, public_errors = validate_release_response(public)
        errors = list(internal_errors) + list(public_errors)
        coordinate_results = []
        for citation in public.get("citations", []) if isinstance(public.get("citations"), list) else []:
            indexed = index.get((citation.get("doc_id"), citation.get("chunk_id")))
            if indexed is None:
                coordinate_results.append(False)
            else:
                coordinate_results.append(validate_citation(
                    citation, indexed, require_quote=True, require_provenance=False).valid)
        citation_valid = all(coordinate_results) if coordinate_results else True
        response_row = {
            **benchmark,
            **internal,
            "schema_valid": internal_ok and public_ok,
            "citation_valid": citation_valid,
            "public": not bool(internal.get("abstained")),
            "claims": ([claim for claim in internal.get("claims", [])
                        if claim.get("claim_id") in {c.get("claim_id") for c in public.get("claims", [])}]
                       if not public.get("abstained") else []),
            "citations": public.get("citations", []),
            "_citation_checks": coordinate_results,
        }
        scored_rows.append(response_row)
        if str(benchmark.get("gold_answer", "")).strip():
            answer_values[benchmark["qid"]] = float(
                not internal.get("abstained") and
                _expected_answer_present(benchmark, str(internal.get("answer", ""))))
        expected_claims = benchmark.get("expected_claims") or []
        if ("temporal" in benchmark.get("tags", []) and expected_claims
                and (expected_claims[0].get("old_course_code")
                     or expected_claims[0].get("adjusted_course_code"))):
            code_values[benchmark["qid"]] = float(
                not internal.get("abstained") and
                _expected_answer_present(benchmark, str(internal.get("answer", ""))))
        if errors:
            schema_errors[benchmark["qid"]] = errors

    quality = _public_grounding_metrics(scored_rows)
    grounding_cis = _bootstrap_grounding_cis(
        scored_rows, GROUNDING_CI_METRICS, iterations=bootstrap_iterations)
    q_count = len(scored_rows)
    predicted_claims = quality["predicted_claim_count"]
    gold_claims = quality["gold_claim_count"]
    citations_count = sum(len(row.get("citations", [])) for row in scored_rows)
    gold_links = sum(len(claim.get("evidence", [])) for row in scored_rows
                     for claim in row.get("gold_claims", []))
    answerable_rows = [row for row in scored_rows if row.get("answerable") is True]
    unanswerable_rows = [row for row in scored_rows if row.get("answerable") is False]
    answerable_abstentions = sum(bool(row.get("abstained")) for row in answerable_rows)
    negative_false_positives = sum(not bool(row.get("abstained")) for row in unanswerable_rows)
    negative_abstentions = len(unanswerable_rows) - negative_false_positives
    predicted_abstentions = sum(bool(row.get("abstained")) for row in scored_rows)
    reason_values = {}
    for row in scored_rows:
        expected_reason = row.get("gold_abstention_reason")
        if expected_reason:
            expected = canonicalize_abstention_reason(expected_reason)
            observed = canonicalize_abstention_reason(
                row.get("abstention_reason", row.get("reason")),
                evidence_found=bool(row.get("retrieved_pages")),
            )
            reason_values[row["qid"]] = float(bool(row.get("abstained")) and observed == expected)
    abstention_tp_qids = {row["qid"] for row in unanswerable_rows if row.get("abstained")}
    predicted_abstention_qids = {row["qid"] for row in scored_rows if row.get("abstained")}
    metrics = {
        "exact_gold_answer_match": {
            "value": round(sum(answer_values.values()) / len(answer_values), 6) if answer_values else None,
            "numerator": int(sum(answer_values.values())), "denominator": len(answer_values),
            "status": "measured" if answer_values else "not_measured_no_gold_answer_fields",
            "population": "rows with explicit gold_answer; exact normalized substring in non-abstained answer",
            "aggregation": "micro exact text match, not semantic correctness",
            "ci95": (_bootstrap_ci(scored_rows, answer_values, "exact_gold_answer_match",
                                   iterations=bootstrap_iterations) if answer_values else
                     {"status": "not_applicable", "ci95": None}),
        },
        "required_code_accuracy": {
            "value": round(sum(code_values.values()) / len(code_values), 6) if code_values else None,
            "numerator": int(sum(code_values.values())), "denominator": len(code_values),
            "status": "measured" if code_values else "not_applicable_no_temporal_code_rows",
            "population": "temporal/comparison rows with old/new course codes; exact code in answer text",
            "aggregation": "micro exact code match",
            "ci95": (_bootstrap_ci(scored_rows, code_values, "required_code_accuracy",
                                   iterations=bootstrap_iterations) if code_values else
                     {"status": "not_applicable", "ci95": None}),
        },
        "grounded_claim_precision": {
            "value": quality["grounded_claim_precision"],
            "numerator": round(quality["grounded_claim_precision"] * predicted_claims),
            "denominator": predicted_claims,
            "status": "measured" if predicted_claims else "not_applicable_no_predicted_claims",
            "population": "predicted answer claims across benchmark rows",
            "aggregation": "micro fraction of predicted claims supported by gold evidence",
            "ci95": (grounding_cis["grounded_claim_precision"]
                     if predicted_claims else {"status": "not_applicable", "ci95": None}),
        },
        "grounded_claim_recall": {
            "value": quality["grounded_claim_recall"],
            "numerator": round(quality["grounded_claim_recall"] * gold_claims),
            "denominator": gold_claims,
            "status": "measured" if gold_claims else "not_applicable_no_gold_claims",
            "population": "gold answer claims across benchmark rows",
            "aggregation": "micro fraction of gold claims recovered with support",
            "ci95": grounding_cis["grounded_claim_recall"],
        },
        "unsupported_claim_leakage": {
            "value": quality["unsupported_claim_leakage"],
            "numerator": round(quality["unsupported_claim_leakage"] * predicted_claims),
            "denominator": predicted_claims,
            "status": "measured" if predicted_claims else "not_applicable_no_predicted_claims",
            "population": "predicted answer claims across benchmark rows",
            "aggregation": "micro fraction of predicted claims that are unsupported",
            "ci95": (grounding_cis["unsupported_claim_leakage"]
                     if predicted_claims else {"status": "not_applicable", "ci95": None}),
        },
        "contradicted_claim_leakage": {
            "value": quality["contradicted_claim_leakage"],
            "numerator": round(quality["contradicted_claim_leakage"] * predicted_claims),
            "denominator": predicted_claims,
            "status": "measured" if predicted_claims else "not_applicable_no_predicted_claims",
            "population": "predicted answer claims across benchmark rows",
            "aggregation": "micro fraction of predicted claims that are contradicted",
            "ci95": (grounding_cis["contradicted_claim_leakage"]
                     if predicted_claims else {"status": "not_applicable", "ci95": None}),
        },
        "citation_precision": {
            "value": quality["citation_precision"],
            "numerator": round(quality["citation_precision"] * citations_count),
            "denominator": citations_count,
            "status": "measured" if citations_count else "not_applicable_no_citations",
            "population": "public citations across benchmark rows",
            "aggregation": "micro fraction of citations matching gold evidence",
            "ci95": (grounding_cis["citation_precision"]
                     if citations_count else {"status": "not_applicable", "ci95": None}),
        },
        "citation_recall": {
            "value": quality["citation_recall"],
            "numerator": round(quality["citation_recall"] * gold_links),
            "denominator": gold_links,
            "status": "measured" if gold_links else "not_applicable_no_gold_evidence_links",
            "population": "gold claim-evidence links across benchmark rows",
            "aggregation": "micro fraction of gold evidence links cited",
            "ci95": grounding_cis["citation_recall"],
        },
        "citation_coordinate_validity": {
            "value": quality["citation_coordinate_validity"],
            "numerator": round(quality["citation_coordinate_validity"] * citations_count),
            "denominator": citations_count,
            "status": "measured" if citations_count else "not_applicable_no_citations",
            "population": "public citations across benchmark rows",
            "aggregation": "micro fraction with valid document/page/chunk coordinates",
            "ci95": (grounding_cis["citation_coordinate_validity"]
                     if citations_count else {"status": "not_applicable", "ci95": None}),
        },
        "answerable_false_abstention_rate": {
            "value": round(answerable_abstentions / len(answerable_rows), 6) if answerable_rows else None,
            "numerator": answerable_abstentions, "denominator": len(answerable_rows),
            "ci95": (_bootstrap_ci(scored_rows,
                                   {row["qid"]: float(bool(row["abstained"])) for row in answerable_rows},
                                   "answerable_false_abstention_rate",
                                   iterations=bootstrap_iterations) if answerable_rows else
                     {"status": "not_applicable", "ci95": None}),
            "population": "answerable benchmark rows",
            "aggregation": "micro fraction of answerable rows incorrectly abstained",
        },
        "unanswerable_false_positive_rate": {
            "value": round(negative_false_positives / len(unanswerable_rows), 6) if unanswerable_rows else None,
            "numerator": negative_false_positives, "denominator": len(unanswerable_rows),
            "status": "measured" if unanswerable_rows else "not_applicable_no_unanswerable_rows",
            "population": "unanswerable benchmark rows",
            "aggregation": "micro fraction answered instead of abstained",
            "ci95": (_bootstrap_ci(scored_rows,
                                   {row["qid"]: float(not bool(row["abstained"])) for row in unanswerable_rows},
                                   "unanswerable_false_positive_rate", iterations=bootstrap_iterations)
                     if unanswerable_rows else {"status": "not_applicable", "ci95": None}),
        },
        "unanswerable_abstention_rate": {
            "value": round(negative_abstentions / len(unanswerable_rows), 6) if unanswerable_rows else None,
            "numerator": negative_abstentions, "denominator": len(unanswerable_rows),
            "status": "measured" if unanswerable_rows else "not_applicable_no_unanswerable_rows",
            "population": "unanswerable benchmark rows",
            "aggregation": "micro fraction correctly abstained",
            "ci95": (_bootstrap_ci(scored_rows,
                                   {row["qid"]: float(bool(row["abstained"])) for row in unanswerable_rows},
                                   "unanswerable_abstention_rate", iterations=bootstrap_iterations)
                     if unanswerable_rows else {"status": "not_applicable", "ci95": None}),
        },
        "schema_validity": {
            "value": round((q_count - len(schema_errors)) / q_count, 6),
            "numerator": q_count - len(schema_errors), "denominator": q_count,
            "status": "measured", "population": "all benchmark responses",
            "aggregation": "micro fraction passing internal and public response schemas",
            "ci95": _bootstrap_ci(scored_rows,
                {row["qid"]: float(row["qid"] not in schema_errors) for row in scored_rows},
                "schema_validity", iterations=bootstrap_iterations),
        },
        "abstention_precision": {
            "value": round(negative_abstentions / predicted_abstentions, 6) if predicted_abstentions else None,
            "numerator": negative_abstentions, "denominator": predicted_abstentions,
            "status": "measured" if predicted_abstentions else "not_applicable_no_predicted_abstentions",
            "population": "predicted abstentions across benchmark rows",
            "aggregation": "micro fraction of predicted abstentions that are unanswerable",
            "ci95": (_bootstrap_ratio_ci(scored_rows, abstention_tp_qids,
                                         predicted_abstention_qids, "abstention_precision",
                                         iterations=bootstrap_iterations)
                     if predicted_abstentions else {"status": "not_applicable", "ci95": None}),
        },
        "abstention_recall": {
            "value": round(negative_abstentions / len(unanswerable_rows), 6) if unanswerable_rows else None,
            "numerator": negative_abstentions, "denominator": len(unanswerable_rows),
            "status": "measured" if unanswerable_rows else "not_applicable_no_unanswerable_rows",
            "population": "unanswerable benchmark rows",
            "aggregation": "micro fraction correctly abstained",
            "ci95": (_bootstrap_ci(scored_rows,
                                   {row["qid"]: float(bool(row.get("abstained"))) for row in unanswerable_rows},
                                   "abstention_recall", iterations=bootstrap_iterations)
                     if unanswerable_rows else {"status": "not_applicable", "ci95": None}),
        },
        "abstention_reason_accuracy": {
            "value": round(sum(reason_values.values()) / len(reason_values), 6) if reason_values else None,
            "numerator": int(sum(reason_values.values())), "denominator": len(reason_values),
            "status": "measured" if reason_values else "not_measured_no_gold_abstention_reason_labels",
            "population": "benchmark rows with an owner-labeled gold_abstention_reason",
            "aggregation": "micro exact match after canonicalizing the abstention reason taxonomy",
            "ci95": (_bootstrap_ci(scored_rows, reason_values, "abstention_reason_accuracy",
                                   iterations=bootstrap_iterations) if reason_values else
                     {"status": "not_measured_no_gold_abstention_reason_labels", "ci95": None}),
        },
    }
    latency_by_qid = {row["qid"]: float(row["latency_ms"]) for row in prediction_rows
                      if row.get("latency_ms") is not None}
    if any("cold_start" in row for row in prediction_rows):
        if any(type(row.get("cold_start")) is not bool or not row.get("runtime_id")
               for row in prediction_rows):
            raise ValueError("sharded predictions require cold_start and runtime_id on every row")
        seen_runtimes = set()
        for row in prediction_rows:
            if row["cold_start"] != (row["runtime_id"] not in seen_runtimes):
                raise ValueError("cold_start must label the first request of each runtime")
            seen_runtimes.add(row["runtime_id"])
        cold_ids = {row["qid"] for row in prediction_rows if row["cold_start"]}
    else:
        cold_ids = {expected_ids[0]}
    warm_rows = [row for row in benchmark_rows if row["qid"] not in cold_ids]
    warm_latency_by_qid = {qid: value for qid, value in latency_by_qid.items() if qid not in cold_ids}
    latency_values = list(latency_by_qid.values())
    warm_values = list(warm_latency_by_qid.values())
    cold_values = [latency_by_qid[qid] for qid in expected_ids if qid in cold_ids and qid in latency_by_qid]
    if len(latency_values) == q_count and warm_values:
        latency = {
            "status": "measured",
            "measured_requests": q_count,
            "denominator": q_count,
            "population": "all product requests; first request of each runtime separately labeled cold start",
            "aggregation": "per-request latency in milliseconds; sharded cold requests include recorded runtime startup",
            "cold_ms": latency_values[0],
            "cold_requests": len(cold_values),
            "cold_start_values_ms": cold_values,
            "warm_requests": len(warm_values),
            "warm_p50_ms": round(float(statistics.median(warm_values)), 3),
            "warm_p95_ms": round(sorted(warm_values)[min(len(warm_values) - 1,
                                                        int(.95 * len(warm_values)))], 3),
            "warm_p99_ms": round(sorted(warm_values)[min(len(warm_values) - 1,
                                                        int(.99 * len(warm_values)))], 3),
            "total_ms": round(sum(latency_values), 3),
            "cold_ci95": {"status": "not_estimable_single_cold_request" if len(cold_values) == 1
                          else "not_measured_runtime_bootstrap_required", "ci95_ms": None},
            "warm_ci95": _bootstrap_latency_ci(
                warm_rows, warm_latency_by_qid, iterations=bootstrap_iterations),
        }
    else:
        latency = {"status": "not_measured", "reason": "all per-query latency_ms values and at least one warm request are required"}

    split_metrics = {
        split: _slice_metrics(
            [row for row in scored_rows if row.get("split", "unknown") == split],
            answer_values=answer_values, code_values=code_values, reason_values=reason_values,
            schema_error_qids=set(schema_errors), latency_values=warm_latency_by_qid,
            iterations=bootstrap_iterations)
        for split in sorted({row.get("split", "unknown") for row in scored_rows})
    }
    tag_predicates = {
        "single_hop_fact": {
            "definition": "answerable; excludes table, calculation, multi_hop, prerequisite, temporal, and comparison tags",
            "predicate": lambda row: row.get("answerable") is True and not set(row.get("tags", [])) & {
                "table", "calculation", "multi_hop", "prerequisite", "temporal", "comparison"},
        },
        "table_or_calculation": {
            "definition": "tagged table or calculation",
            "predicate": lambda row: bool(set(row.get("tags", [])) & {"table", "calculation"}),
        },
        "prerequisite_or_multi_hop": {
            "definition": "tagged prerequisite or multi_hop",
            "predicate": lambda row: bool(set(row.get("tags", [])) & {"prerequisite", "multi_hop"}),
        },
        "temporal_or_comparison": {
            "definition": "tagged temporal or comparison",
            "predicate": lambda row: bool(set(row.get("tags", [])) & {"temporal", "comparison"}),
        },
        "unanswerable_or_adversarial": {
            "definition": "unanswerable or tagged adversarial",
            "predicate": lambda row: row.get("answerable") is False or "adversarial" in row.get("tags", []),
        },
    }
    category_metrics = {
        category: {
            "definition": description["definition"],
            "overlap_allowed": True,
            "metrics": _slice_metrics(
                [row for row in scored_rows if description["predicate"](row)],
                answer_values=answer_values, code_values=code_values, reason_values=reason_values,
                schema_error_qids=set(schema_errors), latency_values=warm_latency_by_qid,
                iterations=bootstrap_iterations),
        }
        for category, description in tag_predicates.items()
    }
    index_manifest_path = index_dir / "manifest.json"
    index_manifest = json.loads(index_manifest_path.read_text(encoding="utf-8-sig"))
    index_size_bytes = sum(path.stat().st_size for path in index_dir.rglob("*") if path.is_file())
    execution_manifest = None
    execution_manifest_sha256 = None
    if execution_manifest_path is not None:
        if predictions_path is None:
            raise ValueError("predictions_path is required when binding an execution manifest")
        execution_manifest, execution_manifest_sha256 = _validate_execution_manifest(
            execution_manifest_path, benchmark_path=benchmark_path,
            predictions_path=predictions_path, index_manifest_path=index_manifest_path,
            index_tree_sha256=_index_tree_sha256(index_dir))
        if _read_jsonl(benchmark_path) != benchmark_rows or _read_jsonl(predictions_path) != prediction_rows:
            raise ValueError("scored rows must be loaded from the files bound by the execution manifest")
    metrics["semantic_answer_correctness"] = {
        "value": None, "numerator": 0, "denominator": 0,
        "status": "not_measured_human_labels_required",
        "reason": "exact answer-text match does not establish semantic correctness; human labels are required",
        "population": "answerable product responses",
        "aggregation": "human-labeled semantic correctness; no gold labels are currently bound",
    }
    metrics["peak_working_set_bytes"] = {
        "value": execution_manifest.get("peak_working_set_bytes") if execution_manifest else None,
        "numerator": execution_manifest.get("peak_working_set_bytes", 0) if execution_manifest else 0,
        "denominator": None,
        "unit": "bytes",
        "status": "measured" if execution_manifest else "not_measured_execution_manifest_required",
        "reason": None if execution_manifest else
            "the scorer process is not the product execution process; bind a product execution manifest",
        "execution_manifest_sha256": execution_manifest_sha256,
        "population": "product process during the bound benchmark run",
        "aggregation": "maximum resident working set in bytes",
    }
    metrics["index_size_bytes"] = {
        "value": index_size_bytes, "numerator": index_size_bytes, "denominator": None,
        "unit": "bytes", "status": "measured",
        "population": "all files under the index directory bound by index_tree_sha256",
        "aggregation": "sum of file sizes",
    }
    try:
        benchmark_label = benchmark_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        benchmark_label = benchmark_path.as_posix()
    grounding_metric_details = dict(quality)
    review_metadata = {"owner_review": "pending", "frozen": False, "officially_approved": False}
    if freeze_manifest_path is not None:
        from evaluation.phase8.repair_reviewed_benchmark import verify_freeze
        freeze = json.loads(freeze_manifest_path.read_text(encoding="utf-8"))
        verify_freeze(freeze)
        if freeze["benchmark"]["sha256"] != sha256(benchmark_path) or _read_jsonl(benchmark_path) != benchmark_rows:
            raise ValueError("freeze does not bind the scored benchmark")
        review_metadata.update(owner_review="owner_delegated_ai_complete", frozen=True,
                               freeze_manifest_sha256=sha256(freeze_manifest_path))
    grounding_metric_details["reason_accuracy"] = metrics["abstention_reason_accuracy"]["value"]
    grounding_metric_details["reason_accuracy_status"] = metrics["abstention_reason_accuracy"]["status"]
    unmeasured = {
        "semantic_answer_correctness": "not_measured_requires_human_labels; exact_gold_answer_match is only exact text matching",
        "abstention_reason_accuracy": "not_measured_requires_owner_labeled_gold_abstention_reason",
    }
    if execution_manifest is None:
        unmeasured["peak_working_set_bytes"] = "not_measured_requires_product_execution_manifest"
    recorded_replay = any(row.get("mode") == "recorded_chat_replay" for row in prediction_rows)
    if recorded_replay:
        timing_scope = "local_wsgi_processing_with_recorded_chat_output_not_live_provider"
        latency["scope"] = timing_scope
        latency["live_provider_latency_measured"] = False
        for item in split_metrics.values():
            item["latency"]["scope"] = timing_scope
        for item in category_metrics.values():
            item["metrics"]["latency"]["scope"] = timing_scope
        metrics["peak_working_set_bytes"]["scope"] = timing_scope
        unmeasured["live_provider_end_to_end_latency"] = "not_measured_recorded_chat_replay_returns_model_output_instantly"
    return {
        "schema_version": 1,
        "phase": 8,
        "status": ("recorded_chat_replay_scored_regression_only" if recorded_replay
                   else "product_quality_scored_regression_only"),
        "gate_eligible": False,
        "provider_requests_by_scorer": 0,
        "scorer_sha256": sha256(Path(__file__)),
        "benchmark": {
            "path": benchmark_label,
            "file_sha256": sha256(benchmark_path),
            "canonical_rows_sha256": hashlib.sha256(("\n".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) for row in benchmark_rows
            )).encode("utf-8")).hexdigest(),
            "rows": q_count,
            "split_counts": dict(sorted(Counter(row.get("split", "unknown") for row in benchmark_rows).items())),
            "tag_counts": dict(sorted(Counter(tag for row in benchmark_rows for tag in row.get("tags", [])).items())),
            **review_metadata,
            "fresh_validation": False,
        },
        "prediction_count": len(prediction_rows),
        "runtime": {
            "index_manifest_sha256": sha256(index_manifest_path),
            "index_tree_sha256": _index_tree_sha256(index_dir),
            "model": index_manifest.get("model_name"),
            "model_revision": index_manifest.get("model_revision"),
            "index_size_bytes": index_size_bytes,
            "execution_manifest_sha256": execution_manifest_sha256,
        },
        "metrics": metrics,
        "grounding_metric_details": grounding_metric_details,
        "split_metrics": split_metrics,
        "category_metrics": category_metrics,
        "schema_errors": schema_errors,
        "latency": latency,
        "unmeasured": unmeasured,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--predictions", type=Path, required=True,
                        help="Saved JSONL rows containing qid, internal_response, public_response, and latency_ms")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--execution-manifest", type=Path,
                        help="Optional completed run manifest bound to this benchmark, predictions, and index")
    parser.add_argument("--freeze-manifest", type=Path, help="Optional reviewed benchmark freeze; verified against scored rows")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = score(_read_jsonl(args.benchmark), _read_jsonl(args.predictions),
                   benchmark_path=args.benchmark, index_dir=args.index_dir,
                   execution_manifest_path=args.execution_manifest, predictions_path=args.predictions,
                   freeze_manifest_path=args.freeze_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "gate_eligible": result["gate_eligible"],
                      "exact_gold_answer_match": result["metrics"]["exact_gold_answer_match"],
                      "required_code_accuracy": result["metrics"]["required_code_accuracy"],
                      "citation_precision": result["metrics"]["citation_precision"],
                      "citation_recall": result["metrics"]["citation_recall"],
                      "provider_requests_by_scorer": result["provider_requests_by_scorer"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
