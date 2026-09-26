"""Annotation contract and split hygiene checks for Phase 5 datasets."""

from __future__ import annotations

from collections import Counter


CATEGORIES = {
    "answerable", "multi_evidence", "table", "document_does_not_mention",
    "no_evidence", "conflict", "ambiguous", "adversarial",
    "temporal/stale_source", "numeric_contradiction", "partial_support",
    "provider_abstention",
}
SPLITS = {"dev", "test", "holdout"}
RELEASE_SPLIT_MINIMUMS = {"dev": 120, "test": 130, "holdout": 150}


def validate_records(records: list[dict], *, minimum: int = 200) -> list[str]:
    errors: list[str] = []
    if len(records) < minimum:
        errors.append(f"dataset_requires_at_least_{minimum}_records")
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_ids")
    for index, record in enumerate(records):
        required = {"id", "split", "question", "language", "category", "answerable", "expected_status", "gold_claims", "gold_abstention_reason"}
        missing = required - record.keys()
        if missing:
            errors.append(f"row_{index}_missing_{','.join(sorted(missing))}")
            continue
        if record["split"] not in SPLITS:
            errors.append(f"row_{index}_invalid_split")
        if record["category"] not in CATEGORIES:
            errors.append(f"row_{index}_invalid_category")
        if not isinstance(record["gold_claims"], list):
            errors.append(f"row_{index}_claims_not_list")
        if bool(record["answerable"]) and not record["gold_claims"]:
            errors.append(f"row_{index}_answerable_without_claims")
        if not bool(record["answerable"]) and not record["gold_abstention_reason"]:
            errors.append(f"row_{index}_abstention_without_reason")
    counts = Counter(record.get("split") for record in records)
    for split in SPLITS:
        if not counts[split]:
            errors.append(f"missing_split_{split}")
    return errors


def validate_release_records(records: list[dict]) -> list[str]:
    """Apply the non-negotiable independent benchmark release gates."""
    errors = validate_records(records, minimum=400)
    counts = Counter(record.get("split") for record in records)
    for split, minimum in RELEASE_SPLIT_MINIMUMS.items():
        if counts[split] < minimum:
            errors.append(f"split_{split}_requires_at_least_{minimum}")
    categories = Counter(record.get("category") for record in records)
    for category in CATEGORIES:
        if not categories[category]:
            errors.append(f"missing_category_{category}")
    for index, record in enumerate(records):
        if record.get("answerable"):
            for claim_index, claim in enumerate(record.get("gold_claims", [])):
                if not isinstance(claim, dict) or not str(claim.get("text", "")).strip():
                    errors.append(f"row_{index}_gold_claim_{claim_index}_text_missing")
                if not isinstance(claim.get("evidence"), list) or not claim.get("evidence"):
                    errors.append(f"row_{index}_gold_claim_{claim_index}_evidence_missing")
    return sorted(set(errors))
