"""Reproduce the P7-06 dev gold-claim/evidence input audit."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.common.release_artifacts import sha256, write_json


def audit(benchmark: Path, index_dir: Path) -> dict:
    dev_path = benchmark / "human_retrieval_dev.jsonl"
    rows = [json.loads(line) for line in dev_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = {}
    for path in sorted(index_dir.glob("*/bm25.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("items", []):
            chunks[item["chunk_id"]] = item

    positives = [row for row in rows if row.get("answerable") is True]
    missing_claims = [row for row in positives if not row.get("expected_claims")]
    errors = []
    evidence_counts = Counter()
    for row in positives:
        evidence = row.get("gold_evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append({"qid": row.get("qid"), "error": "positive_without_gold_evidence"})
            continue
        evidence_counts[str(len(evidence))] += 1
        for item in evidence:
            source = chunks.get(item.get("chunk_id"))
            if source is None:
                errors.append({"qid": row.get("qid"), "error": "missing_chunk", "chunk_id": item.get("chunk_id")})
                continue
            for field in ("doc_id", "page"):
                if item.get(field) != source.get(field):
                    errors.append({"qid": row.get("qid"), "error": "evidence_binding_mismatch",
                                   "chunk_id": item.get("chunk_id"), "field": field})

    missing_ids = [row["qid"] for row in missing_claims]
    return {
        "schema_version": 1,
        "task": "P7-06-dev-gold-input-audit",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "CLAIM_GOLD_MISSING; SOURCE_BINDINGS_AUDITED",
        "release_eligible": False,
        "cycle": benchmark.as_posix(),
        "benchmark_sha256": sha256(dev_path),
        "index_manifest_sha256": sha256(index_dir / "manifest.json"),
        "counts": {
            "dev_rows": len(rows),
            "positive_rows": len(positives),
            "positive_missing_expected_claims": len(missing_claims),
            "positive_without_separate_expected_answer_field": sum(not row.get("expected_answer") for row in positives),
            "positive_missing_both_answer_and_claims": sum(
                not row.get("expected_answer") and not row.get("expected_claims") for row in positives),
            "positive_rows_with_evidence_refs_matching_source_index": len(positives) - len({
                error["qid"] for error in errors}),
            "evidence_item_count_by_row": dict(sorted(evidence_counts.items())),
            "binding_error_count": len(errors),
        },
        "missing_claim_qids": missing_ids,
        "binding_errors": errors,
        "interpretation": (
            "This audit checks physical chunk/document/page bindings only. It does not infer or approve "
            "answer claims, completeness, semantic support, or suitability for held-out evaluation. "
            "Rows without expected answers/claims require source-level claim authoring and an attributable review."
        ),
        "inputs": [
            {"path": dev_path.as_posix(), "sha256": sha256(dev_path)},
            {"path": (index_dir / "manifest.json").as_posix(), "sha256": sha256(index_dir / "manifest.json")},
            {"path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
             "sha256": sha256(Path(__file__))},
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path,
                        default=Path("data/benchmark/phase7_review_cycles/phase7-release-20261004-r18"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output", type=Path,
                        default=Path("evaluation/results/phase7-completion-20261004/p7-06_dev_claim_input_audit.json"))
    args = parser.parse_args(argv)
    report = audit(args.benchmark, args.index_dir)
    write_json(args.output, report)
    print(json.dumps({"status": report["status"], "counts": report["counts"], "output": str(args.output)}))
    return 0 if not report["binding_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
