"""Prepare exact dev-only paired prompts, then collect only an approved packet.

Historical retrieval/reranker observations are replayed for a small grounding
diagnostic. This does not run or certify the current Phase 7 serving policy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import random

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import RetrievalResult
from evaluation.benchmarks.dev_inheritance import rows_at
from evaluation.common.artifact_store import resolve_artifact
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.collect_paired_answers import recording_generate
from evaluation.reranker.optimize_reranker_dev import rank_fusion
from evaluation.reranker.paired_answer_quality import answer_digest

QIDS = [f"human-candidate-{number:04d}" for number in (156, 159, 165, 178)]
ROOT = Path("evaluation/results/phase7-completion-20261004")
REVISION = Path("data/benchmark/phase7_dev_gold_revision_20261007/packet")
SCORES = ROOT / "p7-09_successor_code_table_window_v3_raw_scores.json.gz"


def results(items):
    return [RetrievalResult(item["chunk_id"], item["doc_id"], item["page"], item["content"],
                            item["content_type"], item["score"], item["retrieval_mode"], item["metadata"],
                            rank=number) for number, item in enumerate(items, 1)]


def prepare(output: Path):
    if output.exists():
        raise FileExistsError(output)
    manifest = read_json(REVISION / "manifest.json")
    for name, digest in manifest["outputs"].items():
        if sha256(REVISION / name) != digest:
            raise ValueError("revision packet changed")
    rows = {row["qid"]: row for row in rows_at(REVISION / "human_retrieval_dev.jsonl")}
    rubric = read_json(REVISION / "rubric.partial.json")
    raw = json.loads(gzip.decompress(resolve_artifact(SCORES).read_bytes()))
    if (raw["dev_sha256"] != manifest["parent_dev_sha256"] or raw["index_sha256"] != manifest["index_sha256"]
            or raw["test_used"] or raw["holdout_used"] or not raw["measurements_real"]):
        raise ValueError("historical scores differ from revision parent/index")
    observations = {part["qid"]: part for part in raw["observations"]}
    generator = GroundedAnswerGenerator(max_context_chars=12000, max_context_tokens=2500)
    rng, pairs = random.Random(7), []
    for qid in QIDS:
        row, measured = rows[qid], observations[qid]
        if (row["split"] != "dev" or row["release_eligible"] or qid not in rubric["claims"]
                or measured["actual_request"]["query"] != row["question"]
                or measured["actual_request"]["doc_ids"] != row["doc_ids"]):
            raise ValueError("pilot requires source-reviewed dev with unchanged measured request")
        arms = {"historical_baseline": measured["baseline"][:5],
                "historical_reranked_cap20": rank_fusion(measured["pool"], measured["scores"], 1.0, 20)[:5]}
        order = list(arms)
        rng.shuffle(order)
        for arm in order:
            prompt = generator.prompt(row["question"], results(arms[arm]))
            pairs.append({"qid": qid, "arm": arm, "question": row["question"], "evidence": arms[arm],
                          "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                          "gold_claims": rubric["claims"][qid]})
    packet = {"schema_version": 1, "status": "PREPARED_AWAITING_BENCHMARK_EGRESS_AUTHORIZATION",
              "endpoint_host": "generativelanguage.googleapis.com", "provider": "Gemini",
              "model": "gemini-3-flash-preview", "max_provider_calls": 8, "max_retries": 0,
              "generation_config": {"temperature": 0, "maxOutputTokens": 1536},
              "context_budget": {"max_chars": 12000, "max_tokens": 2500}, "seed": 7,
              "benchmark_queries": len(QIDS), "prompt_chars": sum(len(pair["prompt"]) for pair in pairs),
              "payload": "Four dev questions plus selected university curriculum snippets, metadata and answer schema; no credentials in prompt or artifact.",
              "release_eligible": False, "test_or_holdout_read": False,
              "historical_retrieval_replayed": True, "current_serving_measurement": False,
              "score_artifact": SCORES.as_posix(), "score_artifact_sha256": sha256(SCORES),
              "revision_manifest_sha256": sha256(REVISION / "manifest.json"),
              "rubric_sha256": sha256(REVISION / "rubric.partial.json"),
              "grounding_source_sha256": sha256("src/campusai/rag/grounding.py"),
              "runner_sha256": sha256(__file__), "pairs": pairs}
    write_json(output, packet)
    print(json.dumps({key: packet[key] for key in ("status", "benchmark_queries", "max_provider_calls", "prompt_chars")}))


def collect(packet_path: Path, config_path: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    packet = read_json(packet_path)
    if packet["runner_sha256"] != sha256(__file__) or packet["grounding_source_sha256"] != sha256("src/campusai/rag/grounding.py"):
        raise ValueError("prepared runner/grounding changed")
    if len(packet["pairs"]) != 8 or packet["max_provider_calls"] != 8:
        raise ValueError("pilot call ceiling changed")
    import yaml
    from campusai.llm import GeminiClient
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    key = os.environ.get("GEMINI_API_KEY") or config.get("api_key")
    if not key:
        raise ValueError("provider credential missing")
    llm = GeminiClient(key, model=packet["model"], cache=None, max_retries=0, timeout=60)
    calls = []
    llm.generate = recording_generate(llm.generate, calls)
    original_json = llm.generate_json
    llm.generate_json = lambda prompt, **options: original_json(prompt, generationConfig=packet["generation_config"], **options)
    generator = GroundedAnswerGenerator(llm, max_context_chars=packet["context_budget"]["max_chars"],
                                       max_context_tokens=packet["context_budget"]["max_tokens"])
    report = {"schema_version": 1, "status": "IN_PROGRESS", "release_eligible": False,
              "packet_path": packet_path.as_posix(), "packet_sha256": sha256(packet_path),
              "live_provider": True, "answer_cache_enabled": False, "llm_cache_enabled": False,
              "observations": [], "cost": None, "cost_status": "unknown", "attempted_calls": 0}
    try:
        for pair in packet["pairs"]:
            selected = results(pair["evidence"])
            prompt = generator.prompt(pair["question"], selected)
            if prompt != pair["prompt"] or hashlib.sha256(prompt.encode()).hexdigest() != pair["prompt_sha256"]:
                raise ValueError("prepared prompt bytes changed")
            calls.clear()
            answer = generator.answer(pair["question"], selected).to_public_dict()
            report["attempted_calls"] += len(calls)
            report["observations"].append({"qid": pair["qid"], "arm": pair["arm"], "answer": answer,
                "llm_calls": list(calls), "observed_at": datetime.now(timezone.utc).isoformat(),
                "review": {"status": "pending", "answer_sha256": answer_digest(answer)}})
            report["status"] = "PENDING_SEMANTIC_REVIEW"
            write_json(output, report)
            print(json.dumps({"completed_arms": len(report["observations"]), "provider_calls": report["attempted_calls"]}), flush=True)
            if any(call["provider_status"] != "completed" or call["cached"] for call in calls):
                report["status"] = "PROVIDER_FAILURE_PARTIAL"
                write_json(output, report)
                return 1
    finally:
        close = getattr(llm, "close", None)
        if close:
            close()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "collect"))
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.packet)
        return 0
    if not args.config or not args.output:
        parser.error("collect requires --config and --output")
    return collect(args.packet, args.config, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
