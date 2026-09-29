"""Apply an explicit, auditable review decision to a Phase 5 draft.

This is intentionally separate from candidate generation.  It verifies that
answerable quotes still exist at the claimed PDF coordinate, checks the full
release dataset contract, and only then changes ``review_status`` to
``reviewed``.  The caller must provide the reviewer identity explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf as fitz

from evaluation.benchmark_schema import validate_records


def _repair(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def _load_manifest(corpus_dir: Path) -> dict[str, dict]:
    payload = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    return {item["sha256"]: item for item in payload.get("documents", []) if item.get("sha256")}


def _pages(corpus_dir: Path, manifest: dict[str, dict]) -> dict[tuple[str, int], str]:
    result: dict[tuple[str, int], str] = {}
    for path in sorted(corpus_dir.glob("*.pdf")):
        item = next((value for value in manifest.values() if value.get("filename") == path.name), None)
        if not item:
            continue
        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                result[(item["sha256"], page_number)] = page.get_text("text")
    return result


def review(draft_path: Path, output_path: Path, corpus_dir: Path, annotator_id: str) -> list[dict]:
    rows = [json.loads(line) for line in draft_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    structural_errors = validate_records(rows, minimum=400)
    if structural_errors:
        raise ValueError("draft rejected: " + ", ".join(structural_errors[:12]))
    manifest = _load_manifest(corpus_dir)
    pages = _pages(corpus_dir, manifest)
    reviewed: list[dict] = []
    for row in rows:
        item = dict(row)
        item["review_status"] = "reviewed"
        item["annotator_id"] = annotator_id
        source_hash = str(item.get("source_group", ""))
        if source_hash not in manifest:
            raise ValueError(f"{item['id']}: unknown source_group")
        for claim in item.get("gold_claims", []):
            for evidence in claim.get("evidence", []):
                key = (source_hash, int(evidence["page"]))
                page_text = pages.get(key, "")
                if not page_text:
                    raise ValueError(f"{item['id']}: evidence page unavailable")
                if _repair(evidence.get("quote", "")) not in _repair(page_text):
                    raise ValueError(f"{item['id']}: quote not found on claimed page")
                evidence.setdefault("page_range", [int(evidence["page"]), int(evidence["page"])])
        reviewed.append(item)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in reviewed), encoding="utf-8")
    return reviewed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("draft", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/corpus/university"))
    parser.add_argument("--annotator-id", required=True)
    args = parser.parse_args()
    rows = review(args.draft, args.output, args.corpus_dir, args.annotator_id)
    print(json.dumps({
        "status": "reviewed", "count": len(rows),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "annotator_id": args.annotator_id,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
