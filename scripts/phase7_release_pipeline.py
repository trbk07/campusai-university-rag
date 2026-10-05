"""Phase 7 input preflight and ordered release stages using explicit evidence.

``preflight`` diagnoses M1/S1 inputs. Other stages use the authoritative release
workflow, including human-freeze with owner policy and intake audit checks.
"""
from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argparse.ArgumentParser(description=__doc__).error("specify preflight or an explicit release stage")
    if argv[0] == "preflight":
        from scripts.benchmarks.check_phase7_review import main as inspect_main
        return inspect_main(argv[1:])
    from evaluation.reranker.release_workflow import main as workflow_main
    return workflow_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
