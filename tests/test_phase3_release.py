import json

from evaluation.phase3_release import evidence_errors, load_splits


def test_phase3_release_rejects_missing_independent_splits(tmp_path):
    rows, errors = load_splits(tmp_path)
    assert all(not rows[split] for split in ("dev", "test", "holdout"))
    assert "benchmark_below_400" in errors
    assert "missing_holdout_benchmark" in errors


def test_phase3_release_rejects_cross_split_template_leakage(tmp_path):
    for split in ("dev", "test", "holdout"):
        row = {"qid": split, "split": split, "question": f"Question {split}",
               "answerable": False, "gold_evidence": [], "negative_class": "not_in_corpus",
               "template_group": "shared-template"}
        (tmp_path / f"phase3_retrieval_{split}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    _rows, errors = load_splits(tmp_path)
    assert "source_or_template_leakage" in errors
    assert "independent_annotation_review_missing" in errors


def test_phase3_supporting_evidence_checks_numeric_gates():
    report = {"status": "pass", "index_sha256": "abc", "warm_p50_ms": 151,
              "warm_p95_ms": 100, "warm_p99_ms": 200, "restart_load_ms": 100,
              "error_count": 0, "timeout_count": 0}
    assert "performance_warm_p50_ms" in evidence_errors("phase3_performance.json", report, "abc")
    assert "invalid_phase3_performance.json" in evidence_errors("phase3_performance.json", report, "different")
