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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.grounding.grounding_metrics import evaluate_grounding
from evaluation.benchmarks.benchmark_schema import validate_release_records
from evaluation.grounding.calibrate_confidence import evaluate_calibrator, risk_at_coverage
from evaluation.grounding.run_basic_rag import FixtureLLM, fixture_document, load_records
from campusai.rag.calibration import load_calibration_artifact
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.grounding import build_context
from campusai.rag.claims import normalize_text
from campusai.rag.schemas import validate_response, validate_release_response
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.index_builder import build_document_indexes
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.calibration import RetrievalPolicy
from campusai.ingestion.pipeline import ingest_document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="data/benchmark/basic_rag.jsonl")
    parser.add_argument("--annotation-benchmark", default=None,
                        help="Original reviewed rows when only explicit document selection was added")
    parser.add_argument("--output", default="evaluation/results/grounding_grounding.json")
    parser.add_argument("--mode", choices=("fixture", "draft", "runtime"), default="fixture")
    parser.add_argument("--calibration-artifact", default=None,
                        help="Locked Phase 5 calibration JSON; required in runtime mode")
    parser.add_argument("--calibration-sha256", default=None)
    parser.add_argument("--corpus-dir", default="data/corpus/university",
                        help="Real PDF corpus used by runtime mode")
    parser.add_argument("--ocr", action="store_true",
                        help="Enable bounded OCR for scan-only PDFs; off by default for reproducible release evaluation")
    parser.add_argument("--index-dir", default=None,
                        help="Reuse a persisted index (for example the Phase 6 release index)")
    parser.add_argument("--retrieval-calibration", default=None,
                        help="Optional Phase 6 retrieval calibration artifact")
    parser.add_argument("--retrieval-mode", default=None,
                        choices=("auto", "bm25", "dense", "hybrid", "hybrid_rrf"))
    args = parser.parse_args()
    records = load_records(args.benchmark)
    benchmark_path = Path(args.benchmark)
    benchmark_sha256 = hashlib.sha256(benchmark_path.read_bytes()).hexdigest()
    annotation_benchmark_sha256 = benchmark_sha256
    if args.annotation_benchmark:
        original_path = Path(args.annotation_benchmark)
        original_records = load_records(original_path)
        stripped = [{key: value for key, value in row.items()
                     if key not in {"selected_doc_ids", "selection_provenance"}} for row in records]
        if stripped != original_records:
            raise SystemExit("scoped benchmark differs from reviewed annotations")
        annotation_benchmark_sha256 = hashlib.sha256(original_path.read_bytes()).hexdigest()
    if args.mode == "runtime":
        dataset_errors = validate_release_records(records)
        if dataset_errors:
            raise SystemExit("runtime benchmark rejected: " + ", ".join(dataset_errors))
        if not args.calibration_artifact:
            raise SystemExit("runtime mode requires --calibration-artifact")
    calibrator = None
    calibration_version = None
    calibration_sha256 = None
    calibration_benchmark_sha256 = None
    calibration_population = None
    if args.calibration_artifact:
        calibration_payload = json.loads(Path(args.calibration_artifact).read_text(encoding="utf-8"))
        calibration_benchmark_sha256 = calibration_payload.get("benchmark_sha256")
        calibration_population = calibration_payload.get("population")
        if args.mode == "runtime":
            if calibration_payload.get("fit_split") != "dev":
                raise SystemExit("runtime calibration must declare fit_split=dev")
            if calibration_payload.get("benchmark_sha256") != annotation_benchmark_sha256:
                raise SystemExit("runtime calibration benchmark checksum mismatch")
        calibrator, calibration_sha256 = load_calibration_artifact(
            args.calibration_artifact, expected_sha256=args.calibration_sha256)
        calibration_version = calibrator.version
    with tempfile.TemporaryDirectory(prefix="campusai-grounding-") as temp:
        root = Path(args.index_dir) if args.index_dir else Path(temp) / "index"
        if args.index_dir:
            if not (root / "manifest.json").is_file():
                raise SystemExit("persisted retrieval index is missing manifest.json")
        elif args.mode == "fixture":
            for name in ("graduation_conditions", "prerequisites"):
                build_document_indexes(fixture_document(name), root, dense_model="fallback-hash-256")
        else:
            store = Path(temp) / "store"
            for pdf_path in sorted(Path(args.corpus_dir).glob("*.pdf")):
                document = ingest_document(pdf_path, store_dir=store, enable_ocr=args.ocr,
                                           ocr_max_pages=50, ocr_timeout_seconds=120)
                if document.status == "succeeded":
                    build_document_indexes(document, root, dense_model="fallback-hash-256")
        llm = FixtureLLM()
        policies = {}
        if args.retrieval_calibration:
            retrieval_policy = RetrievalPolicy.from_report(
                args.retrieval_calibration, expected_mode="hybrid_rrf")
            policies[retrieval_policy.mode] = retrieval_policy
        service = CampusAIQueryService(
            HybridRetriever(root, query_cache_size=0, policies=policies),
            GroundedAnswerGenerator(llm, max_context_chars=16000, max_context_tokens=6000,
                                    calibrator=calibrator),
        )
        rows = []
        for record in records:
            llm.active = record
            answer = service.ask(record["question"], top_k=12,
                                 doc_ids=record.get("selected_doc_ids"),
                                 language=record.get("language", "vi"),
                                 mode=args.retrieval_mode)
            retrieved = service.last_retrieval
            gold_evidence = [evidence for claim in (record.get("gold_claims") or [])
                             for evidence in claim.get("evidence", [])]
            gold_coords = {(item.get("doc_id"), int(item.get("page", 0)))
                           for item in gold_evidence}
            retrieved_coords = {
                (item.doc_id, page)
                for item in retrieved
                for page in range(
                    int((item.metadata or {}).get("page_range", [item.page, item.page])[0]),
                    int((item.metadata or {}).get("page_range", [item.page, item.page])[1]) + 1,
                )
            }
            context = build_context(retrieved, max_chars=16000, max_tokens=6000)
            context_normalized = normalize_text(context)
            context_gold = any(
                normalize_text(str(item.get("quote", ""))) in context_normalized
                for item in gold_evidence if str(item.get("quote", "")).strip()
            )
            payload = answer.to_dict()
            internal_valid, internal_errors = validate_response(payload, include_internal=True)
            public_payload = answer.to_public_dict()
            public_valid, public_errors = (
                validate_release_response(public_payload)
                if args.mode == "runtime" else validate_response(public_payload)
            )
            schema_valid = internal_valid and public_valid
            schema_errors = tuple(internal_errors) + tuple(public_errors)
            expected_reason = record.get("gold_abstention_reason")
            if expected_reason is None and not record.get("answerable"):
                expected_reason = "no_evidence_found" if record.get("category") == "out_of_corpus" else "ambiguous_question"
            gold_claims = record.get("gold_claims")
            if gold_claims is None and record.get("answerable"):
                gold_claims = [{"text": record.get("gold_answer", ""), "evidence": record.get("gold_evidence", [])}]
            rows.append({
                **payload,
                "id": record["id"],
                "split": record.get("split", "test"),
                "question": record.get("question", ""),
                "language": record.get("language", ""),
                "category": record.get("category", ""),
                "expected_status": record.get("expected_status"),
                "answerable": bool(record.get("answerable")),
                "gold_abstention_reason": expected_reason,
                "gold_expected_status": "found" if record.get("answerable") else expected_reason,
                "gold_claims": gold_claims or [],
                "source_group": record.get("source_group"),
                "template_group": record.get("template_group"),
                "semantic_topic": record.get("semantic_topic"),
                "adversarial_pattern": record.get("adversarial_pattern"),
                "review_status": record.get("review_status"),
                "annotator_id": record.get("annotator_id"),
                "schema_valid": schema_valid,
                "schema_errors": list(schema_errors),
                "citation_valid": public_valid and all(citation.get("page", 0) > 0 for citation in payload.get("citations", [])),
                "retrieval_hit_doc": any(item.doc_id == doc_id for doc_id, _page in gold_coords for item in retrieved),
                "retrieval_hit_page": bool(gold_coords & retrieved_coords),
                "retrieval_hit_chunk": any(
                    item.get("chunk_id") and item.get("chunk_id") in {result.chunk_id for result in retrieved}
                    for item in gold_evidence
                ),
                "gold_evidence_in_context": context_gold,
                "retrieved_pages": sorted({f"{item.doc_id}:{item.page}" for item in retrieved}),
            })
    metrics = evaluate_grounding(rows)
    answerable_rows = [row for row in rows if row.get("answerable")]
    metrics.update({
        "retrieval_hit_doc": round(sum(row["retrieval_hit_doc"] for row in answerable_rows) / max(1, len(answerable_rows)), 6),
        "retrieval_hit_page": round(sum(row["retrieval_hit_page"] for row in answerable_rows) / max(1, len(answerable_rows)), 6),
        "retrieval_hit_chunk": round(sum(row["retrieval_hit_chunk"] for row in answerable_rows) / max(1, len(answerable_rows)), 6),
        "gold_evidence_in_context": round(sum(row["gold_evidence_in_context"] for row in answerable_rows) / max(1, len(answerable_rows)), 6),
    })
    calibration = evaluate_calibrator(rows, calibrator) if calibrator is not None else {}
    risk_metrics = {}
    if calibrator is not None:
        for coverage in (0.80, 0.90):
            risk_metrics[str(coverage)] = risk_at_coverage(rows, calibrator, coverage)
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
    try:
        working_tree = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=Path(__file__).parents[1], text=True
        ).strip())
    except (OSError, subprocess.CalledProcessError):
        working_tree = True
    report = {
        "schema_version": 2, "phase": "grounding", "mode": args.mode,
        "benchmark": str(benchmark_path), "dataset_count": len(records),
        "benchmark_sha256": benchmark_sha256,
        "metadata": {"commit": commit, "working_tree": working_tree},
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "pid": os.getpid()},
        "dataset": {"path": str(benchmark_path), "sha256": benchmark_sha256,
                    "version": "grounding-independent-v1"},
        "policy_version": "grounding-v1", "calibration_artifact_version": calibration_version,
        "calibration_artifact_sha256": calibration_sha256,
        "calibration_benchmark_sha256": calibration_benchmark_sha256,
        "calibration_population": calibration_population,
        "metrics": metrics, "split_metrics": split_metrics, "category_metrics": category_metrics,
        "calibration": calibration, "risk_at_coverage": risk_metrics,
        "risk_population": "holdout", "rows": rows,
    }
    if args.index_dir:
        index_manifest = Path(args.index_dir) / "manifest.json"
        report["phase6_retrieval"] = {
            "index_dir": str(args.index_dir), "mode": args.retrieval_mode,
            "index_manifest_sha256": hashlib.sha256(index_manifest.read_bytes()).hexdigest(),
            "calibration": args.retrieval_calibration,
            "calibration_sha256": (hashlib.sha256(Path(args.retrieval_calibration).read_bytes()).hexdigest()
                                    if args.retrieval_calibration else None),
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"dataset_count": len(records), "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
