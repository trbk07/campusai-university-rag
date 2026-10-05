"""Create S1 lineage observations from an explicit intake export audit."""
from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-audit", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    args = parser.parse_args(argv)
    from evaluation.reranker.build_supplemental_report import main as lineage_main
    return lineage_main(["--gate", "S1", "--review-audit", str(args.review_audit),
                         "--results-dir", str(args.results_dir), "--index-dir", str(args.index_dir),
                         "--benchmark-dir", str(args.benchmark_dir)])


if __name__ == "__main__":
    raise SystemExit(main())
