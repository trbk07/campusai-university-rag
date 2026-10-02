"""Dev-only exploratory score/margin calibration for the Phase 7 reranker.

The artifact is never marked passing if hard-query routing failed. Test and
holdout are not loaded by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
)
from evaluation.metrics import evaluate_retrieval, ndcg_at_k, recall_at_k, reciprocal_rank
from evaluation.phase6_schema import load_jsonl
from campusai.retrieval.rerank_policy import route_features, score_action
from evaluation.release_artifacts import require_previous_gates, source_identity, assert_tuning_allowed
from evaluation.reranker_model_options import add_inference_options, inference_settings


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)] if ordered else 0.0


def _quality(rows: list[dict], outputs: dict[str, list]) -> dict:
    metrics = evaluate_retrieval(rows, lambda row: outputs[row["qid"]], (1, 3, 5, 10))
    return {"answerable_recall_at_5": metrics["answerable_recall"]["5"],
            "mrr": metrics["mrr_answerable"], "ndcg_at_5": metrics["ndcg"]["5"],
            "negative_fpr": sum(bool(outputs[row["qid"]]) for row in rows if not row["answerable"])
                            / max(1, sum(not row["answerable"] for row in rows))}


def proposal_action(proposal: dict, policy: dict, *, row: dict | None = None, baseline: list | None = None) -> str:
    if policy.get("evidence_model") is not None:
        from campusai.retrieval.evidence_policy import EvidenceProbabilityModel
        from evaluation.calibrate_evidence_probabilities import proposal_features
        if row is None or baseline is None:
            raise ValueError("probability replay requires raw query and retrieval observations")
        return EvidenceProbabilityModel.from_dict(policy["evidence_model"]).action(proposal_features(row, baseline, proposal))
    return score_action(proposal["top_score"], proposal["margin"], policy["threshold"],
                        policy["margin_threshold"], policy.get("low_score_action", "phase6"))


def calibrated_outputs(baseline: dict[str, list], proposals: dict[str, dict], policy: dict,
                       *, rows: list[dict] | None = None) -> dict[str, list]:
    outputs = dict(baseline)
    by_id = {row["qid"]: row for row in rows or []}
    for qid, proposal in proposals.items():
        if qid not in outputs:
            raise ValueError("proposal outside baseline query scope")
        action = proposal_action(proposal, policy, row=by_id.get(qid), baseline=baseline[qid])
        if action == "rerank":
            outputs[qid] = proposal["results"]
        elif action == "abstain":
            outputs[qid] = []
    return outputs


def calibrate(rows: list[dict], baseline: dict[str, list], proposals: dict[str, dict],
              low_score_action: str = "phase6") -> tuple[dict, dict]:
    if low_score_action not in ("phase6", "abstain"):
        raise ValueError("invalid low-score action")
    if any(row.get("split", "dev") != "dev" for row in rows):
        raise ValueError("calibration accepts only dev rows")
    qids = [row["qid"] for row in rows]
    if len(set(qids)) != len(qids) or set(qids) != set(baseline) or not set(proposals) <= set(baseline):
        raise ValueError("calibration query scope mismatch")
    for proposal in proposals.values():
        score_action(proposal["top_score"], proposal["margin"], 0.0, 0.0, low_score_action)
    base_quality = _quality(rows, baseline)
    by_id = {row["qid"]: row for row in rows}
    answerable_count = max(1, sum(row["answerable"] for row in rows))
    negative_count = max(1, sum(not row["answerable"] for row in rows))
    deltas = {}
    abstention_deltas = {}
    for qid, proposal in proposals.items():
        row = by_id[qid]
        gold = row["gold_evidence"]
        before, after = baseline[qid], proposal["results"]
        deltas[qid] = {
            "answerable_recall_at_5": ((recall_at_k(after, gold, 5) - recall_at_k(before, gold, 5))
                                       / answerable_count if row["answerable"] else 0.0),
            "mrr": ((reciprocal_rank(after, gold) - reciprocal_rank(before, gold))
                    / answerable_count if row["answerable"] else 0.0),
            "ndcg_at_5": ((ndcg_at_k(after, gold, 5) - ndcg_at_k(before, gold, 5))
                          / answerable_count if row["answerable"] else 0.0),
            "negative_fpr": ((float(bool(after)) - float(bool(before))) / negative_count
                             if not row["answerable"] else 0.0),
        }
        abstention_deltas[qid] = {
            "answerable_recall_at_5": -recall_at_k(before, gold, 5) / answerable_count if row["answerable"] else 0.0,
            "mrr": -reciprocal_rank(before, gold) / answerable_count if row["answerable"] else 0.0,
            "ndcg_at_5": -ndcg_at_k(before, gold, 5) / answerable_count if row["answerable"] else 0.0,
            "negative_fpr": -float(bool(before)) / negative_count if not row["answerable"] else 0.0,
        }
    top_scores = sorted({item["top_score"] for item in proposals.values()})
    margins = sorted({item["margin"] for item in proposals.values()})
    if not top_scores:
        return {"threshold": 0.0, "margin_threshold": 0.0, "low_score_action": low_score_action}, {
            "baseline": base_quality, "selected": base_quality, "feasible": False}
    thresholds = [top_scores[0] - 1.0, *top_scores, top_scores[-1] + 1.0]
    margin_thresholds = [0.0, *margins, margins[-1] + 1.0]
    best = None
    for threshold in thresholds:
        for margin_threshold in margin_thresholds:
            accepted = [qid for qid, proposal in proposals.items()
                        if proposal["top_score"] >= threshold
                        and proposal["margin"] >= margin_threshold]
            abstained = [qid for qid, proposal in proposals.items()
                         if low_score_action == "abstain" and proposal["top_score"] < threshold]
            quality = {key: base_quality[key] + sum(deltas[qid][key] for qid in accepted)
                       + sum(abstention_deltas[qid][key] for qid in abstained)
                       for key in base_quality}
            feasible = (quality["answerable_recall_at_5"] >= base_quality["answerable_recall_at_5"] - .005
                        and quality["negative_fpr"] <= .01)
            if not feasible:
                continue
            key = (quality["mrr"] + quality["ndcg_at_5"], quality["answerable_recall_at_5"],
                   -len(accepted), threshold, margin_threshold)
            if best is None or key > best[0]:
                best = (key, threshold, margin_threshold, quality)
    if best is None:
        return {"threshold": top_scores[0] - 1.0, "margin_threshold": margins[-1] + 1.0,
                "low_score_action": low_score_action}, {
            "baseline": base_quality, "selected": base_quality, "feasible": False}
    policy = {"threshold": best[1], "margin_threshold": best[2], "low_score_action": low_score_action}
    actual = _quality(rows, calibrated_outputs(baseline, proposals, policy))
    feasible = (actual["answerable_recall_at_5"] >= base_quality["answerable_recall_at_5"] - .005
                and actual["negative_fpr"] <= .01)
    return policy, {"baseline": base_quality, "selected": actual, "feasible": feasible}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", type=Path, default=Path("data/benchmark/human_retrieval_dev.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--phase6-calibration", type=Path,
                        default=Path("evaluation/results/phase6_retrieval_calibration.json"))
    parser.add_argument("--route-calibration", type=Path,
                        default=Path("evaluation/results/hard_query_route_calibration.json"))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--device", default="cpu", help="Explicit cpu, cuda or cuda:N device")
    parser.add_argument("--dtype", choices=("float32", "float16", "bfloat16"), default="float32")
    add_inference_options(parser)
    parser.add_argument("--rerank-cap", type=int, default=10)
    parser.add_argument("--evidence-policy", choices=("probability", "score"), default="probability")
    parser.add_argument("--low-score-action", choices=("phase6", "abstain"), default="phase6")
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--timeout-ms", type=int, default=1000)
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--exploratory", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=Path(".tmp/reranker-reranker-calibration-candidate.json"))
    args = parser.parse_args()
    if not args.exploratory:
        require_previous_gates("M5", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.dev.parent)
        assert_tuning_allowed(args.results_dir)
    if not 1 <= args.rerank_cap <= 40:
        raise SystemExit("rerank cap must be between 1 and 40")
    rows = load_jsonl(args.dev)
    if not rows or any(row.get("split") != "dev" for row in rows):
        raise SystemExit("reranker calibration accepts only dev rows")
    route = json.loads(args.route_calibration.read_text(encoding="utf-8"))
    if (route.get("calibration_split") != "dev" or route.get("holdout_used") is not False
            or route.get("training_split_sha256") != _sha(args.dev)
            or route.get("index_sha256") != _sha(args.index_dir / "manifest.json")
            or route.get("phase6_calibration_sha256") != _sha(args.phase6_calibration)):
        raise SystemExit("route calibration provenance mismatch")
    identity = ModelIdentity(args.model_name, args.model_dir.name,
                             snapshot_sha256(args.model_dir), args.model_dir.name,
                             device=args.device, dtype=args.dtype, **inference_settings(args))
    if not args.exploratory:
        smoke = json.loads((args.results_dir / "model_snapshot_smoke.json").read_text(encoding="utf-8"))
        if identity != ModelIdentity(**smoke["model_identity"]):
            raise SystemExit("calibration inference settings must match the measured M3 identity")
    provider = OfflineCrossEncoderReranker(identity, args.model_dir,
                                           timeout_ms=args.timeout_ms, candidate_cap=args.rerank_cap)
    phase6 = RetrievalPolicy.from_report(args.phase6_calibration, expected_mode="hybrid_rrf")
    retriever = HybridRetriever(args.index_dir, query_cache_size=0,
                                policies={"hybrid_rrf": phase6})
    doc_ids = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
    baseline = {}
    proposals = {}
    latencies = []
    errors = []
    eligible = 0
    try:
        provider.warm_up()
        for row in rows:
            qid = row["qid"]
            results = retriever.search(row["question"], doc_ids=row.get("doc_ids", doc_ids),
                                       filters=row.get("filters"), top_k=5, mode="auto")
            baseline[qid] = results
            trace = retriever.last_trace
            if trace.route in {"exact_code", "abstain"} or trace.abstained or len(results) < 2:
                continue
            confidence = float(results[0].confidence_score or 0.0)
            fusion_margin = max(0.0, float(results[0].fusion_score or 0.0)
                                - float(results[1].fusion_score or 0.0))
            features = route_features(row["question"], results)
            hard = (confidence < route["easy_confidence_threshold"] or fusion_margin < route["easy_margin_threshold"]
                    or (route.get("minimum_agreement", 0) and features["agreement"] < route["minimum_agreement"])
                    or (route.get("constraint_threshold", 0) and features["constraints"] >= route["constraint_threshold"]))
            if not hard:
                continue
            eligible += 1
            pool = retriever.search(row["question"], doc_ids=row.get("doc_ids", doc_ids),
                                    filters=row.get("filters"), top_k=40, mode="auto")
            candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id,
                                          item.page, item.content, item.rank,
                                          float(item.fusion_score or 0.0))
                          for item in pool[:args.rerank_cap]]
            started = time.perf_counter()
            try:
                ranking = provider.score(row["question"], candidates)
            except Exception as error:
                errors.append({"qid": qid, "error_type": type(error).__name__,
                               "reason": str(error) if str(error) in {"reranker_timeout", "invalid_model_scores", "queue_full", "circuit_open"} else "provider_failure"})
                continue
            latencies.append((time.perf_counter() - started) * 1000)
            by_id = {item.chunk_id: item for item in pool}
            reranked = [by_id[item.candidate_id] for item in ranking]
            reranked.extend(pool[args.rerank_cap:])
            proposals[qid] = {"results": reranked[:5],
                              "top_score": ranking[0].reranker_score,
                              "evidence_inputs": {"ranked_candidates": [by_id[item.candidate_id].to_dict() for item in ranking],
                                                  "scores": [item.reranker_score for item in ranking]},
                              "margin": ranking[0].reranker_score - ranking[1].reranker_score
                              if len(ranking) > 1 else 0.0}
    finally:
        provider.close()
    selected, comparison = calibrate(rows, baseline, proposals, args.low_score_action)
    if args.evidence_policy == "probability":
        from evaluation.calibrate_evidence_probabilities import calibrate_probabilities
        try:
            selected, comparison = calibrate_probabilities(rows, baseline, proposals)
        except ValueError as error:
            errors.append({"qid": None, "error_type": "EvidenceCalibrationError", "reason": str(error)})
            comparison["feasible"] = False
    quality = comparison["selected"]
    score_gate = (comparison["feasible"] and quality["answerable_recall_at_5"] >= .95
                  and quality["negative_fpr"] <= .01 and not errors)
    route_gate = route.get("status") == "pass"
    report = {"schema_version": 1, "phase": 7, "mode": "hybrid_rerank",
              "version": "phase7-evidence-dev-v3" if selected.get("evidence_model") else ("phase7-rerank-dev-v2" if args.low_score_action == "abstain" else "phase7-rerank-dev-v1"),
              "status": "pass" if score_gate and route_gate and not args.exploratory else "conditional",
              "calibration_split": "dev", "holdout_used": False, "test_used": False,
              **source_identity(Path(__file__).resolve().parents[1]),
              "model_identity": identity.to_dict(),
              "model_identity_sha256": identity.fingerprint,
              "index_sha256": _sha(args.index_dir / "manifest.json"),
              "phase6_calibration_sha256": _sha(args.phase6_calibration),
              "training_split_sha256": _sha(args.dev),
              "route_calibration_sha256": _sha(args.route_calibration),
              "threshold": selected["threshold"],
              "margin_threshold": selected["margin_threshold"],
              "low_score_action": selected["low_score_action"],
              "evidence_policy": args.evidence_policy,
              "evidence_model": selected.get("evidence_model"),
              "easy_confidence_threshold": route["easy_confidence_threshold"],
              "easy_margin_threshold": route["easy_margin_threshold"],
              "minimum_agreement": route.get("minimum_agreement", 0),
              "constraint_threshold": route.get("constraint_threshold", 0),
              "candidate_cap": 40, "rerank_candidate_cap": args.rerank_cap,
              "selection_rule": "hard route only; valid low scores use calibrated low_score_action; low margins and provider faults use Phase 6",
              "positive_count": sum(row["answerable"] for row in rows),
              "negative_count": sum(not row["answerable"] for row in rows),
              "recall": quality["answerable_recall_at_5"],
              "false_positive_rate": quality["negative_fpr"],
              "comparison": comparison,
              "routing_status": route.get("status"),
              "rerank_requests": len(proposals),
              "eligible_requests": eligible,
              "fallback_rate": (eligible - sum(proposal_action(p, selected, row=next(r for r in rows if r["qid"] == qid), baseline=baseline[qid])
                                  != "phase6" for qid, p in proposals.items())) / max(1, eligible),
              "evidence_abstention_rate": sum(proposal_action(p, selected, row=next(r for r in rows if r["qid"] == qid), baseline=baseline[qid])
                                         == "abstain" for qid, p in proposals.items()) / max(1, eligible),
              "timeout_rate": sum(e["reason"] == "reranker_timeout" for e in errors) / max(1, eligible),
              "invalid_score_rate": sum(e["reason"] == "invalid_model_scores" for e in errors) / max(1, eligible),
              "rerank_latency_ms": {"p50": _percentile(latencies, .5),
                                     "p95": _percentile(latencies, .95),
                                     "p99": _percentile(latencies, .99)},
              "errors": errors}
    report["calibration_observations"] = {
        "baseline": {qid: [item.to_dict() for item in values] for qid, values in baseline.items()},
        "proposals": {qid: {**proposal, "results": [item.to_dict() for item in proposal["results"]]}
                      for qid, proposal in proposals.items()}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "routing_status": report["routing_status"],
                      "baseline": comparison["baseline"], "selected": quality,
                      "rerank_requests": len(proposals), "rerank_p95_ms": report["rerank_latency_ms"]["p95"],
                      "errors": len(errors)}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
