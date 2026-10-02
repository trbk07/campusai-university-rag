"""Validate all frozen Phase 6 retrieval splits."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evaluation.benchmarks.retrieval_schema import validate_dataset


def main() -> int:
    paths = {split: Path(f"data/benchmark/hybrid_retrieval_{split}.jsonl")
             for split in ("dev", "test", "holdout")}
    errors, report = validate_dataset(paths, Path("data/corpus/university/manifest.json"))
    value = {"status": "pass" if not errors else "fail", "errors": errors, **report}
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
