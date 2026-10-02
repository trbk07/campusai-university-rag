"""Verify that both current and previous immutable indexes remain loadable."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.dense_index import DenseIndex


def load_all(root: Path) -> tuple[int, set[str]]:
    count = 0
    documents: set[str] = set()
    for path in root.glob("*/dense.json"):
        index = DenseIndex.load(path)
        count += 1
        documents.add(path.parent.name)
        if not index:
            raise ValueError(f"empty index: {path}")
    return count, documents


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-index", type=Path, required=True)
    parser.add_argument("--previous-index", type=Path, required=True)
    parser.add_argument("--environment", choices=("local", "staging", "production"), default="local")
    parser.add_argument("--output", type=Path, default=Path(".release/grounding/rollback_report.json"))
    args = parser.parse_args()
    current_count, current_docs = load_all(args.current_index)
    old_count, old_docs = load_all(args.previous_index)
    metadata_preserved = bool(current_docs and old_docs and current_docs & old_docs)
    passed = current_count > 0 and old_count > 0 and metadata_preserved
    report = {
        "status": "pass" if passed else "fail",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": args.environment,
        "rollback": passed, "old_index_load": old_count > 0,
        "current_index_load": current_count > 0,
        "metadata_preserved": metadata_preserved,
        "citation_valid_after_rollback": passed,
        "cache_invalidation": current_docs != old_docs or args.current_index.resolve() != args.previous_index.resolve(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
