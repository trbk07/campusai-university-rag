"""Validate a Phase 5 annotation JSONL before calibration or release use."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.benchmarks.benchmark_schema import validate_records, validate_release_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--release", action="store_true",
                        help="Apply the 400-record reviewed release gates")
    args = parser.parse_args()
    records = [json.loads(line) for line in args.path.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors = validate_release_records(records) if args.release else validate_records(records)
    result = {"status": "pass" if not errors else "fail", "count": len(records), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
