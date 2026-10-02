"""Exploratory real-corpus latency probe; never a release performance report."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from campusai.retrieval.calibration import RetrievalPolicy
from campusai.retrieval.cross_encoder_provider import (
    ModelIdentity, OfflineCrossEncoderReranker, RerankCandidate, snapshot_sha256,
)
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.common.release_artifacts import sha256, source_identity, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--index-dir", type=Path, default=Path(".tmp/hybrid-index"))
    parser.add_argument("--dev", type=Path, default=Path("data/benchmark/hybrid_retrieval_dev.jsonl"))
    parser.add_argument("--calibration", type=Path, default=Path("evaluation/results/hybrid_retrieval_calibration.json"))
    parser.add_argument("--output", type=Path, default=Path(".tmp/reranker_cpu_latency.json"))
    args = parser.parse_args(argv)
    provider = None
    try:
        rows = [json.loads(line) for line in args.dev.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows or any(row.get("split") != "dev" for row in rows):
            raise ValueError("diagnostic accepts dev-only data; test/holdout access is forbidden")
        # Diagnostics cannot overwrite official gate evidence.
        root = Path(__file__).resolve().parents[2]
        output = args.output.resolve()
        if not any(output.is_relative_to(root / name) for name in (".tmp", ".release")):
            raise ValueError("diagnostic output must be in .tmp or .release")
        selected = [row for row in rows if row.get("answerable") and row.get("difficulty") == "hard"][:3]
        if len(selected) < 3:
            raise ValueError("three hard dev questions required")
        import psutil
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        identity = ModelIdentity("BAAI/bge-reranker-v2-m3", args.model_dir.name,
                                 snapshot_sha256(args.model_dir), args.model_dir.name, device=args.device)
        provider = OfflineCrossEncoderReranker(identity, args.model_dir, timeout_ms=60000)
        started = time.perf_counter()
        provider.warm_up()
        warmup_ms = (time.perf_counter() - started) * 1000
        retriever = HybridRetriever(args.index_dir, query_cache_size=0,
                                   policies={"hybrid_rrf": RetrievalPolicy.from_report(args.calibration)})
        docs = json.loads((args.index_dir / "manifest.json").read_text(encoding="utf-8"))["documents"]
        observations = []
        for row in selected:
            pool = retriever.search(row["question"], row.get("doc_ids", docs), filters=row.get("filters"), mode="auto", top_k=40)
            for cap in (8, 10, 20):
                candidates = [RerankCandidate(f"{item.doc_id}:{item.chunk_id}", item.doc_id, item.chunk_id, item.page,
                                              item.content, item.rank, float(item.fusion_score or 0)) for item in pool[:cap]]
                if len(candidates) != cap:
                    raise ValueError("real candidate pool is smaller than requested diagnostic cap")
                start = time.perf_counter()
                values = provider.score(row["question"], candidates)
                elapsed = (time.perf_counter() - start) * 1000
                observation = {"qid": row["qid"], "cap": cap, "latency_ms": elapsed,
                               "rss_bytes": psutil.Process().memory_info().rss,
                               "candidate_chars": [len(item.content) for item in candidates],
                               "outputs": [{"doc_id": item.doc_id, "chunk_id": item.chunk_id, "page": item.page,
                                            "score": item.reranker_score} for item in values]}
                observations.append(observation)
                print(json.dumps({key: observation[key] for key in ("qid", "cap", "latency_ms", "rss_bytes")}), flush=True)
        report = {"status": "conditional", "evidence_type": "exploratory_dev_latency", "release_eligible": False,
                  **source_identity(root), "model_identity": identity.to_dict(), "model_identity_sha256": identity.fingerprint,
                  "index_sha256": sha256(args.index_dir / "manifest.json"), "dev_sha256": sha256(args.dev),
                  "warmup_ms": warmup_ms, "observations": observations, "provider_metrics": provider.metrics_snapshot()}
        from campusai.retrieval.runtime_provenance import runtime_description
        report["runtime_environment"] = runtime_description()
        if args.device.startswith("cuda"):
            import torch
            properties = torch.cuda.get_device_properties(args.device)
            report["gpu"] = {"name": properties.name, "total_vram_bytes": properties.total_memory,
                             "peak_allocated_bytes": torch.cuda.max_memory_allocated(args.device),
                             "peak_reserved_bytes": torch.cuda.max_memory_reserved(args.device),
                             "torch_version": torch.__version__, "cuda_version": torch.version.cuda}
        write_json(args.output, report)
        return 0
    finally:
        if provider:
            provider.close()
            provider.drain()


if __name__ == "__main__":
    raise SystemExit(main())
