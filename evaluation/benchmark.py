"""Schema and split checks for frozen retrieval benchmark files."""

from __future__ import annotations

from collections import Counter


CATEGORIES = {"fact", "table_filter_groupby", "calculation", "comparison", "multi_hop"}
DIFFICULTIES = {"easy", "medium", "hard"}


def validate_records(records: list[dict], expected_split: str = "dev", expected_count: int | None = 20) -> list[str]:
    errors = []
    if expected_count is not None and len(records) != expected_count:
        errors.append(f"expected {expected_count} records, got {len(records)}")
    qids = [record.get("qid") for record in records]
    if len(qids) != len(set(qids)):
        errors.append("qid values must be unique")
    counts = Counter(record.get("category") for record in records)
    for index, record in enumerate(records):
        required = {"qid", "split", "question", "category", "difficulty", "gold_answer", "gold_evidence"}
        missing = required - record.keys()
        if missing:
            errors.append(f"row {index}: missing {sorted(missing)}")
        if record.get("split") != expected_split:
            errors.append(f"row {index}: split must be {expected_split}")
        if record.get("category") not in CATEGORIES:
            errors.append(f"row {index}: invalid category")
        if record.get("difficulty") not in DIFFICULTIES:
            errors.append(f"row {index}: invalid difficulty")
        if not isinstance(record.get("gold_evidence"), list) or not record.get("gold_evidence"):
            errors.append(f"row {index}: gold_evidence must be non-empty")
    if expected_count == 20 and set(counts) == CATEGORIES and any(counts[category] != 4 for category in CATEGORIES):
        errors.append(f"category balance must be 4 each, got {dict(counts)}")
    return errors
