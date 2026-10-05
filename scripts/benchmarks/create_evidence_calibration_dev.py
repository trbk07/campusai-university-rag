"""Create source-audited auxiliary dev records for exploratory M5 work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.benchmarks.evidence_calibration_dev import create


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args(argv)
    artifact = create(args.benchmark_dir, args.index_dir, args.output, args.manifest, args.count)
    print(json.dumps({key: artifact[key] for key in ("status", "record_count", "records_sha256",
                                                   "auxiliary_connected_group_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
