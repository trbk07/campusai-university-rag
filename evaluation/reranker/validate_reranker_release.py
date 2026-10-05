"""Fail-closed Phase 7 release gate; no partial score can masquerade as 10/10."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


from evaluation.reranker.reranker_release_gates import ARTIFACTS, default_args, validate
from evaluation.common.release_artifacts import read_json, sha256, write_json
from evaluation.reranker.supplemental_gates import SUPPLEMENTAL


SUPPLEMENTAL_ARTIFACTS = {name: filename for _, name, filename in SUPPLEMENTAL.values()}
ALL_ARTIFACTS = {**ARTIFACTS, **SUPPLEMENTAL_ARTIFACTS}


def build_manifest(args, report: dict) -> dict:
    """Build the reviewable package identity only from fully passing evidence."""
    if (report.get("status") != "pass" or report.get("score") != 10.0
            or report.get("through") != "M12" or report.get("all_release_gates_pass") is not True
            or report.get("working_tree_clean") is not True
            or any(report.get("gates", {}).get(f"M{i}", {}).get("status") != "PASS" for i in range(13))
            or any(report.get("supplemental_gates", {}).get(f"S{i}", {}).get("status") != "PASS" for i in range(1, 7))):
        raise ValueError("release manifest rejected: all M0-M12 gates must PASS")
    if validate(args) != report:
        raise ValueError("release validation report changed after validation")
    for name in ALL_ARTIFACTS:
        if report.get("artifact_sha256", {}).get(name) != sha256(getattr(args, name)):
            raise ValueError(f"release evidence changed after validation: {name}")
    model = read_json(args.smoke)["model_identity"]
    calibration = read_json(args.calibration)
    baseline = read_json(args.baseline)
    index_manifest = Path(args.index_dir) / "manifest.json"
    manifest = deepcopy(report)
    manifest.update({
                "model_name": model["model_name"], "model_revision": model["model_revision"],
                "model_sha256": model["model_sha256"], "tokenizer_revision": model["tokenizer_revision"],
                "reranker_model": {"name": model["model_name"], "revision": model["model_revision"],
                                   "sha256": model["model_sha256"]},
                "device": model["device"], "dtype": model["dtype"],
                "candidate_cap": 40, "rerank_cap": calibration["rerank_candidate_cap"],
                "resource_limits": read_json(args.performance)["resource_limits"],
                "route_policy_sha256": sha256(args.route), "route_policy": sha256(args.route),
                "phase6_calibration_sha256": sha256(args.phase6_calibration),
                "phase7_calibration_sha256": sha256(args.calibration),
                "index_manifest_sha256": sha256(index_manifest),
                "benchmark_sha256": baseline["benchmark_sha256"],
                "human_benchmark_sha256": read_json(args.human_manifest)["dataset_sha256"]})
    for name in ("quality", "performance", "security", "rollback", "staging"):
        manifest[name + "_report_sha256"] = sha256(getattr(args, name))
    filename_to_arg = {filename: name for name, filename in ALL_ARTIFACTS.items()}
    for gate in manifest["gates"].values():
        gate["artifact_sha256"] = {filename: sha256(getattr(args, filename_to_arg[filename]))
                                   for filename in gate["artifacts"] if filename in filename_to_arg}
    return manifest


def main() -> int:
    from evaluation.reranker.active_cycle import active_cycle
    cycle = active_cycle()
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=cycle["results_dir"])
    for name in ALL_ARTIFACTS:
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    parser.add_argument("--index-dir", type=Path, default=cycle["index_dir"])
    parser.add_argument("--benchmark-dir", type=Path, default=cycle["benchmark_dir"])
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
    evidence_paths = {Path(getattr(args, name)).resolve() for name in ALL_ARTIFACTS}
    evidence_paths.add(Path(args.phase6_calibration).resolve())
    if args.output.resolve() in evidence_paths:
        parser.error("readiness output must not overwrite gate evidence")
    if parsed.release_manifest:
        if parsed.release_manifest.resolve() in evidence_paths:
            parser.error("release manifest must not overwrite gate evidence")
        if parsed.release_manifest.resolve() == args.output.resolve():
            parser.error("release manifest and readiness output require separate paths")
    report = validate(args)
    manifest = build_manifest(args, report) if parsed.release_manifest else None
    write_json(args.output, report)
    if parsed.release_manifest:
        write_json(parsed.release_manifest, manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
