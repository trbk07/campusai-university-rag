"""One release command per milestone, with prerequisites and explicit inputs."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from evaluation.common.release_artifacts import read_json, require_previous_gates
from evaluation.reranker.reranker_release_gates import default_args, validate
from evaluation.reranker.reranker_model_options import add_inference_options, inference_cli

STAGES = {
    "baseline": "M0", "human-freeze": "M1", "candidate": "M2", "model": "M3",
    "route": "M4", "calibration": "M5", "quality": "M6", "performance": "M7",
    "security": "M8", "faults": "M9", "rollback": "M10", "staging": "M11", "staging-collect": "M11",
    "validate": "M12", "release": "M12",
}


def commands(args) -> list[list[str]]:
    common = ["--results-dir", str(args.results_dir), "--index-dir", str(args.index_dir),
              "--benchmark-dir", str(args.benchmark_dir)]
    model = ["--model-dir", str(args.model_dir), "--model-name", args.model_name, "--device", args.device]
    simple = {"candidate": "evaluate_candidate_coverage", "quality": "compare_retrieval_quality",
              "rollback": "verify_reranker_rollback"}
    def command(module, *options):
        package = "benchmarks" if module == "freeze_human_benchmark" else (
            "retrieval" if module in {"evaluate_candidate_coverage", "compare_retrieval_quality"} else "reranker")
        return [sys.executable, "-m", f"evaluation.{package}.{module}", *options]
    if args.stage == "candidate":
        return [command(simple[args.stage], *common,
                        "--phase6-calibration", str(args.results_dir / "hybrid_retrieval_calibration.json"),
                        "--output", str(args.results_dir / "candidate_coverage.json"))]
    if args.stage in simple:
        return [command(simple[args.stage], *common)]
    if args.stage == "human-freeze":
        return [command("freeze_human_benchmark", "--dataset", str(args.benchmark_dir / "human_retrieval.jsonl"),
                        "--regression-dir", str(args.benchmark_dir), "--index-dir", str(args.index_dir),
                        "--output-dir", str(args.results_dir))]
    if args.stage == "model":
        return [command("check_model_snapshot", *common, *model, "--dtype", args.dtype, *inference_cli(args), "--output", str(args.results_dir / "model_snapshot_smoke.json")),
                command("check_reranker_faults", *common, "--gate", "M3")]
    if args.stage in {"route", "calibration"}:
        options = ["--results-dir", str(args.results_dir), "--index-dir", str(args.index_dir),
                   "--dev", str(args.benchmark_dir / "human_retrieval_dev.jsonl")]
        if args.stage == "route":
            return [command("calibrate_hard_query_route", *options,
                            "--phase6-calibration", str(args.results_dir / "hybrid_retrieval_calibration.json"),
                            "--output", str(args.results_dir / "hard_query_route_calibration.json"))]
        return [command("sweep_reranker_caps", *options, *model, "--dtype", args.dtype, *inference_cli(args),
                        "--low-score-action", getattr(args, "low_score_action", "phase6"),
                        "--evidence-policy", args.evidence_policy)]
    if args.stage == "performance":
        return [command("measure_reranker_capacity", *common, "--deployment-ram-bytes", str(args.deployment_ram_bytes),
                        "--profile", args.profile),
                command("measure_reranker_http", *common, "--model-dir", str(args.model_dir),
                        "--llm-config", str(args.llm_config), "--deployment-ram-bytes", str(args.deployment_ram_bytes),
                        "--p95-budget-ms", str(args.http_p95_budget_ms))]
    if args.stage == "security":
        return [command("evaluate_reranker_security", *common, "--cases", str(args.cases))]
    if args.stage == "faults":
        return [command("check_reranker_faults", *common, "--gate", "M9")]
    if args.stage == "staging":
        return [command("audit_canary_staging", *common, "--observations", str(args.observations),
                        "--fault-observations", str(args.fault_observations))]
    if args.stage == "staging-collect":
        observations = args.observations or Path(".release/reranker/staging_observations.json")
        faults = args.fault_observations or Path(".release/reranker/staging_fault_observations.json")
        options = [*common, *model, "--output", str(observations), "--fault-output", str(faults),
                   "--environment-id", args.environment_id, "--requests", str(args.staging_requests),
                   "--concurrency", str(args.staging_concurrency)]
        if args.deployment_ram_bytes is not None:
            options += ["--deployment-ram-bytes", str(args.deployment_ram_bytes)]
        return [command("run_canary_staging", *options), command("audit_canary_staging", *common,
                "--observations", str(observations), "--fault-observations", str(faults))]
    options = [*common, "--through", STAGES[args.stage], "--output", str(args.readiness_output)]
    if args.stage == "release":
        options += ["--release-manifest", str(args.release_manifest), "--model-dir", str(args.model_dir)]
    return [command("validate_reranker_release", *options)]


def measurement_environment(args) -> dict[str, str]:
    """Bind evaluation activation to the measured identity, never ambient flags."""
    from campusai.retrieval.cross_encoder_provider import ModelIdentity, snapshot_sha256
    smoke = read_json(args.results_dir / "model_snapshot_smoke.json")
    identity = ModelIdentity(**smoke["model_identity"])
    if (args.model_dir.name != identity.model_revision or snapshot_sha256(args.model_dir) != identity.model_sha256
            or args.device != identity.device or args.model_name != identity.model_name):
        raise ValueError("measurement snapshot/name/device does not match M3")
    env = dict(os.environ)
    env.update(RERANKER_ENABLED="true", RERANKER_DEPLOYMENT="experimental", RERANKER_MODE="hard_only",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               RERANKER_MODEL=identity.model_name, RERANKER_MODEL_REVISION=identity.model_revision,
               RERANKER_MODEL_SHA256=identity.model_sha256, RERANKER_TOKENIZER_REVISION=identity.tokenizer_revision,
               RERANKER_MODEL_DIR=str(args.model_dir.resolve()), RERANKER_DEVICE=identity.device,
               RERANKER_BATCH_SIZE=str(identity.batch_size), RERANKER_MAX_LENGTH=str(identity.max_length),
               RERANKER_INPUT_FORMAT=identity.input_format,
               RERANKER_DTYPE=identity.dtype, RERANKER_SCORE_CACHE_SIZE="0",
               RERANKER_BATCH_WINDOW_MS=str(identity.batch_window_ms), RERANKER_MAX_BATCH_PAIRS=str(identity.max_batch_pairs),
               RERANKER_CANDIDATE_CAP="40", RERANKER_TIMEOUT_MS="1000", RERANKER_QUEUE_LIMIT=str(getattr(args, "queue_limit", 19)),
               RERANKER_WARMUP="true", RERANKER_CALIBRATION=str((args.results_dir / "reranker_score_calibration.json").resolve()))
    return env


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", choices=("float32", "float16", "bfloat16"), default="float32")
    add_inference_options(parser)
    parser.add_argument("--queue-limit", type=int, default=19)
    parser.add_argument("--deployment-ram-bytes", type=int)
    parser.add_argument("--profile", default="cpu-small")
    parser.add_argument("--llm-config", type=Path)
    parser.add_argument("--http-p95-budget-ms", type=int, default=10000)
    parser.add_argument("--cases", type=Path, default=Path("data/benchmark/reranker_adversarial.jsonl"))
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--fault-observations", type=Path)
    parser.add_argument("--environment-id", default="local-staging")
    parser.add_argument("--staging-requests", type=int, default=100)
    parser.add_argument("--staging-concurrency", type=int, default=1)
    parser.add_argument("--low-score-action", choices=("phase6", "abstain"), default="phase6")
    parser.add_argument("--evidence-policy", choices=("probability", "score"), default="probability")
    parser.add_argument("--readiness-output", type=Path, default=Path(".release/reranker/readiness.json"))
    parser.add_argument("--release-manifest", type=Path, default=Path("evaluation/results/reranker_release_manifest.json"))
    args = parser.parse_args(argv)
    measured = {"quality", "performance", "security", "rollback"}
    if args.stage in measured | {"model", "calibration", "release", "staging-collect"} and args.model_dir is None:
        parser.error("--model-dir is required for this stage (local immutable snapshot)")
    if args.stage == "performance" and (args.deployment_ram_bytes is None or args.deployment_ram_bytes <= 0):
        parser.error("--deployment-ram-bytes must be the positive deployment limit")
    if args.stage == "performance" and (args.llm_config is None or not args.llm_config.is_file()):
        parser.error("--llm-config is required for live end-to-end HTTP measurement")
    if not 0 <= args.queue_limit <= 99:
        parser.error("--queue-limit must be between 0 and 99")
    if args.stage == "staging" and (args.observations is None or args.fault_observations is None):
        parser.error("--observations and --fault-observations are required")
    try:
        if args.stage not in {"baseline", "validate"}:
            require_previous_gates(STAGES[args.stage], args.results_dir,
                                   index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
        env = measurement_environment(args) if args.stage in measured else dict(os.environ)
        for command in commands(args):
            run = subprocess.run(command, env=env, check=False)
            if run.returncode:
                return run.returncode
        if args.stage not in {"baseline", "validate", "release"}:
            check = default_args(args.results_dir)
            check.index_dir, check.benchmark_dir, check.through = args.index_dir, args.benchmark_dir, STAGES[args.stage]
            report = validate(check)
            if report["status"] != "pass":
                print("Milestone rejected: " + ", ".join(report["errors"]), file=sys.stderr)
                return 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"Reranker {args.stage}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
