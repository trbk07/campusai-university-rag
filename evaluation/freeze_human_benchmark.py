"""Validate and freeze independently reviewed human-natural dev/test/holdout.

This tool never authors questions or assigns reviewer approval. Those are
human inputs; missing review/evidence is a blocking condition, not a score.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse

from evaluation.release_artifacts import read_json, sha256, write_json


def normalize_question(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"\w+", text))


def frozen_evidence(index_dir: Path) -> dict[tuple[str, str], dict]:
    manifest = read_json(index_dir / "manifest.json")
    evidence = {}
    for doc_id in manifest["documents"]:
        if not isinstance(doc_id, str) or Path(doc_id).name != doc_id or doc_id in {".", ".."}:
            raise ValueError("invalid manifest document ID")
        data = json.loads((index_dir / doc_id / "bm25.json").read_text(encoding="utf-8"))
        for item in data["items"]:
            key = (doc_id, item["chunk_id"])
            if key in evidence or item.get("doc_id") != doc_id:
                raise ValueError("duplicate or incorrect frozen provenance")
            evidence[key] = item
    return evidence


def validate_rows(rows: list[dict], evidence: dict[tuple[str, str], dict],
                  regression_rows: list[dict] | None = None) -> dict:
    errors = []
    seen_ids, seen_queries, groups = set(), {}, {}
    counts = Counter()
    split_counts = Counter()
    questions = []
    for number, row in enumerate(rows, 1):
        prefix = f"row_{number}"
        if not isinstance(row, dict):
            errors.append(prefix + ":invalid_record")
            continue
        qid, question = row.get("qid"), row.get("question")
        if not isinstance(qid, str) or not qid.strip() or qid in seen_ids:
            errors.append(prefix + ":duplicate_or_missing_qid")
        if isinstance(qid, str):
            seen_ids.add(qid)
        normalized = normalize_question(question) if isinstance(question, str) else ""
        if not normalized or normalized in seen_queries:
            errors.append(prefix + ":duplicate_or_empty_question")
        split = row.get("split")
        if split not in {"dev", "test", "holdout"}:
            errors.append(prefix + ":invalid_split")
        else:
            split_counts[split] += 1
        group = row.get("paraphrase_group")
        if not isinstance(group, str) or not group.strip():
            errors.append(prefix + ":missing_paraphrase_group")
        elif group in groups and groups[group] != split:
            errors.append(prefix + ":paraphrase_group_leakage")
        else:
            groups[group] = split
        if normalized:
            seen_queries[normalized] = split
            questions.append((qid, split, set(normalized.split())))
        if (row.get("author_type") != "human" or row.get("review_status") != "approved"
                or not isinstance(row.get("author"), str) or not row["author"].strip()
                or not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip()
                or row["author"].strip().casefold() == row["reviewer"].strip().casefold()):
            errors.append(prefix + ":independent_human_review_required")
        review = row.get("review_checks", {})
        required = {"natural", "answerability", "evidence_sufficient", "corpus_temporal_scope", "difficulty",
                    "no_paraphrase_leakage", "expected_behavior"}
        if not isinstance(review, dict) or any(review.get(key) is not True for key in required):
            errors.append(prefix + ":incomplete_review_checks")
        if (not isinstance(row.get("source_url"), str)
                or urlparse(row["source_url"]).scheme not in {"https", "http"}
                or not urlparse(row["source_url"]).netloc):
            errors.append(prefix + ":missing_source_url")
        try:
            retrieved = datetime.fromisoformat(row.get("source_retrieved_at", "").replace("Z", "+00:00"))
            if retrieved.tzinfo is None:
                raise ValueError("timezone required")
        except (ValueError, TypeError, AttributeError):
            errors.append(prefix + ":invalid_retrieved_at")
        if row.get("evidence_source") != "frozen_pdf":
            errors.append(prefix + ":frozen_pdf_evidence_required")
        if row.get("difficulty") not in {"easy", "medium", "hard"}:
            errors.append(prefix + ":invalid_difficulty")
        tags = row.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            errors.append(prefix + ":invalid_tags")
            tags = []
        gold = row.get("gold_evidence")
        if not isinstance(row.get("answerable"), bool) or not isinstance(gold, list):
            errors.append(prefix + ":invalid_answerability_or_gold")
            gold = []
        if bool(gold) != row.get("answerable"):
            errors.append(prefix + ":answerability_evidence_mismatch")
        doc_ids, filters = row.get("doc_ids"), row.get("filters", {})
        known_docs = {key[0] for key in evidence}
        if (not isinstance(doc_ids, list) or not doc_ids
                or any(not isinstance(doc, str) or doc not in known_docs for doc in doc_ids)
                or len(set(doc_ids)) != len(doc_ids)):
            errors.append(prefix + ":invalid_doc_scope")
            doc_ids = []
        if not isinstance(filters, dict) or any(not isinstance(key, str) for key in filters):
            errors.append(prefix + ":invalid_filters")
            filters = {}
        for item in gold:
            frozen = evidence.get((item.get("doc_id"), item.get("chunk_id"))) if isinstance(item, dict) else None
            if (not frozen or type(item.get("page")) is not int or item["page"] != frozen.get("page")):
                errors.append(prefix + ":evidence_provenance_mismatch")
            elif item["doc_id"] not in doc_ids or any(
                    str(frozen.get("metadata", {}).get(key, "")).casefold() != str(value).casefold()
                    for key, value in filters.items()):
                errors.append(prefix + ":evidence_scope_mismatch")
        counts["answerable"] += row.get("answerable") is True
        counts["negative"] += row.get("answerable") is False
        counts["hard"] += row.get("difficulty") == "hard" or "multi_hop" in tags
        counts["exact_code"] += "exact_code" in tags
        counts["ambiguous"] += bool({"ambiguous", "abstention"} & set(tags))
    for name, floor in {"records": 150, "answerable": 100, "negative": 20,
                        "hard": 15, "exact_code": 15, "ambiguous": 10}.items():
        actual = len(rows) if name == "records" else counts[name]
        if actual < floor:
            errors.append(f"insufficient_{name}:{actual}<{floor}")
    # Held-out sets need both positives and negatives and routing labels.
    for split in ("dev", "test", "holdout"):
        subset = [row for row in rows if isinstance(row, dict) and row.get("split") == split]
        if not subset or not all(any(row.get("answerable") is answerable for row in subset)
                                 for answerable in (True, False)):
            errors.append(f"insufficient_split_coverage:{split}")
        if not all(any(row.get("difficulty") == label and row.get("answerable") is True for row in subset)
                   for label in ("easy", "hard")):
            errors.append(f"insufficient_route_coverage:{split}")
    for index, (qid, split, tokens) in enumerate(questions):
        for other_qid, other_split, other in questions[index + 1:]:
            if split != other_split and len(tokens) >= 6 and len(other) >= 6:
                if len(tokens & other) / len(tokens | other) >= .85:
                    errors.append(f"suspected_paraphrase_leakage:{qid}:{other_qid}")
    for row in regression_rows or []:
        query = normalize_question(row["question"])
        if query in seen_queries:
            errors.append(f"regression_query_leakage:{row.get('qid')}")
        tokens = set(query.split())
        if len(tokens) >= 6:
            for qid, _, other in questions:
                if len(other) >= 6 and len(tokens & other) / len(tokens | other) >= .85:
                    errors.append(f"regression_paraphrase_leakage:{row.get('qid')}:{qid}")
    return {"schema_version": 1, "phase": 7, "status": "pass" if not errors else "conditional",
            "errors": sorted(set(errors)), "records": len(rows), "counts": dict(counts),
            "split_counts": dict(split_counts), "independent_review_complete": not any(
                "review" in error for error in errors)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("data/benchmark/human_retrieval.jsonl"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--regression-dir", type=Path, default=Path("data/benchmark"))
    args = parser.parse_args()
    from evaluation.release_artifacts import assert_tuning_allowed
    assert_tuning_allowed(args.output_dir, route=True)
    try:
        from evaluation.release_artifacts import require_previous_gates
        require_previous_gates("M1", args.output_dir, index_dir=args.index_dir, benchmark_dir=args.dataset.parent)
        rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
        regression = [json.loads(line) for path in args.regression_dir.glob("phase6_retrieval_*.jsonl")
                      for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        report = validate_rows(rows, frozen_evidence(args.index_dir), regression)
        report.update(dataset_sha256=sha256(args.dataset), index_sha256=sha256(args.index_dir / "manifest.json"))
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"phase": 7, "status": "blocked", "errors": [f"dataset_input:{type(error).__name__}"]}
        rows = []
    write_json(args.output_dir / "human_benchmark_review.json", report)
    manifest = {**report, "frozen": report["status"] == "pass", "split_sha256": {}}
    if report["status"] == "pass":
        for split in ("dev", "test", "holdout"):
            target = args.dataset.parent / f"human_retrieval_{split}.jsonl"
            target.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                      for row in rows if row["split"] == split), encoding="utf-8")
            manifest["split_sha256"][split] = sha256(target)
        manifest["review_sha256"] = sha256(args.output_dir / "human_benchmark_review.json")
    write_json(args.output_dir / "human_benchmark_manifest.json", manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
