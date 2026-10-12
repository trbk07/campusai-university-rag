import copy
import json
from pathlib import Path

import pytest

from evaluation.phase8.validate_automated_review import (
    DEFAULT_REPORT, ROOT, validate, validate_decisions,
)


@pytest.fixture
def saved_review():
    report = json.loads((ROOT / DEFAULT_REPORT).read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (ROOT / report["benchmark"]["path"])
            .read_text(encoding="utf-8").splitlines()]
    markdown = (ROOT / report["review_packet"]["path"]).read_text(encoding="utf-8")
    return rows, report, markdown


def test_saved_ai_review_has_valid_sources_without_promoting_release():
    result = validate()
    assert result["status"] == "PASS"
    assert result["counts"] == {"reviewed": 30, "accept": 28, "reject": 2, "pending": 0}
    assert result["accepted_provenance_pass"] == 28
    assert result["officially_approved"] is False
    assert result["provider_calls"] == 0


@pytest.mark.parametrize("corruption,match", [
    ("missing_row", "coverage"),
    ("duplicate_row", "coverage"),
    ("missing_reason", "incomplete criterion"),
    ("missing_criterion", "missing review criterion"),
    ("accept_rejected", "contradicts criteria"),
    ("human_signature", "must not promote"),
    ("skip_v4_review", "revised question not reviewed"),
    ("changed_question", "row drift"),
    ("markdown_decision", "Markdown decision mismatch"),
])
def test_incomplete_or_forged_reviews_fail_closed(saved_review, corruption, match):
    rows, report, markdown = copy.deepcopy(saved_review)
    if corruption == "missing_row":
        report["decisions"].pop()
    elif corruption == "duplicate_row":
        report["decisions"][-1] = copy.deepcopy(report["decisions"][0])
    elif corruption == "missing_reason":
        report["decisions"][0]["criteria"]["evidence_support"]["reason"] = ""
    elif corruption == "missing_criterion":
        del report["decisions"][0]["criteria"]["clarity"]
    elif corruption == "accept_rejected":
        next(d for d in report["decisions"] if d["decision"] == "Reject")["decision"] = "Accept"
    elif corruption == "human_signature":
        report["human_signed"] = True
    elif corruption == "skip_v4_review":
        d = next(d for d in report["decisions"] if d["qid"].endswith("-04"))
        d["criteria"]["v4_revision_integrity"]["status"] = "NOT_APPLICABLE"
    elif corruption == "changed_question":
        next(r for r in rows if r["qid"].startswith("p8-"))["question"] += " Changed"
    elif corruption == "markdown_decision":
        markdown = markdown.replace("- Decision: [x] Accept  [ ] Reject",
                                    "- Decision: [ ] Accept  [x] Reject", 1)
    with pytest.raises(ValueError, match=match):
        validate_decisions(rows, report, markdown)


@pytest.mark.parametrize("corruption,match", [
    ("benchmark_hash", "benchmark hash mismatch"),
    ("pdf_page", "PDF quote missing"),
    ("source_hash", "source PDF/corpus mismatch"),
])
def test_source_and_page_tampering_fail(saved_review, tmp_path: Path, corruption, match):
    _, report, _ = copy.deepcopy(saved_review)
    if corruption == "benchmark_hash":
        report["benchmark"]["sha256"] = "0" * 64
    elif corruption == "source_hash":
        report["sources"][0]["sha256"] = "0" * 64
    elif corruption == "pdf_page":
        # Both 2 and 3 are in the indexed chunk range; only PDF page 3 actually
        # contains article 4. Range membership alone must not validate the quote.
        next(d for d in report["decisions"]
             if d["qid"] == "p8-fact-excellent-student-floor")["pdf_page"] = 2
    path = tmp_path / "tampered-review.json"
    path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        validate(path)
