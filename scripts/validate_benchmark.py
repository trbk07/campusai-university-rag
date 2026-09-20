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
    parser.add_argument("--split", default="dev")
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.path).read_text(encoding="utf-8").splitlines() if line.strip()]
    errors = validate_records(records, args.split, 20 if args.split == "dev" else None)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"valid: {len(records)} records ({args.split})")


if __name__ == "__main__":
    main()
