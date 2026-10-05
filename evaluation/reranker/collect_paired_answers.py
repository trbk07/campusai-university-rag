"""Collect uncached, paired live answers; leave semantic review pending."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import random
import time

from evaluation.benchmarks.human_benchmark_intake import digest_record
from evaluation.common.release_artifacts import (read_json, sha256, source_identity, write_json,
                                                require_previous_gates, freeze_before_evaluation, policy_bindings)
from evaluation.reranker.paired_answer_quality import answer_digest


def prompt_provenance(prompt: str) -> dict:
    """Retain the exact answer context and bind it to the provider prompt."""
    if not isinstance(prompt, str):
        raise TypeError("provider prompt must be text")
    prompt_bytes = prompt.encode("utf-8")
    marker = "\n\nEVIDENCE:\n"
    _, found, selected_context = prompt.partition(marker)
    context_bytes = selected_context.encode("utf-8") if found else b""
    return {
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "prompt_chars": len(prompt),
        "selected_context_status": "captured" if found else "unparsed_prompt_format",
        "selected_context": selected_context if found else None,
        "selected_context_sha256": hashlib.sha256(context_bytes).hexdigest() if found else None,
        "selected_context_chars": len(selected_context) if found else None,
    }


def recording_generate(original_generate, calls: list[dict]):
    """Wrap one provider method while retaining attempted and failed calls."""
    def wrapped(prompt, **options):
        call = {**prompt_provenance(prompt), "provider_status": "attempted",
                "usage": None, "usage_status": "unknown", "latency_ms": None,
                "cached": None, "cost": None, "cost_status": "unknown"}
        calls.append(call)
        started = time.perf_counter()
        try:
            response = original_generate(prompt, **options)
        except Exception as error:
            call.update(provider_status="failed", provider_error_type=type(error).__name__,
                        latency_ms=(time.perf_counter() - started) * 1000)
            raise
        call.update(provider_status="completed", usage=response.usage or None,
                    usage_status="reported" if response.usage else "unknown",
                    latency_ms=response.latency_ms, cached=response.cached)
        return response
    return wrapped


def failed_attempt_record(*, split: str, row: dict, arm: str, request: dict,
                          calls: list[dict], evidence: list[dict], elapsed_ms: float,
                          error: Exception) -> dict:
    """Build a privacy-safe record when an application call raises outright."""
    return {
        "split": "human_" + split,
        "qid": row["qid"],
        "arm": arm,
        "stage": "application_request",
        "error_type": type(error).__name__,
        "request": request,
        "request_sha256": digest_record(request),
        "record_sha256": digest_record(row),
        "llm_calls": list(calls),
        "evidence": evidence,
        "latency_ms": elapsed_ms,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--llm-config", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--prepare-only", action="store_true", help="freeze answer protocol before ranking; do not open held-out rows")
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError("retain paired observations; choose a new output path")
    require_previous_gates("M6", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
    rubric = read_json(args.rubric)
    if rubric.get("status") != "approved" or not rubric.get("reviewer"):
        raise ValueError("approve the semantic rubric before opening held-out answers")
    from campusai.llm.factory import create_llm
    from campusai.llm.client import GeminiClient, OpenAICompatibleClient
    from campusai.rag.grounding import GroundedAnswerGenerator
    from campusai.rag.service import CampusAIQueryService
    from campusai.rag.context import benchmark_request
    from campusai.retrieval.reranker_activation import build_phase7_retriever
    from campusai.retrieval.hybrid import HybridRetriever
    from campusai.retrieval.calibration import RetrievalPolicy
    from evaluation.reranker.measure_reranker_http import _NoAnswerCache
    llm = create_llm(args.llm_config)
    if type(llm) not in (GeminiClient, OpenAICompatibleClient):
        raise ValueError("a concrete live provider is required")
    original_cache, llm.cache = llm.cache, None
    if original_cache is not None:
        original_cache.close()
    phase7 = None
    observations = []
    try:
        phase6_path = args.results_dir / "hybrid_retrieval_calibration.json"
        policy = RetrievalPolicy.from_report(phase6_path, expected_mode="hybrid_rrf")
        baseline = HybridRetriever(args.index_dir, query_cache_size=0, policies={"hybrid_rrf": policy})
        calls = []
        llm.generate = recording_generate(llm.generate, calls)
        phase7 = build_phase7_retriever(args.index_dir, phase6_path, args.benchmark_dir / "human_retrieval_dev.jsonl")
        if not phase7.phase7_enabled:
            raise ValueError("paired answer runtime activation rejected")
        phase7.query_cache_size = 0
        generator = GroundedAnswerGenerator(llm)
        identity = {"provider": type(llm).__name__, "model": llm.model}
        budget = {"max_chars": generator.max_context_chars, "max_tokens": generator.max_context_tokens}
        # The lock is written before reading held-out rows. Changes to rubric,
        # LLM config or generation code require a new independent study.
        from evaluation.reranker.reranker_release_gates import ARTIFACTS
        paths = {key: args.results_dir / ARTIFACTS[key] for key in ("route", "calibration", "smoke", "human_manifest", "sensitivity")}
        protocol = {"schema_version": 1, "status": "frozen", "rubric_sha256": sha256(args.rubric),
                    "llm_config_sha256": sha256(args.llm_config), "llm_identity": identity, "context_budget": budget,
                    "prompt_sha256": sha256(Path(inspect.getfile(GroundedAnswerGenerator))),
                    "review_policy_sha256": sha256(args.benchmark_dir / "phase7_review_policy.json"),
                    "arm_order_seed": args.seed, "provider_repeats_per_arm": 1}
        protocol_path = args.results_dir / "reranker_answer_protocol.json"
        if protocol_path.exists() and read_json(protocol_path) != protocol:
            raise ValueError("answer protocol changed after freeze")
        if not protocol_path.exists():
            with protocol_path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(protocol, sort_keys=True, indent=2) + "\n")
        paths["answer_protocol"] = protocol_path
        freeze_before_evaluation(args.results_dir, paths)
        if args.prepare_only:
            print(json.dumps({"status": "protocol_frozen", "path": str(protocol_path)}))
            return 0
        source = source_identity(Path(__file__).resolve().parents[2])
        failed_attempts = []
        bindings = {"index_sha256": sha256(args.index_dir / "manifest.json"),
                    "model_identity_sha256": read_json(args.results_dir / "model_snapshot_smoke.json")["model_identity_sha256"],
                    "phase6_calibration_sha256": sha256(phase6_path),
                    "calibration_sha256": sha256(args.results_dir / "reranker_score_calibration.json"),
                    "review_policy_sha256": sha256(args.benchmark_dir / "phase7_review_policy.json"),
                    **policy_bindings(args.results_dir)}
        services = {"baseline": CampusAIQueryService(baseline, generator, cache=_NoAnswerCache(), default_mode="auto"),
                    "phase7": CampusAIQueryService(phase7, generator, cache=_NoAnswerCache(), default_mode="phase7")}
        docs = read_json(args.index_dir / "manifest.json")["documents"]
        rng = random.Random(args.seed)
        for split in ("test", "holdout"):
            path = args.benchmark_dir / f"human_retrieval_{split}.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            for row in rows:
                request = benchmark_request(row, docs)
                arms = list(services)
                rng.shuffle(arms)
                for arm in arms:
                    calls.clear()
                    started = time.perf_counter()
                    try:
                        answer = services[arm].ask(**request).to_public_dict()
                    except Exception as error:
                        failure = failed_attempt_record(
                            split=split, row=row, arm=arm, request=request, calls=calls,
                            evidence=[item.to_dict() for item in services[arm].last_retrieval],
                            elapsed_ms=(time.perf_counter() - started) * 1000, error=error)
                        failed_attempts.append(failure)
                        write_json(args.output, {**protocol, "schema_version": 1,
                            "status": "provider_error_partial", "observations": observations,
                            "failed_attempts": failed_attempts, "live_provider": True,
                            "llm_identity": identity, "seed": args.seed,
                            "answer_cache_enabled": False, "llm_cache_enabled": False,
                            "measured_at": datetime.now(timezone.utc).isoformat(),
                            **source, **bindings})
                        raise RuntimeError("paired collection stopped; failed attempt retained") from None
                    observations.append({"split": "human_" + split, "qid": row["qid"], "arm": arm,
                        "author": row["author"], "answerable": row["answerable"], "tags": row["tags"],
                        "request": request, "request_sha256": digest_record(request), "record_sha256": digest_record(row),
                        "rubric_sha256": sha256(args.rubric), "gold_claim_ids": rubric["gold_claim_ids"][row["qid"]],
                        "answer": answer, "evidence": [item.to_dict() for item in services[arm].last_retrieval],
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "llm_calls": list(calls), "usage_status": "reported" if calls and all(call['usage'] for call in calls) else "unknown",
                        "provider_error": answer.get('abstention_reason') == 'llm_error',
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "review": {"status": "pending", "reviewer": "", "reviewer_role": "pending", "answer_sha256": answer_digest(answer),
                                   "reviewed_at": None, "all_factual_claims_enumerated": False, "rubric_satisfied": None,
                                   "unsupported_affirmative_answer": None, "covered_gold_claim_ids": [], "claims": []}})
                    # Persist each arm, including a provider-error output, before
                    # attempting another call. Interrupted pairs remain visible.
                    write_json(args.output, {**protocol, "schema_version": 1, "status": "pending_semantic_review", "observations": observations,
                                        "live_provider": True, "llm_identity": identity,
                                        "seed": args.seed, "answer_cache_enabled": False, "llm_cache_enabled": False,
                                        "measured_at": datetime.now(timezone.utc).isoformat(),
                                        **source, **bindings})
                    if observations[-1]['provider_error'] or any(call['cached'] for call in calls):
                        raise ValueError('paired collection stopped: provider error or cached live call; partial observations retained')
    finally:
        if phase7 is not None and phase7.phase7_provider is not None:
            phase7.phase7_provider.close()
        close = getattr(llm, "close", None)
        if close is not None:
            close()
    print(json.dumps({"status": "pending_semantic_review", "observations": len(observations), "path": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
