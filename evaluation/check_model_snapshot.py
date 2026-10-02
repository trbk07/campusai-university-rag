"""Offline-only Phase 7 model identity and single-batch smoke evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
)
from campusai.retrieval.runtime_provenance import runtime_description
from evaluation.release_artifacts import require_previous_gates, sha256, source_identity
from evaluation.reranker_model_options import add_inference_options, inference_settings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cpu", help="Explicit cpu, cuda or cuda:N device")
    parser.add_argument("--dtype", choices=("float32", "float16", "bfloat16"), default="float32")
    add_inference_options(parser)
    parser.add_argument("--timeout-ms", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/model_snapshot_smoke.json"))
    parser.add_argument("--results-dir", type=Path, default=Path("evaluation/results"))
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/phase6-index"))
    parser.add_argument("--benchmark-dir", type=Path, default=Path("data/benchmark"))
    parser.add_argument("--exploratory", action="store_true")
    args = parser.parse_args()
    import re
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.model_dir.name):
        raise ValueError("model directory must name an immutable commit revision (40 or 64 hex characters)")
    if not args.exploratory:
        require_previous_gates("M3", args.results_dir, index_dir=args.index_dir, benchmark_dir=args.benchmark_dir)
        from evaluation.release_artifacts import assert_tuning_allowed
        assert_tuning_allowed(args.results_dir, route=True)
    identity = ModelIdentity(args.model_name, args.model_dir.name,
                             snapshot_sha256(args.model_dir), args.model_dir.name,
                             device=args.device, dtype=args.dtype, **inference_settings(args))
    provider = OfflineCrossEncoderReranker(identity, args.model_dir,
                                           timeout_ms=args.timeout_ms)
    started = time.perf_counter()
    try:
        provider.warm_up()
        probe = [
            RerankCandidate("a", "doc", "a", 1,
                            "The course requires introductory mathematics.", 1, .4),
            RerankCandidate("b", "doc", "b", 2,
                            "The tuition fee is paid each semester.", 2, .3),
        ]
        ranking = provider.score("What are the course prerequisites?", probe)
        first_ms = (time.perf_counter() - started) * 1000
        warm_started = time.perf_counter()
        repeated = provider.score("What are the course prerequisites?", probe)
        warm_two_ms = (time.perf_counter() - warm_started) * 1000
        batch = [RerankCandidate(str(index), "doc", str(index), 1,
                                 probe[index % 2].content, index + 1, .4)
                 for index in range(40)]
        warm_batches = {}
        for size in (10, 20, 40):
            batch_started = time.perf_counter()
            provider.score("What are the course prerequisites?", batch[:size])
            warm_batches[str(size)] = round((time.perf_counter() - batch_started) * 1000, 3)
        delta = max(abs(a.reranker_score - b.reranker_score) for a, b in zip(ranking, repeated))
        report = {"schema_version": 1, "phase": 7, "status": "pass" if delta <= 1e-5 and not args.exploratory else "conditional",
                  "deterministic": delta <= 1e-5, "max_score_delta": delta,
                  **source_identity(Path(__file__).resolve().parents[1]),
                  "index_sha256": sha256(args.index_dir / "manifest.json"),
                  "phase6_calibration_sha256": sha256(args.results_dir / "phase6_retrieval_calibration.json"),
                  "model_identity": identity.to_dict(),
                  "runtime_environment": runtime_description(),
                  "model_identity_sha256": identity.fingerprint,
                  "model_files_sha256": {path.relative_to(args.model_dir).as_posix(): sha256(path)
                                         for path in sorted(args.model_dir.rglob("*")) if path.is_file()},
                  "latency_ms": {"first_request": round(first_ms, 3),
                                 "warm_2_candidates": round(warm_two_ms, 3),
                                 "warm_batch_candidates": warm_batches},
                  "ranking": [{"candidate_id": item.candidate_id,
                               "reranker_score": item.reranker_score,
                               "final_rank": item.final_rank} for item in ranking]}
    except Exception as error:
        report = {"schema_version": 1, "phase": 7, "status": "conditional",
                  "model_identity": identity.to_dict(),
                  "error_type": type(error).__name__}
    finally:
        provider.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
