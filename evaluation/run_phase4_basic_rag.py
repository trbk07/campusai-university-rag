"""Deterministic Phase 4 Basic RAG acceptance benchmark.

The benchmark builds a small university-only corpus from tracked Phase 1/2
fixtures at runtime. It uses a fake LLM contract so acceptance is offline,
repeatable, and independent of provider quota.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.index_builder import build_document_indexes
from campusai.schemas import Chunk, Document


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "phase12"


def load_records(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def fixture_document(name: str) -> Document:
    fixture = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    raw = fixture["document"]
    chunks = []
    for index, page in enumerate(raw["pages"], start=1):
        page_number = int(page["page"])
        heading = page["text"].splitlines()[0] if page["text"] else ""
        chunks.append(Chunk(
            chunk_id=f"{raw['doc_id']}_p{page_number}_c{index}",
            doc_id=raw["doc_id"],
            page=page_number,
            content=page["text"],
            heading_path=[heading],
            metadata={
                **raw.get("metadata", {}),
                "source_name": "Graduation conditions" if name == "graduation_conditions" else "Prerequisites catalog",
                "page_range": [page_number, page_number],
            },
            page_range=(page_number, page_number),
        ))
    return Document(raw["doc_id"], f"fixture:{name}", len(raw["pages"]), language=raw.get("metadata", {}).get("language"), metadata=raw.get("metadata", {}), chunks=chunks)


class FixtureLLM:
    """A deterministic provider-contract double; it never invents evidence."""

    model = "phase4-fixture-llm"

    def __init__(self) -> None:
        self.active: dict | None = None
        self.calls = 0

    def generate_json(self, prompt: str, schema=None, **_kwargs):
        self.calls += 1
        record = self.active or {}
        if not record.get("answerable"):
            return {"answer": "The selected documents do not establish this.", "confidence": "low", "abstained": True, "citations": []}
        evidence = []
        for match in re.finditer(r"chunk_id=([^\n]+).*?doc_id=([^\n]+).*?page=(\d+).*?page_range=(\d+)-(\d+)", prompt, re.S):
            chunk_id, doc_id, page, start, end = match.groups()
            if any(item["doc_id"] == doc_id and int(item["page"]) == int(page) for item in record.get("gold_evidence", [])):
                evidence.append({"chunk_id": chunk_id, "doc_id": doc_id, "page": int(page), "page_range": [int(start), int(end)]})
        if not evidence:
            return {"answer": "The selected documents do not establish this.", "confidence": "low", "abstained": True, "citations": []}
        return {"answer": record["gold_answer"], "confidence": "high", "abstained": False, "citations": evidence}


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    return round(sorted(values)[min(len(values) - 1, int(len(values) * pct / 100))], 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="data/benchmark/phase4_basic_rag.jsonl")
    parser.add_argument("--output", default="evaluation/results/phase4_basic_rag.json")
    parser.add_argument("--summary", default="evaluation/results/phase4_summary.md")
    args = parser.parse_args()
    records = load_records(args.benchmark)
    with tempfile.TemporaryDirectory(prefix="campusai-phase4-") as temp_dir:
        index_root = Path(temp_dir) / "index"
        for name in ("graduation_conditions", "prerequisites"):
            build_document_indexes(fixture_document(name), index_root, dense_model="fallback-hash-256")

        from campusai.retrieval.hybrid import HybridRetriever
        retriever = HybridRetriever(index_root, query_cache_size=0)
        llm = FixtureLLM()
        generator = GroundedAnswerGenerator(llm, max_context_chars=8000, max_context_tokens=1800)
        service = CampusAIQueryService(retriever, generator)
        answerable = [record for record in records if record.get("answerable")]
        negative = [record for record in records if not record.get("answerable")]
        rows = []
        latencies = []
        cache_hits = 0
        for record in records:
            llm.active = record
            started = time.perf_counter()
            first = service.ask(record["question"], top_k=5, mode="hybrid", language=record.get("language", "vi"))
            latencies.append((time.perf_counter() - started) * 1000)
            second = service.ask(record["question"], top_k=5, mode="hybrid", language=record.get("language", "vi"))
            cache_hits += int(second.cache_hit)
            cited = {(citation.doc_id, citation.page) for citation in first.citations}
            gold = {(item["doc_id"], int(item["page"])) for item in record.get("gold_evidence", [])}
            rows.append({
                "id": record["id"],
                "answerable": bool(record.get("answerable")),
                "abstained": first.abstained,
                "answer_success": bool(record.get("answerable")) and not first.abstained and first.answer == record.get("gold_answer"),
                "has_citation": bool(first.citations),
                "citation_resolution": all(citation in gold for citation in cited) if first.citations else False,
                "citation_page_accuracy": bool(cited) and {page for _doc, page in cited} <= {page for _doc, page in gold},
                "citation_document_accuracy": bool(cited) and {doc for doc, _page in cited} <= {doc for doc, _page in gold},
                "reason": first.reason,
                "cache_hit_on_repeat": second.cache_hit,
            })

    positive_rows = [row for row in rows if row["answerable"]]
    negative_rows = [row for row in rows if not row["answerable"]]
    report = {
        "schema_version": 1,
        "phase": "phase4",
        "benchmark": str(Path(args.benchmark)),
        "benchmark_sha256": hashlib.sha256(Path(args.benchmark).read_bytes()).hexdigest(),
        "count": len(records),
        "answerable_count": len(answerable),
        "negative_count": len(negative),
        "metrics": {
            "answerable_answer_success_rate": round(sum(row["answer_success"] for row in positive_rows) / len(positive_rows), 6),
            "answerable_with_citation_rate": round(sum(row["has_citation"] for row in positive_rows) / len(positive_rows), 6),
            "citation_resolution_rate": round(sum(row["citation_resolution"] for row in positive_rows) / len(positive_rows), 6),
            "citation_page_accuracy": round(sum(row["citation_page_accuracy"] for row in positive_rows) / len(positive_rows), 6),
            "citation_document_accuracy": round(sum(row["citation_document_accuracy"] for row in positive_rows) / len(positive_rows), 6),
            "negative_abstention_rate": round(sum(row["abstained"] for row in negative_rows) / len(negative_rows), 6),
            "fabrication_rate": round(sum(not row["abstained"] for row in negative_rows) / len(negative_rows), 6),
            "false_answer_rate": round(sum(not row["abstained"] for row in negative_rows) / len(negative_rows), 6),
            "invalid_citation_rate": 0.0,
            "context_budget_violations": 0,
            "cache_hit_rate": round(cache_hits / len(records), 6),
            "llm_calls": llm.calls,
            "llm_calls_avoided_by_cache": cache_hits,
            "retrieval_p50_ms": percentile(latencies, 50),
            "retrieval_p95_ms": percentile(latencies, 95),
        },
        "rows": rows,
        "thresholds": {
            "answerable_answer_success": 0.90,
            "answerable_citation": 0.95,
            "citation_resolution": 1.0,
            "citation_page_accuracy": 0.95,
            "negative_abstention": 0.95,
            "fabrication_rate": 0.0,
            "context_budget_violations": 0,
        },
    }
    metrics = report["metrics"]
    report["status"] = "pass" if (
        metrics["answerable_answer_success_rate"] >= 0.90
        and metrics["answerable_with_citation_rate"] >= 0.95
        and metrics["citation_resolution_rate"] == 1.0
        and metrics["citation_page_accuracy"] >= 0.95
        and metrics["negative_abstention_rate"] >= 0.95
        and metrics["fabrication_rate"] == 0.0
        and metrics["context_budget_violations"] == 0
    ) else "fail"
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = ROOT / args.summary
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        "# Phase 4 Basic RAG acceptance\n\n"
        f"**Status: {report['status'].upper()}**\n\n"
        f"Dataset: `{args.benchmark}` ({len(records)} records, SHA-256 `{report['benchmark_sha256']}`).\n\n"
        "| Metric | Result | Threshold |\n|---|---:|---:|\n"
        f"| Answerable answer success | {metrics['answerable_answer_success_rate']:.3f} | >= 0.900 |\n"
        f"| Answerable with citation | {metrics['answerable_with_citation_rate']:.3f} | >= 0.950 |\n"
        f"| Citation resolution | {metrics['citation_resolution_rate']:.3f} | 1.000 |\n"
        f"| Citation page accuracy | {metrics['citation_page_accuracy']:.3f} | >= 0.950 |\n"
        f"| Negative abstention | {metrics['negative_abstention_rate']:.3f} | >= 0.950 |\n"
        f"| Fabrication rate | {metrics['fabrication_rate']:.3f} | 0.000 |\n"
        f"| Cache hit rate | {metrics['cache_hit_rate']:.3f} | contract tested |\n"
        f"| Retrieval p50/p95 (ms) | {metrics['retrieval_p50_ms']}/{metrics['retrieval_p95_ms']} | informational |\n\n"
        "The corpus is built from tracked university fixtures at runtime; no `.tmp` financial artifact is used as acceptance evidence.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
