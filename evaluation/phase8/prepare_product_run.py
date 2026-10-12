"""Prepare a hash-bound, zero-egress Phase 8 product-run packet.

This preflight exercises the actual WSGI/query-service path with an offline
LLM recorder. It captures prompts and retrieval evidence but never sends them
to a provider and never treats fallback responses as product quality outputs.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

from campusai.llm.client import LLMResponseError
from campusai.rag.context import benchmark_request
from campusai.web import make_wsgi_app
from evaluation.common.release_artifacts import source_identity
from evaluation.phase8.score_temporal_product_outputs import _index_tree_sha256, _read_jsonl

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK = ROOT / "evaluation/phase8/benchmark_candidate_v5.jsonl"
DEFAULT_INDEX = ROOT / ".tmp/hybrid-index"
DEFAULT_LLM_CONFIG = ROOT / "configs/product_llm.yaml"
DEFAULT_PACKET = ROOT / "evaluation/results/phase8-product-preflight-v5.json"


class _NoCache:
    def get(self, _key):
        return None

    def put(self, _key, _value):
        return None

    def lock(self, _key):
        return nullcontext()

    def close(self):
        return None


class _PreflightLLM:
    """Capture exact prompt/schema pairs then stop before any transport."""

    def __init__(self):
        self.model = "preflight-no-provider"
        self.generation_config = {}
        self.prompts: list[dict] = []

    def generate_json(self, prompt, **options):
        self.prompts.append({"prompt": prompt, "schema": options.get("schema")})
        raise LLMResponseError("Phase 8 offline preflight; provider call disabled")

    def close(self):
        return None


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _request(web, payload: dict) -> tuple[str, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    response: dict = {}
    body = web({"PATH_INFO": "/api/query", "REQUEST_METHOD": "POST",
                "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)},
               lambda status, _headers: response.update(status=status))
    response_body = json.loads(b"".join(body))
    return response.get("status", ""), response_body


def prepare(*, benchmark_path: Path = DEFAULT_BENCHMARK,
            index_dir: Path = DEFAULT_INDEX,
            llm_config: Path = DEFAULT_LLM_CONFIG,
            packet_path: Path = DEFAULT_PACKET,
            app_factory=None) -> dict:
    """Run local product preflight and persist exact prompt/evidence bindings."""
    benchmark_path, index_dir = benchmark_path.resolve(), index_dir.resolve()
    llm_config, packet_path = llm_config.resolve(), packet_path.resolve()
    if packet_path.exists():
        raise FileExistsError(packet_path)
    rows = _read_jsonl(benchmark_path)
    if not rows or len({row.get("qid") for row in rows}) != len(rows):
        raise ValueError("benchmark must contain unique qids")
    index_manifest_path = index_dir / "manifest.json"
    index_manifest = json.loads(index_manifest_path.read_text(encoding="utf-8-sig"))
    doc_ids = index_manifest.get("documents")
    if not isinstance(doc_ids, list) or not doc_ids:
        raise ValueError("bound product index manifest must list documents")

    profile = {
        "CAMPUSAI_INDEX_DIR": str(index_dir),
        "CAMPUSAI_STORE_DIR": str(ROOT / ".tmp/phase8-product-preflight-store"),
        "CAMPUSAI_DEVICE": "cpu",
        "CAMPUSAI_LLM_CONFIG": str(llm_config),
        "CAMPUSAI_INGESTION_WORKERS": "1",
        "CAMPUSAI_RETRIEVAL_CALIBRATION": str(ROOT / ".tmp/phase8-no-calibration.json"),
        "RERANKER_ENABLED": "false",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "OMP_NUM_THREADS": "8",
        "MKL_NUM_THREADS": "8",
    }
    offline_client = _PreflightLLM()
    before = source_identity(ROOT)
    cases = []
    if app_factory is None:
        from scripts.operations.serve import build_application
        app_factory = build_application
    def deny_network(*_args, **_kwargs):
        raise RuntimeError("network access is disabled during Phase 8 preflight")

    with patch.dict(os.environ, profile), \
            patch("scripts.operations.serve.create_llm", return_value=offline_client), \
            patch("urllib.request.urlopen", side_effect=deny_network):
        import torch
        torch.set_num_threads(8)
        application = app_factory()
        try:
            service = application.query_service
            service.cache.close()
            service.cache = _NoCache()
            service.retriever.query_cache_size = 0
            answers = []
            original_ask = service.ask

            def capture_internal(*args, **kwargs):
                answer = original_ask(*args, **kwargs)
                answers.append(answer.to_dict())
                return answer

            service.ask = capture_internal
            web = make_wsgi_app(application)
            for row in rows:
                offline_client.prompts.clear()
                answers.clear()
                request = benchmark_request(row, doc_ids)
                if not isinstance(request.get("filters"), dict):
                    request["filters"] = {}
                started = time.perf_counter()
                status, result = _request(web, request)
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                if status != "200 OK" or result.get("ok") is not True or len(answers) != 1:
                    raise ValueError(f"product preflight failed for {row['qid']}: {status}")
                if len(offline_client.prompts) > 1:
                    raise ValueError(f"product generated multiple prompts for {row['qid']}")
                captured = offline_client.prompts[0] if offline_client.prompts else None
                cases.append({
                    "qid": row["qid"],
                    "split": row.get("split"),
                    "request": request,
                    "answerable": row.get("answerable"),
                    "tags": row.get("tags", []),
                    "planned_provider_call": captured is not None,
                    "prompt": captured["prompt"] if captured else None,
                    "prompt_sha256": hashlib.sha256(captured["prompt"].encode("utf-8")).hexdigest()
                        if captured else None,
                    "schema": captured["schema"] if captured else None,
                    "preflight_internal_response": answers[0],
                    "preflight_public_response": result["answer"],
                    "retrieved_evidence": [item.to_dict() for item in service.last_retrieval],
                    "preflight_latency_ms": elapsed_ms,
                })
        finally:
            application.close()
    after = source_identity(ROOT)
    if after != before:
        raise ValueError("source identity changed during Phase 8 preflight")

    prompt_cases = [case for case in cases if case["planned_provider_call"]]
    packet = {
        "schema_version": 1,
        "phase": 8,
        "status": "OFFLINE_PREFLIGHT_PREPARED_NOT_PRODUCT_ACCEPTANCE",
        "provider_requests_sent": 0,
        "external_egress": False,
        "release_eligible": False,
        "fresh_validation": False,
        "benchmark": {"path": benchmark_path.relative_to(ROOT).as_posix(),
                       "sha256": _digest(benchmark_path), "rows": len(rows),
                       "qids_in_order": [row["qid"] for row in rows]},
        "index": {"path": index_dir.relative_to(ROOT).as_posix(),
                  "manifest_sha256": _digest(index_manifest_path),
                  "tree_sha256": _index_tree_sha256(index_dir)},
        "llm_config": {"path": llm_config.relative_to(ROOT).as_posix(),
                       "sha256": _digest(llm_config)},
        "source_identity": before,
        "profile": profile,
        "provider_call_count_estimate": len(prompt_cases),
        "prompt_characters": sum(len(case["prompt"] or "") for case in cases),
        "cases": cases,
        "limitations": [
            "Preflight answers for rows with prompts are synthetic provider-failure fallbacks and are not product outputs.",
            "Rows without prompts were run through the local product path, but are not a full product acceptance report.",
            "The benchmark is historically exposed and this packet does not establish fresh validation.",
            "Owner review and provider exposure audit remain separate requirements.",
        ],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    with packet_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(packet, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    packet["packet_sha256"] = _digest(packet_path)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--llm-config", type=Path, default=DEFAULT_LLM_CONFIG)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args()
    packet = prepare(benchmark_path=args.benchmark, index_dir=args.index_dir,
                     llm_config=args.llm_config, packet_path=args.packet)
    print(json.dumps({"status": packet["status"], "packet": str(args.packet),
                      "packet_sha256": packet["packet_sha256"],
                      "provider_requests_sent": packet["provider_requests_sent"],
                      "provider_call_count_estimate": packet["provider_call_count_estimate"],
                      "prompt_characters": packet["prompt_characters"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
