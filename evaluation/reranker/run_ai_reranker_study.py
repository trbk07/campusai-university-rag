"""Real-model GPU/CPU research with AI questions; never a release gate shortcut.

Fit on dev, freeze once, then measure held-out quality and concurrent retrieval.
All output stays in .release/reranker/studies and is explicitly ineligible for
production. A failed route or score fit remains a recorded failure.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import statistics
from threading import Event, Thread
import time

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.cross_encoder_provider import ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.rerank_policy import Phase7Policy
from evaluation.reranker.calibrate_hard_query_route import collect_samples, fit_feature_route, route_metrics
from evaluation.reranker.calibrate_reranker_scores import calibrate, _quality
from evaluation.retrieval.compare_retrieval_quality import compare_split
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.release_artifacts import sha256, source_identity, write_json

CAPS = (8, 10, 12, 16, 20)


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else 0.0


def latency_summary(values):
    return {"p50": percentile(values, .5), "p95": percentile(values, .95), "p99": percentile(values, .99)}


def complete_gold_coverage(rows, outputs, k=5):
    """Unlike any-hit recall, measure whether all supporting chunks were found."""
    positives = [row for row in rows if row["answerable"]]
    complete = []
    for row in positives:
        gold = {(item["doc_id"], item["chunk_id"]) for item in row["gold_evidence"]}
        found = {(item["doc_id"], item["chunk_id"]) for item in outputs[row["qid"]][:k]}
        complete.append(gold <= found)
    return statistics.mean(complete) if complete else 0.0


def validate_dataset(directory: Path, index_dir: Path):
    manifest = json.loads((directory / "dataset_manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("evidence_type") != "ai_authored_pdf_research" or manifest.get("release_eligible") is not False
            or manifest.get("review_status") != "not_human_reviewed"
            or manifest.get("index_sha256") != sha256(index_dir / "manifest.json")):
        raise ValueError("research dataset identity mismatch")
    for split in ("dev", "test", "holdout"):
        if manifest["dataset_sha256"][split] != sha256(directory / f"{split}.jsonl"):
            raise ValueError("research dataset checksum mismatch")
    for doc, checksum in manifest["chunk_sha256"].items():
        if Path(doc).name != doc or doc in {".", ".."} or sha256(index_dir / doc / "bm25.json") != checksum:
            raise ValueError("frozen chunk checksum mismatch")
    return manifest


def load_rows(directory, split):
    rows = [json.loads(line) for line in (directory / f"{split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if (not rows or any(row.get("split") != split or row.get("author_type") != "ai"
                        or row.get("review_status") != "not_human_reviewed" or row.get("release_eligible") is not False
                        for row in rows) or len({row["qid"] for row in rows}) != len(rows)):
        raise ValueError("invalid AI research rows")
    return rows


def output_dict(item):
    return {**item.to_dict(), "reranker_score": item.reranker_score}


def proposal(row, pool, provider, cap):
    candidates = [RerankCandidate(item.chunk_id, item.doc_id, item.chunk_id, item.page,
                                 item.content, item.rank, float(item.fusion_score or 0)) for item in pool[:cap]]
    started = time.perf_counter()
    ranking = provider.score(row["question"], candidates)
    elapsed = (time.perf_counter() - started) * 1000
    by_id = {item.chunk_id: item for item in pool}
    outputs = [replace(by_id[item.candidate_id], rank=rank, reranker_score=item.reranker_score)
               for rank, item in enumerate(ranking, 1)]
    outputs.extend(replace(item, rank=rank) for rank, item in enumerate(pool[len(candidates):], len(candidates) + 1))
    return {"results": outputs, "top_score": ranking[0].reranker_score,
            "margin": ranking[0].reranker_score - ranking[1].reranker_score if len(ranking) > 1 else 0.0,
            "latency_ms": elapsed, "candidate_count": len(candidates)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=Path(".release/reranker/studies/ai-benchmark-v1"))
    parser.add_argument("--output-dir", type=Path, default=Path(".release/reranker/studies/ai-gpu-v1"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/hybrid_retrieval_calibration.json"))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--requests-per-profile", type=int, default=100)
    parser.add_argument("--concurrency", default="1,5,20")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    if not output.is_relative_to(root / ".release" / "reranker" / "studies"):
        raise ValueError("research output must stay in the isolated studies directory")
    profiles = [int(value) for value in args.concurrency.split(",")]
    if args.requests_per_profile < 100 or not profiles or len(set(profiles)) != len(profiles) or any(value not in (1, 5, 20) for value in profiles):
        raise ValueError("at least 100 requests per distinct 1/5/20 concurrency profile required")
    output.mkdir(parents=True, exist_ok=True)
    # Reserve the attempt before doing work. Failed and evaluated studies cannot
    # silently be retuned using the same held-out data or overwritten on rerun.
    with (output / "attempt.json").open("x", encoding="utf-8") as handle:
        json.dump({"status": "running", "release_eligible": False}, handle)
    manifest = validate_dataset(args.dataset_dir, args.index_dir)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    import psutil
    from campusai.retrieval.runtime_provenance import runtime_description
    process = psutil.Process()
    identity = ModelIdentity("BAAI/bge-reranker-v2-m3", args.model_dir.name,
                             snapshot_sha256(args.model_dir), args.model_dir.name, device=args.device)
    phase6 = RetrievalPolicy.from_report(args.calibration)
    provider = OfflineCrossEncoderReranker(identity, args.model_dir, timeout_ms=1000, candidate_cap=20)
    baseline = HybridRetriever(args.index_dir, query_cache_size=0, policies={"hybrid_rrf": phase6})
    metadata = {"schema_version": 1, "status": "conditional", "release_eligible": False,
                "evidence_type": "ai_authored_real_model_research", "human_review": "missing",
                **source_identity(root), "runtime_environment": runtime_description(),
                "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
                "dataset_manifest_sha256": sha256(args.dataset_dir / "dataset_manifest.json"),
                "index_sha256": manifest["index_sha256"], "phase6_calibration_sha256": sha256(args.calibration)}
    report = {**metadata, "splits": {}, "capacity": [], "errors": []}
    try:
        started = time.perf_counter()
        provider.warm_up()
        report["warmup_ms"] = (time.perf_counter() - started) * 1000
        dev = load_rows(args.dataset_dir, "dev")
        samples, bypass = collect_samples(dev, baseline, [])
        route, routing_metrics, route_feasible = fit_feature_route(samples)
        report["dev_route"] = {"config": route, "feasible": route_feasible, "metrics": routing_metrics, **bypass, "samples": samples}
        base_policy = Phase7Policy("ai-study-only-v1", identity.fingerprint, manifest["index_sha256"],
                                   sha256(args.calibration), manifest["dataset_sha256"]["dev"],
                                   -1e6, 0, **route, rerank_candidate_cap=20)
        before, pools = {}, {}
        for row in dev:
            before[row["qid"]] = baseline.search(row["question"], row["doc_ids"], mode="auto", top_k=5)
            selected, _ = base_policy.route(row["question"], before[row["qid"]], baseline.last_trace)
            if selected:
                pools[row["qid"]] = baseline.search(row["question"], row["doc_ids"], mode="auto", top_k=40)
        trials, proposals_by_cap = [], {}
        for cap in CAPS:
            proposals = {}
            for row in dev:
                if pools.get(row["qid"]):
                    proposals[row["qid"]] = proposal(row, pools[row["qid"]], provider, cap)
            fit, comparison = calibrate(dev, before, proposals)
            shadow = {**before, **{qid: value["results"][:5] for qid, value in proposals.items()}}
            trial = {"cap": cap, "fit": fit, "comparison": comparison, "shadow_quality": _quality(dev, shadow),
                     "latency_ms": latency_summary([value["latency_ms"] for value in proposals.values()]),
                     "requests": len(proposals), "release_eligible": False}
            trials.append(trial)
            proposals_by_cap[cap] = proposals
            write_json(output / f"dev-cap-{cap}.json", {**metadata, **trial,
                       "baseline": {qid: [output_dict(item) for item in items] for qid, items in before.items()},
                       "proposals": {qid: {**value, "results": [output_dict(item) for item in value["results"]]}
                                     for qid, value in proposals.items()}})
            print(json.dumps({"event": "dev_cap", **trial}), flush=True)
        passing = [trial for trial in trials if trial["comparison"]["feasible"] and trial["latency_ms"]["p95"] <= 1000]
        # If calibration cannot pass, record a conservative fallback policy and
        # measure shadow ranking separately. Never pretend this is a valid fit.
        choices = passing or trials
        chosen = max(choices, key=lambda trial: (trial["comparison"]["selected"]["mrr"],
                                                  trial["comparison"]["selected"]["ndcg_at_5"],
                                                  -trial["latency_ms"]["p95"], -trial["cap"]))
        policy = replace(base_policy, **chosen["fit"], rerank_candidate_cap=chosen["cap"])
        freeze = {**metadata, "calibration_split": "dev", "test_used": False, "holdout_used": False,
                  "route_feasible": route_feasible, "score_feasible": bool(passing), "selected_cap": chosen["cap"],
                  "policy": policy.__dict__, "trials": trials, "dataset_sha256": manifest["dataset_sha256"]}
        write_json(output / "frozen_dev_policy.json", freeze)
        freeze_hash = sha256(output / "frozen_dev_policy.json")
        report["frozen_policy_sha256"] = freeze_hash
        report["dev_trials"] = trials
        report["selected_cap"] = chosen["cap"]
        # This is a local research object, never an activation report or env flag.
        baseline.phase7_provider, baseline.phase7_policy, baseline.phase7_enabled = provider, policy, True
        evidence = frozen_evidence(args.index_dir)
        for split in ("dev", "test", "holdout"):
            rows = dev if split == "dev" else load_rows(args.dataset_dir, split)
            before_outputs, after_outputs, observations, shadow_outputs = {}, {}, [], {}
            split_samples, split_bypass = collect_samples(rows, baseline, [])
            for number, row in enumerate(rows, 1):
                values = baseline.search(row["question"], row["doc_ids"], mode="auto", top_k=10)
                before_outputs[row["qid"]] = [output_dict(item) for item in values]
                start = time.perf_counter()
                ranked = baseline.search(row["question"], row["doc_ids"], mode="phase7", top_k=10)
                elapsed = (time.perf_counter() - start) * 1000
                after_outputs[row["qid"]] = [output_dict(item) for item in ranked]
                trace = baseline.last_trace.to_dict()
                shadow_outputs[row["qid"]] = before_outputs[row["qid"]]
                routing = baseline.search(row["question"], row["doc_ids"], mode="auto", top_k=5)
                selected, _ = policy.route(row["question"], routing, baseline.last_trace)
                if selected:
                    pool = baseline.search(row["question"], row["doc_ids"], mode="auto", top_k=40)
                    if pool:
                        raw = proposal(row, pool, provider, policy.rerank_candidate_cap)
                        shadow_outputs[row["qid"]] = [output_dict(item) for item in raw["results"][:10]]
                observations.append({"qid": row["qid"], "latency_ms": elapsed, "rss_bytes": process.memory_info().rss,
                                     "trace": trace})
                if number % 10 == 0:
                    print(json.dumps({"event": "quality_progress", "split": split, "completed": number}), flush=True)
            part = compare_split(rows, before_outputs, after_outputs, evidence, [])
            shadow_part = compare_split(rows, before_outputs, shadow_outputs, evidence, [])
            part["complete_gold_coverage5"] = {"baseline": complete_gold_coverage(rows, before_outputs),
                                                 "phase7": complete_gold_coverage(rows, after_outputs),
                                                 "shadow": complete_gold_coverage(rows, shadow_outputs)}
            part["latency_ms"] = latency_summary([item["latency_ms"] for item in observations])
            part["route"] = {**route_metrics(split_samples, **{
                "confidence_threshold": route["easy_confidence_threshold"], "margin_threshold": route["easy_margin_threshold"],
                "minimum_agreement": route["minimum_agreement"], "constraint_threshold": route["constraint_threshold"]}), **split_bypass}
            write_json(output / f"quality-{split}.json", {**metadata, "frozen_policy_sha256": freeze_hash,
                       "quality": part, "shadow_quality": shadow_part, "observations": observations})
            report["splits"][split] = {key: value for key, value in part.items() if key != "per_query"}
            report["splits"][split]["shadow_quality"] = {key: value for key, value in shadow_part.items() if key != "per_query"}
            print(json.dumps({"event": "quality_done", "split": split, "baseline": part["baseline"],
                              "phase7": part["phase7"], "shadow": shadow_part["phase7"], "latency_ms": part["latency_ms"]}), flush=True)
            write_json(output / "report.json", report)
        for concurrency in profiles:
            # A busy profile can trip the actual circuit breaker. Each following
            # profile must start with a fresh provider, rather than accidentally
            # benchmarking only Phase 6 after a previous rollback.
            provider.close()
            provider.drain()
            provider = OfflineCrossEncoderReranker(identity, args.model_dir, timeout_ms=1000, candidate_cap=20)
            provider.warm_up()
            baseline.phase7_provider = provider
            baseline.phase7_enabled = True
            gauges, stop = [], Event()
            def sample_memory():
                while not stop.is_set():
                    gauges.append({"elapsed_ms": (time.perf_counter() - profile_started) * 1000,
                                   "rss_bytes": process.memory_info().rss,
                                   "queue_depth": provider.metrics_snapshot()["queue_depth"]})
                    stop.wait(.01)
            def retrieve(number):
                row = dev[number % len(dev)]
                started = time.perf_counter()
                result = baseline.search(row["question"], row["doc_ids"], mode="phase7", top_k=5)
                return {"request_id": number, "qid": row["qid"], "difficulty": row["difficulty"],
                        "answerable": row["answerable"], "latency_ms": (time.perf_counter() - started) * 1000,
                        "trace": baseline.last_trace.to_dict(), "output": [output_dict(item) for item in result]}
            profile_started = time.perf_counter()
            sampler = Thread(target=sample_memory, daemon=True)
            sampler.start()
            try:
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    observations = list(executor.map(retrieve, range(args.requests_per_profile)))
            finally:
                stop.set()
                sampler.join()
            elapsed = time.perf_counter() - profile_started
            summary = {"concurrency": concurrency, "requests": len(observations), "duration_seconds": elapsed,
                       "requests_per_second": len(observations) / elapsed,
                       "latency_ms": latency_summary([item["latency_ms"] for item in observations]),
                       "peak_rss_bytes": max(item["rss_bytes"] for item in gauges),
                       "peak_queue_depth": max(item["queue_depth"] for item in gauges),
                       "selected_requests": sum(item["trace"]["rerank_selected"] for item in observations),
                       "timeout_requests": sum(item["trace"]["rerank_reason"] == "reranker_timeout" for item in observations),
                       "queue_full_requests": sum(item["trace"]["rerank_reason"] == "queue_full" for item in observations),
                       "provider_metrics": provider.metrics_snapshot(), "phase7_enabled_at_start": True,
                       "phase7_enabled_after": baseline.phase7_enabled,
                       "rolled_back_during_profile": not baseline.phase7_enabled}
            write_json(output / f"capacity-{concurrency}.json", {**metadata, "frozen_policy_sha256": freeze_hash,
                       "summary": summary, "observations": observations, "resource_gauges": gauges})
            report["capacity"].append(summary)
            print(json.dumps({"event": "capacity_done", **summary}), flush=True)
            write_json(output / "report.json", report)
        if args.device.startswith("cuda"):
            import torch
            report["gpu"] = {"name": torch.cuda.get_device_properties(args.device).name,
                             "peak_allocated_bytes": torch.cuda.max_memory_allocated(args.device),
                             "peak_reserved_bytes": torch.cuda.max_memory_reserved(args.device)}
        if sha256(output / "frozen_dev_policy.json") != freeze_hash:
            raise ValueError("frozen study policy was modified during evaluation")
        report["completed"] = True
        write_json(output / "report.json", report)
        return 0
    except Exception as error:
        report["completed"] = False
        report["errors"].append({"type": type(error).__name__, "message": str(error)})
        write_json(output / "report.json", report)
        raise
    finally:
        provider.close()
        provider.drain()


if __name__ == "__main__":
    raise SystemExit(main())
