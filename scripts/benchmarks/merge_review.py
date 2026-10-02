"""Merge an independent Phase 5 review overlay into a draft benchmark.

The reviewer may correct claims, evidence, category, answerability and
abstention reason, but cannot silently move a row across a frozen split or
source/template group. The resulting file is still validated by the release
dataset checker.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FROZEN_FIELDS = ("split", "source_group", "template_group", "semantic_topic", "adversarial_pattern")


def _load(path: Path) -> dict[str, dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = {str(row.get("id")): row for row in rows}
    if len(result) != len(rows) or "None" in result:
        raise ValueError(f"duplicate or missing IDs in {path}")
    return result


def merge(draft_path: Path, review_path: Path) -> list[dict]:
    draft, review = _load(draft_path), _load(review_path)
    if set(draft) != set(review):
        raise ValueError("review IDs must exactly match draft IDs")
    merged = []
    for identifier in draft:
        base, overlay = draft[identifier], review[identifier]
        for field in FROZEN_FIELDS:
            if overlay.get(field) != base.get(field):
                raise ValueError(f"review changed frozen field {field} for {identifier}")
        if overlay.get("review_status") != "reviewed":
            raise ValueError(f"row {identifier} is not marked reviewed")
        if not str(overlay.get("annotator_id", "")).strip() or overlay.get("annotator_id") == "auto-draft":
            raise ValueError(f"row {identifier} has no independent annotator")
        merged_row = dict(base)
        merged_row.update(overlay)
        merged.append(merged_row)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = merge(args.draft, args.review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"status": "merged", "count": len(rows), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
