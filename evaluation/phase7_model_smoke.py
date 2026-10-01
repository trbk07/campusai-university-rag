"""Offline-only Phase 7 model identity and single-batch smoke evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from campusai.retrieval.phase7_reranker import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cpu", help="Explicit cpu, cuda or cuda:N device")
    parser.add_argument("--timeout-ms", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=Path(".tmp/phase7-model-smoke.json"))
    args = parser.parse_args()
    identity = ModelIdentity(args.model_name, args.model_dir.name,
                             snapshot_sha256(args.model_dir), args.model_dir.name,
                             device=args.device)
    provider = OfflineCrossEncoderReranker(identity, args.model_dir,
                                           timeout_ms=args.timeout_ms)
    started = time.perf_counter()
    try:
        probe = [
            RerankCandidate("a", "doc", "a", 1,
                            "The course requires introductory mathematics.", 1, .4),
            RerankCandidate("b", "doc", "b", 2,
                            "The tuition fee is paid each semester.", 2, .3),
        ]
        ranking = provider.score("What are the course prerequisites?", probe)
        first_ms = (time.perf_counter() - started) * 1000
        warm_started = time.perf_counter()
        provider.score("What are the course prerequisites?", probe)
        warm_two_ms = (time.perf_counter() - warm_started) * 1000
        batch = [RerankCandidate(str(index), "doc", str(index), 1,
                                 probe[index % 2].content, index + 1, .4)
                 for index in range(40)]
        warm_batches = {}
        for size in (10, 20, 40):
            batch_started = time.perf_counter()
            provider.score("What are the course prerequisites?", batch[:size])
            warm_batches[str(size)] = round((time.perf_counter() - batch_started) * 1000, 3)
        report = {"schema_version": 1, "phase": 7, "status": "pass",
                  "model_identity": identity.to_dict(),
                  "model_identity_sha256": identity.fingerprint,
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
