"""Annotation contract and split hygiene checks for Phase 5 datasets."""

from __future__ import annotations

from collections import Counter
import re
import unicodedata
from evaluation.benchmarks.families import question_template, record_families


CATEGORIES = {
    "answerable", "multi_evidence", "table", "document_does_not_mention",
    "no_evidence", "conflict", "ambiguous", "adversarial",
    "temporal/stale_source", "numeric_contradiction", "partial_support",
    "provider_abstention",
}
ABSTENTION_REASONS = {
    "no_evidence_found", "document_does_not_mention", "conflicting_evidence",
    "ambiguous_question", "provider_abstention", "unsupported_claim", "contradicted_claim",
}
SPLITS = {"dev", "test", "holdout"}
LANGUAGES = {"vi", "en", "mixed"}
RELEASE_SPLIT_MINIMUMS = {"dev": 120, "test": 130, "holdout": 150}
RELEASE_SPLIT_MINIMUM_POSITIVE_RATIO = 0.25


def disclosed_gold_claims(record: dict) -> list[str]:
    """Find the legacy authoring suffix that copied the answer into a query.

    This is a bounded benchmark hygiene check, not a ban on normal fact-check
    questions containing names, numbers or a statement to verify. It does not
    rewrite questions or feed annotation data into runtime inference.
    """
    question = record.get("question")
    if not isinstance(question, str):
        return []
    parts = re.split(r"\btopic\s*:\s*", question, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return []
    normalize = lambda text: " ".join(unicodedata.normalize("NFC", text).casefold().split())
    suffix = normalize(parts[1])
    claims = record.get("gold_claims")
    if not isinstance(claims, list):
        return []
    return [str(claim.get("claim_id", index)) for index, claim in enumerate(claims)
            if isinstance(claim, dict) and isinstance(claim.get("text"), str)
            and len(normalize(claim["text"])) >= 12
            and suffix.endswith(normalize(claim["text"]))]


def validate_records(records: list[dict], *, minimum: int = 200) -> list[str]:
    errors: list[str] = []
    if len(records) < minimum:
        errors.append(f"dataset_requires_at_least_{minimum}_records")
    ids = [record.get("id") for record in records]
    if any(not isinstance(identifier, str) or not identifier.strip() for identifier in ids):
        errors.append("missing_ids")
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
        if record.get("language") not in LANGUAGES:
            errors.append(f"row_{index}_invalid_language")
        if record["category"] not in CATEGORIES:
            errors.append(f"row_{index}_invalid_category")
        if bool(record["answerable"]) and record.get("expected_status") != "found":
            errors.append(f"row_{index}_answerable_status_invalid")
        if not bool(record["answerable"]) and record.get("expected_status") not in ABSTENTION_REASONS:
            errors.append(f"row_{index}_abstention_status_invalid")
        if not bool(record["answerable"]) and record.get("expected_status") != record.get("gold_abstention_reason"):
            errors.append(f"row_{index}_expected_status_reason_mismatch")
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


def validate_release_records(records: list[dict], *, acceptance_scope: str = "public_release") -> list[str]:
    """Apply the non-negotiable independent benchmark release gates."""
    errors = validate_records(records, minimum=400)
    counts = Counter(record.get("split") for record in records)
    for split, minimum in RELEASE_SPLIT_MINIMUMS.items():
        if counts[split] < minimum:
            errors.append(f"split_{split}_requires_at_least_{minimum}")
        split_records = [record for record in records if record.get("split") == split]
        if not any(bool(record.get("answerable")) for record in split_records):
            errors.append(f"split_{split}_requires_answerable_cases")
        if not any(not bool(record.get("answerable")) for record in split_records):
            errors.append(f"split_{split}_requires_abstention_cases")
        if split_records:
            positive_count = sum(bool(record.get("answerable")) for record in split_records)
            negative_count = len(split_records) - positive_count
            minimum_positive = max(1, int(minimum * RELEASE_SPLIT_MINIMUM_POSITIVE_RATIO))
            if positive_count < minimum_positive:
                errors.append(f"split_{split}_answerable_below_{minimum_positive}")
            if negative_count < minimum_positive:
                errors.append(f"split_{split}_abstention_below_{minimum_positive}")
    categories = Counter(record.get("category") for record in records)
    for category in CATEGORIES:
        if not categories[category]:
            errors.append(f"missing_category_{category}")
    for index, record in enumerate(records):
        if disclosed_gold_claims(record):
            errors.append(f"row_{index}_gold_disclosed_in_question")
        for field in ("source_group", "template_group", "semantic_topic", "adversarial_pattern"):
            if not str(record.get(field, "")).strip():
                errors.append(f"row_{index}_{field}_missing")
        if record.get("review_status") != "reviewed":
            errors.append(f"row_{index}_not_independently_reviewed")
        if not str(record.get("annotator_id", "")).strip():
            errors.append(f"row_{index}_annotator_missing")
        if (not record.get("answerable")
                and record.get("gold_abstention_reason") not in ABSTENTION_REASONS):
            errors.append(f"row_{index}_gold_abstention_reason_invalid")
        if record.get("answerable"):
            for claim_index, claim in enumerate(record.get("gold_claims", [])):
                if not isinstance(claim, dict) or not str(claim.get("text", "")).strip():
                    errors.append(f"row_{index}_gold_claim_{claim_index}_text_missing")
                if not isinstance(claim.get("evidence"), list) or not claim.get("evidence"):
                    errors.append(f"row_{index}_gold_claim_{claim_index}_evidence_missing")
                for evidence_index, evidence in enumerate(claim.get("evidence", [])):
                    if not isinstance(evidence, dict):
                        errors.append(f"row_{index}_gold_claim_{claim_index}_evidence_{evidence_index}_invalid")
                        continue
                    if not str(evidence.get("doc_id", "")).strip() or not isinstance(evidence.get("page"), int) or evidence.get("page", 0) < 1:
                        errors.append(f"row_{index}_gold_claim_{claim_index}_evidence_{evidence_index}_coordinate_invalid")
                    if not str(evidence.get("quote", "")).strip():
                        errors.append(f"row_{index}_gold_claim_{claim_index}_evidence_{evidence_index}_quote_missing")
                    if evidence.get("page_range") is not None:
                        page_range = evidence.get("page_range")
                        if (not isinstance(page_range, list) or len(page_range) != 2
                                or not all(isinstance(value, int) and value >= 1 for value in page_range)
                                or not page_range[0] <= evidence["page"] <= page_range[1]):
                            errors.append(f"row_{index}_gold_claim_{claim_index}_evidence_{evidence_index}_page_range_invalid")
    # A group is allowed to occur in only one split. This prevents the same
    # source/template/topic or adversarial pattern from leaking calibration
    # information into test/holdout while keeping IDs unique.
    for field in ("source_group", "template_group", "semantic_topic", "adversarial_pattern"):
        groups: dict[str, set[str]] = {}
        for record in records:
            value = str(record.get(field, "")).strip()
            if value:
                groups.setdefault(value, set()).add(str(record.get("split")))
        for value, splits in groups.items():
            if len(splits) > 1:
                errors.append(f"{field}_cross_split_leakage_{value}")
    # Split-specific names such as dev-page-template-0 / test-page-template-0
    # must not conceal the same observable question template in both splits.
    derived_templates: dict[str, set[str]] = {}
    for record in records:
        question = record.get("question")
        if isinstance(question, str) and question.strip():
            derived_templates.setdefault(question_template(question), set()).add(str(record.get("split")))
    for template, splits in derived_templates.items():
        if len(splits) > 1:
            errors.append(f"derived_template_cross_split_leakage_{template}")
    families: dict[tuple[str, str], set[str]] = {}
    for index, record in enumerate(records):
        for family in record_families(record):
            families.setdefault(family, set()).add(str(record.get("split")))
        if record.get("official_evaluation_eligible") is False:
            errors.append(f"row_{index}_official_evaluation_ineligible")
        if acceptance_scope != "phase5_acceptance" and record.get("split") == "holdout" and (
                record.get("fresh_holdout") is False
                or record.get("exposure_status") == "previously_exposed"):
            errors.append(f"row_{index}_holdout_previously_exposed")
    for (kind, value), splits in families.items():
        if len(splits) > 1:
            errors.append(f"derived_{kind}_family_cross_split_leakage_{value}")
    return sorted(set(errors))
