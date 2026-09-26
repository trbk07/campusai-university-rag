"""Run the Phase 5 grounding evaluator against the existing university fixture path.

This is a reproducible smoke benchmark. It intentionally reports the dataset
size so the separate 400-record release gate cannot be bypassed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.metrics_grounding import evaluate_grounding
from evaluation.run_phase4_basic_rag import FixtureLLM, fixture_document, load_records
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.schemas import validate_response
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.index_builder import build_document_indexes
from campusai.retrieval.hybrid import HybridRetriever


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="data/benchmark/phase4_basic_rag.jsonl")
    parser.add_argument("--output", default="evaluation/results/phase5_grounding.json")
    parser.add_argument("--mode", choices=("fixture", "runtime"), default="fixture")
    args = parser.parse_args()
    records = load_records(args.benchmark)
    with tempfile.TemporaryDirectory(prefix="campusai-phase5-") as temp:
        root = Path(temp) / "index"
        for name in ("graduation_conditions", "prerequisites"):
            build_document_indexes(fixture_document(name), root, dense_model="fallback-hash-256")
        llm = FixtureLLM()
        service = CampusAIQueryService(HybridRetriever(root, query_cache_size=0), GroundedAnswerGenerator(llm, max_context_chars=8000, max_context_tokens=1800))
        rows = []
        for record in records:
            llm.active = record
            answer = service.ask(record["question"], language=record.get("language", "vi"))
            payload = answer.to_dict()
            internal_valid, internal_errors = validate_response(payload, include_internal=True)
            public_valid, public_errors = validate_response(answer.to_public_dict())
            schema_valid = internal_valid and public_valid
            schema_errors = tuple(internal_errors) + tuple(public_errors)
            expected_reason = None
            if not record.get("answerable"):
                expected_reason = "no_evidence_found" if record.get("category") == "out_of_corpus" else "ambiguous_question"
            rows.append({
                **payload,
                "id": record["id"],
                "split": record.get("split", "test"),
                "answerable": bool(record.get("answerable")),
                "gold_abstention_reason": expected_reason,
                "gold_expected_status": "found" if record.get("answerable") else expected_reason,
                "gold_claims": [{"text": record.get("gold_answer", ""), "evidence": record.get("gold_evidence", [])}] if record.get("answerable") else [],
                "schema_valid": schema_valid,
                "schema_errors": list(schema_errors),
                "citation_valid": all(citation.get("page", 0) > 0 for citation in payload.get("citations", [])),
            })
    metrics = evaluate_grounding(rows)
    split_metrics = {}
    category_metrics = {}
    for key in ("split", "category"):
        values = sorted({record.get(key) for record in records if record.get(key) is not None})
        target = split_metrics if key == "split" else category_metrics
        for value in values:
            selected = [row for row, record in zip(rows, records) if record.get(key) == value]
            target[value] = evaluate_grounding(selected)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[1], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "working-tree"
    benchmark_path = Path(args.benchmark)
    report = {
        "schema_version": 2, "phase": "phase5", "mode": args.mode,
        "benchmark": str(benchmark_path), "dataset_count": len(records),
        "benchmark_sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
        "metadata": {"commit": commit, "working_tree": bool(not commit or commit == "working-tree")},
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "pid": os.getpid()},
        "dataset": {"path": str(benchmark_path), "sha256": hashlib.sha256(benchmark_path.read_bytes()).hexdigest(),
                    "version": "phase5-independent-v1"},
        "policy_version": "phase5-v1", "calibration_artifact_version": None,
        "metrics": metrics, "split_metrics": split_metrics, "category_metrics": category_metrics, "rows": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"dataset_count": len(records), "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
