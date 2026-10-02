"""Dev-only cap sweep. Select quality and latency jointly; never read held-out data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from evaluation.release_artifacts import read_json, require_previous_gates, sha256, write_json, assert_tuning_allowed
from evaluation.reranker_model_options import add_inference_options, inference_cli


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--dtype", choices=("float32", "float16", "bfloat16"), default="float32")
    add_inference_options(parser)
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--dev", type=Path, default=Path("data/benchmark/human_retrieval_dev.jsonl"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--p95-budget-ms", type=float, default=1000)
    parser.add_argument("--low-score-action", choices=("phase6", "abstain"), default="phase6")
    parser.add_argument("--evidence-policy", choices=("probability", "score"), default="probability")
    args = parser.parse_args()
    require_previous_gates("M5", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.dev.parent)
    assert_tuning_allowed(args.results_dir)
    trials = []
    trial_dir = args.results_dir / "reranker_cap_trials"
    for cap in (8, 10, 12, 16, 20):
        output = trial_dir / f"cap-{cap}.json"
        command = [sys.executable, "-m", "evaluation.calibrate_reranker_scores", "--dev", str(args.dev),
                   "--model-dir", str(args.model_dir), "--model-name", args.model_name, "--device", args.device,
                   "--dtype", args.dtype, *inference_cli(args), "--index-dir", str(args.index_dir), "--results-dir", str(args.results_dir),
                   "--phase6-calibration", str(args.results_dir / "phase6_retrieval_calibration.json"),
                   "--route-calibration", str(args.results_dir / "hard_query_route_calibration.json"),
                   "--rerank-cap", str(cap), "--low-score-action", args.low_score_action,
                   "--evidence-policy", args.evidence_policy, "--output", str(output)]
        subprocess.run(command, check=False)
        report = read_json(output)
        trials.append({"rerank_cap": cap, "status": report["status"], "recall": report["recall"],
                       "mrr": report["comparison"]["selected"]["mrr"], "negative_fpr": report["false_positive_rate"],
                       "p95_ms": report["rerank_latency_ms"]["p95"], "eligible_requests": report["eligible_requests"],
                       "fallback_rate": report["fallback_rate"], "timeout_rate": report["timeout_rate"],
                       "invalid_score_rate": report["invalid_score_rate"], "artifact_sha256": sha256(output),
                       "artifact": output.relative_to(args.results_dir).as_posix()})
    passing = [trial for trial in trials if trial["status"] == "pass" and trial["eligible_requests"] > 0
               and trial["p95_ms"] <= args.p95_budget_ms and trial["timeout_rate"] <= .005]
    selected = max(passing, key=lambda trial: (trial["mrr"], trial["recall"], -trial["p95_ms"], -trial["rerank_cap"])) if passing else None
    first = read_json(trial_dir / "cap-8.json")
    bindings = {key: first[key] for key in ("source_sha256", "runtime_sha256", "index_sha256", "phase6_calibration_sha256",
                                            "model_identity_sha256", "training_split_sha256", "route_calibration_sha256")}
    report = {"status": "pass" if selected else "conditional", "calibration_split": "dev", "test_used": False,
              "holdout_used": False, **bindings, "trials": trials, "selected_cap": selected["rerank_cap"] if selected else None,
              "p95_budget_ms": args.p95_budget_ms,
              "selection_policy": "passing dev quality and latency; maximize MRR, recall, then minimize latency and cap"}
    write_json(args.results_dir / "reranker_cap_sensitivity.json", report)
    if selected:
        calibration = read_json(trial_dir / f"cap-{selected['rerank_cap']}.json")
        write_json(args.results_dir / "reranker_score_calibration.json", calibration)
    print(json.dumps(report, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
