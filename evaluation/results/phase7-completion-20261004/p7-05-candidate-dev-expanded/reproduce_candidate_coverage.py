"""Dev-only candidate coverage diagnostic on the expanded Phase 7 index.

This intentionally bypasses confidence calibration: candidate generation disables
answer acceptance thresholds and this study measures retrieved evidence only.
It is not a release gate and never reads test/holdout rows.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from campusai.rag.context import benchmark_retrieval_request
from campusai.retrieval.hybrid import HybridRetriever
import campusai.retrieval.table_links as table_links
from evaluation.benchmarks.freeze_human_benchmark import frozen_evidence
from evaluation.common.release_artifacts import sha256, source_identity, write_json
from evaluation.retrieval.evaluate_candidate_coverage import audit_outputs, coverage_errors


def main() -> int:
    study = Path(__file__).resolve().parent
    dev = ROOT / "evaluation/results/phase7-completion-20261004/p7-02-dev-replay/human_retrieval_dev.jsonl"
    index = ROOT / ".tmp/phase7-source-b-restored-p701"
    rows = [json.loads(line) for line in dev.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 889 or any(row.get("split") != "dev" for row in rows):
        raise ValueError("expected the validated 889-row dev-only packet")
    evidence = frozen_evidence(index)
    documents = sorted({doc for doc, _ in evidence})
    identity = source_identity(ROOT)
    original = table_links.linked_table_sources
    parts = {}
    started = datetime.now(timezone.utc).isoformat()
    for label, enabled in (("existing_code_rows", False), ("named_curriculum_rows", True)):
        def linked(query, records, cap, *, include_named_curriculum=False, named_exact_only=False):
            return original(query, records, cap,
                include_named_curriculum=enabled and include_named_curriculum,
                named_exact_only=named_exact_only)
        table_links.linked_table_sources = linked
        retriever = HybridRetriever(index, query_cache_size=0, candidate_limit=40)
        retriever._ensure_loaded(documents)
        # The stored corpus embeddings remain unchanged. This host's PyTorch build
        # is CPU-only, so query embedding uses CPU for this diagnostic replay.
        for _bm25, dense in retriever._indexes.values():
            if dense is not None:
                dense.device = "cpu"
        outputs = {}
        clock = time.perf_counter()
        try:
            for number, row in enumerate(rows, 1):
                values = retriever.generate_candidates(
                    **benchmark_retrieval_request(row, documents), top_k=40, mode="auto")
                outputs[row["qid"]] = [value.to_dict() for value in values]
                if number % 50 == 0:
                    print(f"{label}: {number}/{len(rows)}", flush=True)
        finally:
            table_links.linked_table_sources = original
        metrics = audit_outputs(rows, outputs, documents, 40, evidence)
        raw = study / f"{label}.json.gz"
        with gzip.open(raw, "wt", encoding="utf-8") as stream:
            json.dump({"outputs": outputs, "metrics": metrics}, stream,
                      ensure_ascii=False, allow_nan=False)
        compact = {key: value for key, value in metrics.items()
                   if key not in {"per_query", "candidate_misses"}}
        compact.update(raw_path=raw.name, raw_sha256=sha256(raw),
                       elapsed_seconds=time.perf_counter() - clock,
                       errors=coverage_errors(metrics, .95),
                       misses=[{"qid": miss["qid"], "expected_evidence": miss["expected_evidence"]}
                               for miss in metrics["candidate_misses"]])
        parts[label] = compact
    after = source_identity(ROOT)
    report = {
        "schema_version": 1, "task": "P7-05", "status": "diagnostic",
        "release_eligible": False,
        "purpose": "dev-only candidate evidence coverage and named curriculum linkage ablation",
        "calibration": "not applied: generate_candidates bypasses acceptance threshold by contract",
        "started_at": started, "ended_at": datetime.now(timezone.utc).isoformat(),
        "source_before": identity, "source_after": after, "source_stable": identity == after,
        "dataset_path": dev.relative_to(ROOT).as_posix(), "dataset_sha256": sha256(dev),
        "dataset_records": len(rows), "index_path": index.relative_to(ROOT).as_posix(),
        "index_manifest_sha256": sha256(index / "manifest.json"), "candidate_cap": 40,
        "query_embedding_device": "cpu",
        "parts": parts,
    }
    write_json(study / "candidate_coverage.json", report)
    print(json.dumps({name: {key: part.get(key) for key in
        ("records", "answerable", "negative", "all_gold_recall", "provenance_errors",
         "scope_errors", "errors")} for name, part in parts.items()}, indent=2))
    return 0 if identity == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
