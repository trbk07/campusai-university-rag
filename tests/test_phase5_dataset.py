from evaluation.phase5_dataset import validate_records, validate_release_records


def row(identifier, split="test", answerable=True):
    return {"id": identifier, "split": split, "question": "q", "language": "en", "category": "answerable" if answerable else "no_evidence", "answerable": answerable, "expected_status": "found" if answerable else "no_evidence_found", "gold_claims": [{"text": "fact", "evidence": [{"chunk_id": "c1"}]}] if answerable else [], "gold_abstention_reason": None if answerable else "no_evidence_found"}


def test_phase5_dataset_requires_reviewed_scale_and_all_splits():
    records = [row(str(index), split) for index, split in enumerate(["dev", "test", "holdout"] * 70)]
    assert validate_records(records) == []
    assert "dataset_requires_at_least_200_records" in validate_records(records[:3])


def test_phase5_release_dataset_requires_balanced_holdout_and_categories():
    records = [row(str(index), "test") for index in range(400)]
    errors = validate_release_records(records)
    assert "split_dev_requires_at_least_120" in errors
    assert "split_holdout_requires_at_least_150" in errors
    assert "missing_category_adversarial" in errors
