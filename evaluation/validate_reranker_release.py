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


def build_manifest(args, report: dict) -> dict:
    """Build the reviewable package identity only from fully passing evidence."""
    if report.get("status") != "pass" or report.get("score") != 10.0 or report.get("through") != "M12":
        raise ValueError("release manifest rejected: all M0-M12 gates must PASS")
    from evaluation.release_artifacts import read_json
    if any(report.get("artifact_sha256", {}).get(name) != sha256(getattr(args, name)) for name in ARTIFACTS):
        raise ValueError("release evidence changed after validation")
    model = read_json(args.smoke)["model_identity"]
    calibration = read_json(args.calibration)
    baseline = read_json(args.baseline)
    manifest = {**report,
                "model_name": model["model_name"], "model_revision": model["model_revision"],
                "model_sha256": model["model_sha256"], "tokenizer_revision": model["tokenizer_revision"],
                "reranker_model": {"name": model["model_name"], "revision": model["model_revision"], "sha256": model["model_sha256"]},
                "device": model["device"], "candidate_cap": 40, "rerank_cap": calibration["rerank_candidate_cap"],
                "resource_limits": read_json(args.performance)["resource_limits"],
                "route_policy_sha256": sha256(args.route), "route_policy": sha256(args.route),
                "phase6_calibration_sha256": sha256(args.phase6_calibration),
                "phase7_calibration_sha256": sha256(args.calibration),
                "benchmark_sha256": baseline["benchmark_sha256"],
                "human_benchmark_sha256": read_json(args.human_manifest)["dataset_sha256"]}
    for name in ("quality", "performance", "security", "rollback", "staging"):
        manifest[name + "_report_sha256"] = sha256(getattr(args, name))
    for gate in manifest["gates"].values():
        gate["artifact_sha256"] = {filename: sha256(getattr(args, name))
                                  for name, filename in ARTIFACTS.items() if filename in gate["artifacts"]}
    return manifest


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
    parser.add_argument("--model-dir", type=Path, help="Recheck physical offline model snapshot")
    parser.add_argument("--deployment-ram-bytes", type=int)
    parser.add_argument("--output", type=Path, default=Path(".tmp/reranker-readiness.json"))
    parsed = parser.parse_args()
    if parsed.release_manifest and parsed.model_dir is None:
        parser.error("--model-dir is required to package a release")
    args = default_args(parsed.results_dir)
    for name, value in vars(parsed).items():
        if value is not None:
            setattr(args, name, value)
    evidence_paths = {Path(getattr(args, name)).resolve() for name in ARTIFACTS}
    if args.output.resolve() in evidence_paths:
        parser.error("readiness output must not overwrite gate evidence")
    report = validate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if parsed.release_manifest:
        if report["status"] != "pass" or report["score"] != 10.0:
            raise SystemExit("release manifest rejected: all M0-M12 gates must PASS")
        if parsed.release_manifest.resolve() in {Path(getattr(args, name)).resolve() for name in ARTIFACTS}:
            raise SystemExit("release manifest must not overwrite gate evidence")
        write_json(parsed.release_manifest, build_manifest(args, report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
