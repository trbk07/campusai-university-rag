"""Answer recall must match requested fields rather than extra source metadata."""
import pytest

from scripts.benchmarks.build_phase7_dev_rubric import curriculum_claims


@pytest.mark.parametrize("kind,fields", [
    ("curriculum_credits", ["credits"]),
    ("curriculum_semester", ["semester"]),
    ("curriculum_combined", ["credits", "semester"]),
])
def test_only_requested_fields_are_required(kind, fields):
    row = {"source_validation": {"kind": kind}}
    fact = {"name": "Algebra", "credits": 4, "semester": 1, "doc_id": "doc",
            "chunk_id": "table", "page": 1, "cells_sha256": "source-row-hash"}
    claims = curriculum_claims(row, fact)
    assert [claim["field"] for claim in claims] == fields
    assert [claim["value"] for claim in claims] == [fact[field] for field in fields]
    assert all(claim["source_cells_sha256"] == "source-row-hash" for claim in claims)
    assert all(claim["evidence"] == [{"doc_id": "doc", "chunk_id": "table", "page": 1}] for claim in claims)


def test_unknown_question_template_is_not_automatically_approved():
    with pytest.raises(KeyError):
        curriculum_claims({"source_validation": {"kind": "invented"}}, {})
