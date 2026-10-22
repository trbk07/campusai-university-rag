"""Audit Phase 5 inputs without rewriting gold, review labels or old reports."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

from evaluation.benchmarks.benchmark_schema import validate_release_records
from evaluation.common.release_artifacts import source_identity, write_json
from campusai.rag.grounding import validate_quote


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root: Path, benchmark: Path, index: Path) -> dict:
    rows = [json.loads(line) for line in benchmark.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = []
    for path in sorted(index.glob("*/bm25.json")):
        chunks.extend(json.loads(path.read_text(encoding="utf-8")).get("items", []))
    quote_checks = []
    for row in rows:
        for claim in row.get("gold_claims", []):
            for evidence in claim.get("evidence", []):
                candidates = [chunk for chunk in chunks if chunk.get("doc_id") == evidence.get("doc_id")
                              and chunk.get("page_range", [chunk.get("page"), chunk.get("page")])[0]
                              <= evidence["page"]
                              <= chunk.get("page_range", [chunk.get("page"), chunk.get("page")])[1]]
                quote_checks.append({"id": row["id"], "claim_id": claim.get("claim_id"),
                    "doc_id": evidence["doc_id"], "page": evidence["page"],
                    "quote_in_indexed_source": any(validate_quote(evidence.get("quote", ""), chunk["content"])
                                                   for chunk in candidates)})
    files = [benchmark, root / "plan.md", root / "configs/grounding_release.json",
             root / "data/benchmark/grounding_calibration.json", index / "manifest.json"]
    for directory in ("src/campusai/rag", "evaluation/grounding"):
        files.extend(sorted((root / directory).glob("*.py")))
    # A source title is not proof that a rule applies to the current year.
    # Flag these existing rows for review rather than changing their labels.
    temporal_review = [row["id"] for row in rows if row.get("answerable")
                       and "current academic year" in row.get("question", "").casefold()
                       and not any(re.search(r"\b(?:19|20)\d{2}\b", claim.get("text", ""))
                                   for claim in row.get("gold_claims", []))]
    errors = validate_release_records(rows)
    return {
        "schema_version": 1, "reviewer": "Codex - Automated AI Review",
        "source_identity": source_identity(root),
        "status": "INPUTS_REQUIRE_REVIEW" if errors or temporal_review else "STRUCTURAL_CHECKS_PASS",
        "benchmark_records": len(rows), "split_counts": dict(Counter(row["split"] for row in rows)),
        "category_counts": dict(Counter(row["category"] for row in rows)),
        "annotator_counts": dict(Counter(row.get("annotator_id") for row in rows)),
        "review_metadata_is_human_signoff": False,
        "dataset_errors": errors, "temporal_answer_relevance_review_ids": temporal_review,
        "source_quote_checks": quote_checks,
        "source_quote_matches": sum(check["quote_in_indexed_source"] for check in quote_checks),
        "source_quote_population": len(quote_checks),
        "bindings": {path.resolve().relative_to(root).as_posix(): digest(path) for path in files if path.is_file()},
        "limitations": ["Index quote fidelity does not establish that the gold answers the question.",
                        "Previously exposed splits cannot be described as fresh holdout.",
                        "No model generation or independent human annotation was performed by this audit."],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/grounding_reviewed.jsonl"))
    parser.add_argument("--index", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/phase5-input-audit-20261016.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    report = audit(root, args.benchmark, args.index)
    write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("status", "benchmark_records", "dataset_errors",
                     "source_quote_matches", "source_quote_population", "temporal_answer_relevance_review_ids")},
                     ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
