"""Review gate for the human-natural Phase 6 challenge benchmark."""

from __future__ import annotations

import json
from pathlib import Path


TAGS = {
    "typo_no_accent", "exact_code", "table", "prerequisite",
    "multi_document", "negative", "ocr_degraded", "ambiguous", "code_switch",
    "short_meaningful",
}
REQUIRED_TAGS = {"typo_no_accent", "exact_code", "table", "prerequisite",
                 "multi_document", "negative", "ambiguous", "short_meaningful",
                 "code_switch", "ocr_degraded"}


def load_human_challenge(path: Path, valid_evidence: set[tuple[str, str]]) -> list[dict]:
    if not path.is_file():
        raise ValueError(f"human challenge file missing: {path}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not 100 <= len(rows) <= 150:
        raise ValueError("human challenge requires 100-150 reviewed questions")
    qids = set()
    queries = set()
    for index, row in enumerate(rows):
        qid = row.get("qid")
        query = " ".join(str(row.get("question", "")).casefold().split())
        if not qid or qid in qids or not query or query in queries:
            raise ValueError(f"duplicate or missing challenge identity at row {index}")
        qids.add(qid)
        queries.add(query)
        if (row.get("author_type") != "human" or not row.get("author") or not row.get("reviewer")
                or row.get("author") == row.get("reviewer")):
            raise ValueError(f"human authorship and independent reviewer required at row {index}")
        if row.get("annotation_status") != "reviewed" or not row.get("source_annotation"):
            raise ValueError(f"reviewed evidence note required at row {index}")
        if row.get("split") != "human_natural" or row.get("language") not in {"vi", "en", "vi-en"}:
            raise ValueError(f"challenge split/language invalid at row {index}")
        if row.get("difficulty") not in {"easy", "medium", "hard"}:
            raise ValueError(f"challenge difficulty invalid at row {index}")
        if not row.get("category") or row.get("expected_route") not in {
                "abstain", "exact_code", "filtered_hybrid_rrf", "hybrid_rrf"}:
            raise ValueError(f"challenge category/expected route invalid at row {index}")
        if not isinstance(row.get("answerable"), bool):
            raise ValueError(f"challenge answerable flag invalid at row {index}")
        tags = row.get("challenge_tags", [])
        if not isinstance(tags, list) or not set(tags) <= TAGS:
            raise ValueError(f"challenge tags invalid at row {index}")
        gold = row.get("gold_evidence")
        if not isinstance(gold, list) or bool(gold) != row["answerable"]:
            raise ValueError(f"challenge answerability/evidence mismatch at row {index}")
        if any((item.get("doc_id"), item.get("chunk_id")) not in valid_evidence for item in gold):
            raise ValueError(f"challenge evidence missing from index at row {index}")
        if not row["answerable"] and "negative" not in tags:
            raise ValueError(f"negative challenge tag required at row {index}")
    if sum(not row["answerable"] for row in rows) < 10:
        raise ValueError("human challenge requires at least 10 negative queries")
    if not {"vi", "en", "vi-en"} <= {row["language"] for row in rows}:
        raise ValueError("human challenge needs vi, en and vi-en questions")
    if not REQUIRED_TAGS <= {tag for row in rows for tag in row["challenge_tags"]}:
        raise ValueError("human challenge category coverage is incomplete")
    if sum(row["answerable"] and row["difficulty"] == "hard" for row in rows) < 10:
        raise ValueError("human challenge needs at least 10 hard answerable questions")
    if sum(row["answerable"] and "exact_code" in row["challenge_tags"] for row in rows) < 10:
        raise ValueError("human challenge needs at least 10 exact-code questions")
    return rows
