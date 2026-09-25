"""Validate a benchmark JSONL file before it is used for tuning."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.benchmark import validate_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/benchmark/dev.jsonl")
    parser.add_argument("--split", default=None, help="Expected split; defaults to dev for the legacy dev file")
    parser.add_argument("--expected-count", type=int, default=None, help="Expected number of records")
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.path).read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_split = args.split or ("dev" if Path(args.path).name == "dev.jsonl" else records[0].get("split") if records else "dev")
    expected_count = args.expected_count if args.expected_count is not None else (20 if expected_split == "dev" else None)
    errors = validate_records(records, expected_split, expected_count)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"valid: {len(records)} records ({expected_split})")


if __name__ == "__main__":
    main()
