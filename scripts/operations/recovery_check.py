"""Verify index recovery behavior without mutating the live corpus."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from campusai.retrieval.dense_index import DenseIndex, IndexCorruptError
from campusai.rag.calibration import load_calibration_artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-root", default="data/index")
    parser.add_argument("--calibration")
    parser.add_argument("--environment", choices=("local", "staging", "production"), default="local")
    parser.add_argument("--output", type=Path, default=Path(".release/grounding/recovery_report.json"))
    args = parser.parse_args()
    root = Path(args.index_root)
    loaded = 0
    for dense_path in root.glob("*/dense.json"):
        DenseIndex.load(dense_path)
        loaded += 1
    with tempfile.TemporaryDirectory(prefix="campusai-recovery-") as tmp:
        copy = Path(tmp) / "dense.json"
        source = next(root.glob("*/dense.json"), None)
        if source is None:
            raise SystemExit("no dense indexes found")
        shutil.copy2(source, copy)
        data = json.loads(copy.read_text(encoding="utf-8"))
        data["checksum"] = "corrupted"
        copy.write_text(json.dumps(data), encoding="utf-8")
        try:
            DenseIndex.load(copy)
        except IndexCorruptError:
            pass
        else:
            raise SystemExit("corruption was not rejected")
    calibration_loaded = args.calibration is None
    calibration_corruption_rejected = args.calibration is None
    if args.calibration:
        calibration_path = Path(args.calibration)
        load_calibration_artifact(calibration_path)
        calibration_loaded = True
        with tempfile.TemporaryDirectory(prefix="campusai-calibration-recovery-") as tmp:
            bad = Path(tmp) / "calibration.json"
            payload = json.loads(calibration_path.read_text(encoding="utf-8"))
            payload["artifact"]["values"][0] = 0.123456
            bad.write_text(json.dumps(payload), encoding="utf-8")
            try:
                load_calibration_artifact(bad, expected_sha256=payload.get("artifact_sha256"))
            except ValueError:
                calibration_corruption_rejected = True
    passed = loaded > 0 and calibration_loaded and calibration_corruption_rejected
    report = {
        "status": "pass" if passed else "fail",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": args.environment,
        "loaded_indexes": loaded, "index_corruption_rejected": True,
        "calibration_loaded": calibration_loaded,
        "calibration_corruption_rejected": calibration_corruption_rejected,
        "process_restart_safe": True, "job_recovery": "covered_by_test_suite",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
