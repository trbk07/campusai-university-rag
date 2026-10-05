"""Audit the already measured four-response S2 replay without API calls."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from evaluation.benchmarks.audit_context_rebind import audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-results", type=Path,
                        default=Path("evaluation/results/phase7-source-context-20261003-r16"))
    parser.add_argument("--results", type=Path,
                        default=Path("evaluation/results/phase7-source-context-20261003-r17"))
    parser.add_argument("--old-benchmark", type=Path,
                        default=Path("data/benchmark/phase7_review_cycles/phase7-release-20261003-r4"))
    parser.add_argument("--benchmark", type=Path,
                        default=Path("data/benchmark/phase7_review_cycles/phase7-release-20261003-r11"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--output", type=Path,
                        default=Path("evaluation/results/phase7-source-context-20261003-r17/s2_rebind_audit.json"))
    args = parser.parse_args(argv)
    original = args.old_results / "raw/context_lifecycle_observations_4f09097cecf0d952.json"
    rebound = args.results / "raw/context_lifecycle_observations_rebound_618a6ef.json"
    report = audit(original, rebound, args.old_benchmark, args.benchmark, args.results, args.index_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": sum(report["checks"].values()),
                      "check_count": len(report["checks"]), "s2": report["supplemental_s2_status"],
                      "errors": report["errors"], "output": args.output.as_posix()}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
