"""Phase 6 retrieval benchmark and release data gates."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


SPLIT_COUNTS = {"dev": 140, "test": 130, "holdout": 130}
CATEGORIES = {
    "fact", "exact_code", "table_filter_calculation", "prerequisite",
    "multi_document", "comparison_year", "negative",
}
NEGATIVE_CLASSES = {
    "out_of_domain", "not_in_corpus", "unknown_code", "wrong_year",
    "ambiguous", "prompt_injection", "too_short", "stopwords_only",
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_records(records: list[dict], split: str) -> list[str]:
    errors: list[str] = []
    if len(records) != SPLIT_COUNTS[split]:
        errors.append(f"{split}_count_must_equal_{SPLIT_COUNTS[split]}")
    ids: set[str] = set()
    normalized_questions: set[str] = set()
    for index, row in enumerate(records):
        prefix = f"row_{index}"
        required = {"qid", "split", "question", "language", "category", "query_type",
                    "difficulty", "answerable", "gold_evidence", "expected_retrieval"}
        missing = required - row.keys()
        if missing:
            errors.append(f"{prefix}_missing_{','.join(sorted(missing))}")
            continue
        if row["qid"] in ids:
            errors.append(f"{prefix}_duplicate_qid")
        ids.add(row["qid"])
        question = re.sub(r"\s+", " ", str(row["question"]).casefold()).strip()
        if not question or question in normalized_questions:
            errors.append(f"{prefix}_duplicate_or_empty_question")
        normalized_questions.add(question)
        if row["split"] != split:
            errors.append(f"{prefix}_split_mismatch")
        if row["category"] not in CATEGORIES:
            errors.append(f"{prefix}_category_invalid")
        evidence = row["gold_evidence"]
        if not isinstance(evidence, list):
            errors.append(f"{prefix}_evidence_not_list")
            continue
        if row["answerable"] and not evidence:
            errors.append(f"{prefix}_answerable_without_evidence")
        if not row["answerable"]:
            if evidence:
                errors.append(f"{prefix}_negative_with_evidence")
            if row.get("negative_class") not in NEGATIVE_CLASSES:
                errors.append(f"{prefix}_negative_class_invalid")
        for item in evidence:
            if not isinstance(item, dict) or not item.get("doc_id") or not item.get("chunk_id"):
                errors.append(f"{prefix}_evidence_identity_missing")
            pages = item.get("pages")
            if not isinstance(pages, list) or not pages or not all(isinstance(page, int) and page >= 1 for page in pages):
                errors.append(f"{prefix}_evidence_pages_invalid")
    return errors


def validate_dataset(split_paths: dict[str, Path], manifest_path: Path) -> tuple[list[str], dict]:
    errors: list[str] = []
    all_rows: list[dict] = []
    split_rows: dict[str, list[dict]] = {}
    for split, path in split_paths.items():
        rows = load_jsonl(path)
        split_rows[split] = rows
        all_rows.extend(rows)
        errors.extend(validate_records(rows, split))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = manifest.get("documents", [])
    if len(documents) < 8:
        errors.append("corpus_requires_at_least_8_documents")
    if len({item.get("document_type") for item in documents}) < 4:
        errors.append("corpus_requires_at_least_4_document_types")
    if len({item.get("language") for item in documents}) < 2:
        errors.append("corpus_requires_multilingual_documents")
    questions = [re.sub(r"\s+", " ", str(row.get("question", "")).casefold()).strip() for row in all_rows]
    duplicate_queries = len(questions) - len(set(questions))
    if duplicate_queries:
        errors.append("duplicate_queries")
    group_splits: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in all_rows:
        for field in ("source_group", "template_group"):
            group_splits[(field, str(row.get(field, "")))].add(row["split"])
    leaking = [key for key, splits in group_splits.items() if key[1] and len(splits) > 1]
    if leaking:
        errors.append("split_leakage")
    categories = Counter(row.get("category") for row in all_rows)
    for category in CATEGORIES:
        if not categories[category]:
            errors.append(f"missing_category_{category}")
    manifest_ids = {str(item.get("sha256")) for item in documents}
    referenced_docs = ({item["doc_id"] for row in all_rows for item in row.get("gold_evidence", [])}
                       | {str(row.get("source_group")) for row in all_rows if str(row.get("source_group")) in manifest_ids})
    if len(referenced_docs) < 8:
        errors.append("benchmark_requires_evidence_from_8_documents")
    report = {
        "records": len(all_rows), "documents": len(documents),
        "answerable": sum(bool(row.get("answerable")) for row in all_rows),
        "unanswerable": sum(not bool(row.get("answerable")) for row in all_rows),
        **{split: len(rows) for split, rows in split_rows.items()},
        "categories": dict(sorted(categories.items())),
        "duplicate_queries": duplicate_queries,
        "split_leakage": len(leaking),
        "missing_gold_evidence": sum(bool(row.get("answerable")) and not row.get("gold_evidence") for row in all_rows),
        "referenced_documents": len(referenced_docs),
        "checksums": {split: sha256(path) for split, path in split_paths.items()},
        "manifest_sha256": sha256(manifest_path),
    }
    return sorted(set(errors)), report
