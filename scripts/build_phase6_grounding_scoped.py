"""Add explicit document selection when the reviewed question names a PDF.

Selection uses only the question and corpus filenames. Gold claims and source
groups are checked after selection, never used to choose the document.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmark/grounding_reviewed.jsonl"))
    parser.add_argument("--corpus-manifest", type=Path, default=Path("data/corpus/university/manifest.json"))
    parser.add_argument("--index-manifest", type=Path, default=Path(".tmp/phase6-index/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path(".tmp/phase6_grounding_scoped.jsonl"))
    args = parser.parse_args()
    corpus = json.loads(args.corpus_manifest.read_text(encoding="utf-8"))
    indexed = set(json.loads(args.index_manifest.read_text(encoding="utf-8"))["documents"])
    aliases = {Path(entry["filename"]).stem.casefold(): entry["sha256"]
               for entry in corpus["documents"] if entry["sha256"] in indexed}
    rows = [json.loads(line) for line in args.benchmark.read_text(encoding="utf-8").splitlines() if line.strip()]
    scoped = 0
    for row in rows:
        query = str(row["question"]).casefold()
        matched = {doc_id for alias, doc_id in aliases.items()
                   if re.search(rf"(?<![\w]){re.escape(alias)}(?![\w])", query)}
        if len(matched) > 1:
            raise SystemExit(f"ambiguous source titles in question: {row['id']}")
        if matched:
            doc_id = next(iter(matched))
            if row.get("source_group") and row["source_group"] != doc_id:
                raise SystemExit(f"question title disagrees with review source: {row['id']}")
            row["selected_doc_ids"] = [doc_id]
            row["selection_provenance"] = "explicit_document_title_in_question"
            scoped += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"records": len(rows), "explicitly_scoped": scoped,
                      "unscoped": len(rows) - scoped, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
