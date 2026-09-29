"""Generate or validate a fail-closed Phase 5 release package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.phase5_package import build_manifest, validate_package


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build-manifest")
    build.add_argument("--package-dir", type=Path, required=True)
    build.add_argument("--release-candidate", default="phase5-rc1")
    build.add_argument("--benchmark", type=Path, default=Path("data/benchmark/grounding_reviewed.jsonl"))
    build.add_argument("--calibration", type=Path, default=Path("data/benchmark/grounding_calibration.json"))
    build.add_argument("--config", type=Path, default=Path("configs/phase5_release.json"))
    build.add_argument("--adversarial-cases", type=int, default=0)
    build.add_argument("--adversarial-passed", type=int, default=0)
    check = sub.add_parser("validate")
    check.add_argument("package_dir", type=Path)
    check.add_argument("--no-repository-check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.command == "build-manifest":
        cases = args.adversarial_cases
        verification = {"adversarial": {"cases": cases,
                        "pass_rate": (args.adversarial_passed / cases if cases else 0.0)}}
        try:
            manifest = build_manifest(args.package_dir, root=root,
                                      release_candidate=args.release_candidate,
                                      benchmark=args.benchmark, calibration=args.calibration,
                                      config=args.config, verification=verification)
        except ValueError as error:
            print(json.dumps({"status": "fail", "errors": [str(error)]}, indent=2))
            return 1
        path = args.package_dir / "release_manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "created", "path": str(path)}, indent=2))
        return 0
    result = validate_package(args.package_dir, root=root,
                              check_repository=not args.no_repository_check)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
