"""Fail-closed Phase 7 release gate; no partial score can masquerade as 10/10."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


from evaluation.reranker_release_gates import ARTIFACTS, default_args, validate
from evaluation.release_artifacts import sha256, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    for name in ARTIFACTS:
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--phase6-calibration", type=Path)
    parser.add_argument("--through", choices=[f"M{i}" for i in range(13)], default="M12")
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--deployment-ram-bytes", type=int)
    parser.add_argument("--output", type=Path, default=Path(".tmp/reranker-readiness.json"))
    parsed = parser.parse_args()
    args = default_args(parsed.results_dir)
    for name, value in vars(parsed).items():
        if value is not None:
            setattr(args, name, value)
    report = validate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if parsed.release_manifest:
        if report["status"] != "pass" or report["score"] != 10.0:
            raise SystemExit("release manifest rejected: all M0-M12 gates must PASS")
        model = json.loads(args.smoke.read_text(encoding="utf-8"))["model_identity"]
        calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
        manifest = {**report, "reranker_model": {"name": model["model_name"], "revision": model["model_revision"], "sha256": model["model_sha256"]},
                    "device": model["device"], "candidate_cap": 40, "rerank_cap": calibration["rerank_candidate_cap"],
                    "route_policy": sha256(args.route), "phase6_calibration_sha256": sha256(args.phase6_calibration),
                    "phase7_calibration_sha256": sha256(args.calibration)}
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        manifest.update(benchmark_sha256=baseline["benchmark_sha256"],
                        human_benchmark_sha256=json.loads(args.human_manifest.read_text(encoding="utf-8"))["dataset_sha256"])
        for name in ("quality", "performance", "security", "rollback", "staging"):
            manifest[name + "_report_sha256"] = sha256(getattr(args, name))
        write_json(parsed.release_manifest, manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
