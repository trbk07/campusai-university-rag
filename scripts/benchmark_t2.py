"""Run the reproducible feasibility checks for Task 2.

The normal command is safe to run offline.  Docling and model execution are
explicit opt-ins because they may download large assets.  Missing optional
dependencies are recorded as blocked evidence; they are never reported as
successful measurements.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterable


DENSE_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
REPORT_SCHEMA = 2


def sha256(path: Path) -> str:
    """Return the content hash used as the stable document identity."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _rss_bytes() -> int | None:
    """Read current process RSS without making psutil mandatory."""

    try:
        import psutil

        return int(psutil.Process().memory_info().rss)
    except (ImportError, OSError):
        pass

    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("page_fault_count", wintypes.DWORD),
                    ("peak_working_set", ctypes.c_size_t),
                    ("working_set", ctypes.c_size_t),
                    ("quota_peak", ctypes.c_size_t),
                    ("quota", ctypes.c_size_t),
                    ("pagefile_peak", ctypes.c_size_t),
                    ("pagefile", ctypes.c_size_t),
                    ("private_peak", ctypes.c_size_t),
                    ("private", ctypes.c_size_t),
                ]

            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(ProcessMemoryCounters)
            get_current_process = ctypes.windll.kernel32.GetCurrentProcess
            get_current_process.restype = wintypes.HANDLE
            get_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
            get_memory_info.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessMemoryCounters),
                wintypes.DWORD,
            ]
            get_memory_info.restype = wintypes.BOOL
            ok = get_memory_info(
                get_current_process(),
                ctypes.byref(counters),
                counters.cb,
            )
            return int(counters.working_set) if ok else None

        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        multiplier = 1 if sys.platform == "darwin" else 1024
        return int(value * multiplier)
    except (ImportError, AttributeError, OSError):
        return None


def rss_mb() -> float | None:
    value = _rss_bytes()
    return round(value / (1024 * 1024), 2) if value is not None else None


class PeakMemory:
    """Sample RSS during an operation so model loading has a peak metric."""

    def __init__(self, interval_seconds: float = 0.02) -> None:
        self.interval_seconds = interval_seconds
        self.peak_bytes: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "PeakMemory":
        self.peak_bytes = _rss_bytes()

        def sample() -> None:
            while not self._stop.wait(self.interval_seconds):
                current = _rss_bytes()
                if current is not None:
                    self.peak_bytes = max(self.peak_bytes or current, current)

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        current = _rss_bytes()
        if current is not None:
            self.peak_bytes = max(self.peak_bytes or current, current)

    @property
    def peak_mb(self) -> float | None:
        if self.peak_bytes is None:
            return None
        return round(self.peak_bytes / (1024 * 1024), 2)


def environment(device: str) -> dict[str, Any]:
    cuda: dict[str, Any] = {"available": False}
    if _module_available("torch"):
        try:
            import torch

            cuda = {
                "available": bool(torch.cuda.is_available()),
                "device_count": int(torch.cuda.device_count()),
                "device_names": [
                    torch.cuda.get_device_name(index)
                    for index in range(torch.cuda.device_count())
                ],
                "torch_version": torch.__version__,
                "cuda_version": getattr(torch.version, "cuda", None),
            }
        except Exception as error:  # pragma: no cover - hardware-dependent
            cuda = {"available": False, "error": f"{type(error).__name__}: {error}"}

    selected_device = device
    if device == "auto":
        selected_device = "cuda" if cuda.get("available") else "cpu"

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "pid": os.getpid(),
        "device_requested": device,
        "device_selected": selected_device,
        "cuda": cuda,
        "packages": {
            "docling": _package_version("docling"),
            "fastembed": _package_version("fastembed"),
            "sentence_transformers": _package_version("sentence-transformers"),
            "psutil": _package_version("psutil"),
            "torch": _package_version("torch"),
        },
    }


def _read_pages(path: Path) -> list[dict[str, Any]]:
    from finrag.ingestion.docling_parser import parse_pdf

    return parse_pdf(path)


def _sample_texts(paths: Iterable[Path], limit: int = 64) -> list[str]:
    """Build model inputs from pages without putting page text in the report."""

    samples: list[str] = []
    for path in paths:
        try:
            pages = _read_pages(path)
        except Exception:
            continue
        for page in pages:
            text = str(page.get("text", "")).strip()
            if text:
                samples.append(text[:4000])
            if len(samples) >= limit:
                return samples
    return samples or ["Financial report revenue and operating income."]


def _run_docling(path: Path) -> dict[str, Any]:
    from finrag.ingestion.docling_parser import parse_with_docling

    started = time.perf_counter()
    with PeakMemory() as memory:
        metrics = parse_with_docling(path)
    metrics["seconds"] = round(time.perf_counter() - started, 6)
    metrics["peak_rss_mb"] = memory.peak_mb
    metrics["status"] = "success"
    return metrics


def benchmark_parser(
    path: Path,
    max_mb: int,
    max_pages: int,
    run_docling: bool,
) -> dict[str, Any]:
    """Measure cold parsing separately from persisted-cache lookup."""

    from finrag.ingestion.pipeline import ingest_document
    from finrag.ingestion.validate import validate_pdf

    result: dict[str, Any] = {
        "path": str(path),
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "implementation": "pymupdf",
    }

    try:
        validation = validate_pdf(path, max_mb=max_mb, max_pages=max_pages)
    except Exception as error:
        return {
            **result,
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }

    result["pages"] = validation.pages
    if not validation.has_text:
        result.update({"status": "skipped", "reason": "no_text_requires_ocr"})
        if run_docling:
            try:
                result["docling"] = _run_docling(path)
            except Exception as error:
                result["docling"] = {
                    "status": "blocked" if type(error).__name__ == "DoclingUnavailable" else "failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
        return result

    try:
        baseline_rss = rss_mb()
        started = time.perf_counter()
        with PeakMemory() as memory:
            pages = _read_pages(path)
        cold_seconds = time.perf_counter() - started
        result.update(
            {
                "status": "success",
                "pages": len(pages),
                "text_chars": sum(len(str(page.get("text", ""))) for page in pages),
                "cold_parse_seconds": round(cold_seconds, 6),
                "cold_seconds_per_page": round(cold_seconds / max(len(pages), 1), 6),
                "cold_baseline_rss_mb": baseline_rss,
                "cold_peak_rss_mb": memory.peak_mb,
                "cold_peak_rss_delta_mb": (
                    round(memory.peak_mb - baseline_rss, 2)
                    if memory.peak_mb is not None and baseline_rss is not None
                    else None
                ),
            }
        )

        store_dir = Path("data/processed/t2_store")
        started = time.perf_counter()
        document = ingest_document(
            path,
            store_dir=store_dir,
            max_mb=max_mb,
            max_pages=max_pages,
        )
        first_ingest_seconds = time.perf_counter() - started

        started = time.perf_counter()
        cached_document = ingest_document(
            path,
            store_dir=store_dir,
            max_mb=max_mb,
            max_pages=max_pages,
        )
        warm_seconds = time.perf_counter() - started
        result.update(
            {
                "ingest_seconds": round(first_ingest_seconds, 6),
                "warm_cache_seconds": round(warm_seconds, 6),
                "cached": bool(cached_document.cached),
                "chunks": len(document.chunks),
                "tables": len(document.tables),
                "table_inventory": [
                    {
                        "table_id": table.table_id,
                        "pages": table.pages,
                        "row_count": len(table.rows),
                        "column_count": len(table.headers),
                        "headers_present": bool(table.headers),
                    }
                    for table in document.tables
                ],
                "language": document.language,
                "peak_rss_mb": rss_mb(),
            }
        )
    except Exception as error:
        result.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
                "peak_rss_mb": rss_mb(),
            }
        )

    if run_docling:
        try:
            result["docling"] = _run_docling(path)
        except Exception as error:
            result["docling"] = {
                "status": "blocked" if type(error).__name__ == "DoclingUnavailable" else "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
    return result


def probe_fastembed() -> dict[str, Any]:
    """Record the exact FastEmbed support list without downloading a model."""

    base = {"implementation": "fastembed", "requested_model": DENSE_MODEL}
    if not _module_available("fastembed"):
        return {**base, "status": "blocked", "reason": "fastembed_not_installed"}

    try:
        from fastembed import TextEmbedding

        supported = TextEmbedding.list_supported_models()
        names = []
        for model in supported:
            if isinstance(model, dict):
                names.append(str(model.get("model", model)))
            else:
                names.append(str(model))
        return {
            **base,
            "status": "success",
            "supported_model_count": len(names),
            "supported_models": names,
            "requested_model_supported": DENSE_MODEL in names,
            "note": "The production plan uses sentence-transformers for bge-m3; this is an availability check only.",
        }
    except Exception as error:  # pragma: no cover - optional package API
        return {
            **base,
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sorted(values)[max(0, math.ceil(len(values) * 0.95) - 1)], 6)


def _benchmark_encoder(
    model: Any,
    texts: list[str],
    batch_size: int,
    repeats: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    with PeakMemory() as memory:
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
    cold_seconds = time.perf_counter() - started

    warm_seconds = []
    for _ in range(repeats):
        started = time.perf_counter()
        model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        warm_seconds.append(time.perf_counter() - started)

    warm_p50 = statistics.median(warm_seconds) if warm_seconds else None
    return {
        "item_count": len(texts),
        "batch_size": batch_size,
        "dimension": len(vectors[0]) if len(vectors) else 0,
        "cold_seconds": round(cold_seconds, 6),
        "warm_seconds": [round(value, 6) for value in warm_seconds],
        "warm_p50_seconds": round(warm_p50, 6) if warm_p50 is not None else None,
        "warm_p95_seconds": _p95(warm_seconds),
        "throughput_items_per_second": round(len(texts) / warm_p50, 3) if warm_p50 else None,
        "peak_rss_mb": memory.peak_mb,
    }


def _benchmark_reranker(
    model: Any,
    texts: list[str],
    batch_size: int,
    repeats: int,
) -> dict[str, Any]:
    pairs = [["What is revenue?", text] for text in texts]
    started = time.perf_counter()
    with PeakMemory() as memory:
        model.predict(pairs, batch_size=batch_size, show_progress_bar=False)
    cold_seconds = time.perf_counter() - started

    warm_seconds = []
    for _ in range(repeats):
        started = time.perf_counter()
        model.predict(pairs, batch_size=batch_size, show_progress_bar=False)
        warm_seconds.append(time.perf_counter() - started)

    warm_p50 = statistics.median(warm_seconds) if warm_seconds else None
    return {
        "pair_count": len(pairs),
        "batch_size": batch_size,
        "cold_seconds": round(cold_seconds, 6),
        "warm_seconds": [round(value, 6) for value in warm_seconds],
        "warm_p50_seconds": round(warm_p50, 6) if warm_p50 is not None else None,
        "warm_p95_seconds": _p95(warm_seconds),
        "throughput_pairs_per_second": round(len(pairs) / warm_p50, 3) if warm_p50 else None,
        "peak_rss_mb": memory.peak_mb,
    }


def benchmark_models(
    texts: list[str],
    device: str,
    batch_size: int,
    repeats: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "blocked",
        "dense_model": DENSE_MODEL,
        "reranker_model": RERANKER_MODEL,
        "device": device,
        "text_count": len(texts),
    }
    if not _module_available("sentence_transformers"):
        return {**result, "reason": "sentence_transformers_not_installed"}

    try:
        from sentence_transformers import CrossEncoder, SentenceTransformer

        started = time.perf_counter()
        with PeakMemory() as dense_memory:
            encoder = SentenceTransformer(DENSE_MODEL, device=device)
        dense_load_seconds = time.perf_counter() - started
        dense_metrics = _benchmark_encoder(encoder, texts, batch_size, repeats)
        del encoder

        started = time.perf_counter()
        with PeakMemory() as reranker_memory:
            reranker = CrossEncoder(RERANKER_MODEL, device=device)
        reranker_load_seconds = time.perf_counter() - started
        reranker_metrics = _benchmark_reranker(reranker, texts, batch_size, repeats)

        return {
            **result,
            "status": "success",
            "dense": {
                "load_seconds": round(dense_load_seconds, 6),
                "load_peak_rss_mb": dense_memory.peak_mb,
                **dense_metrics,
            },
            "reranker": {
                "load_seconds": round(reranker_load_seconds, 6),
                "load_peak_rss_mb": reranker_memory.peak_mb,
                **reranker_metrics,
            },
        }
    except Exception as error:  # pragma: no cover - model/network-dependent
        return {
            **result,
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
        }


def derive_limits(
    report: dict[str, Any],
    memory_budget_mb: int,
    concurrency: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Derive conservative page limits from observed parser measurements."""

    rows = [row for row in report.get("parser", []) if row.get("status") == "success"]
    seconds_per_page = [
        float(row["cold_seconds_per_page"])
        for row in rows
        if isinstance(row.get("cold_seconds_per_page"), (int, float))
    ]
    peak_rss = [
        float(row["cold_peak_rss_delta_mb"])
        for row in rows
        if isinstance(row.get("cold_peak_rss_delta_mb"), (int, float))
    ]
    total = len(report.get("parser", []))
    failed = sum(row.get("status") == "failed" for row in report.get("parser", []))
    evidence = {
        "documents": len(rows),
        "p95_seconds_per_page": _p95(seconds_per_page),
        "max_cold_peak_rss_delta_mb": max(peak_rss) if peak_rss else None,
        "model_peak_rss_mb": _model_peak_rss(report.get("models", {})),
        "failure_rate": round(failed / total, 6) if total else None,
        "memory_budget_mb": memory_budget_mb,
        "concurrency": concurrency,
        "timeout_seconds": timeout_seconds,
    }

    distinct_page_counts = {row.get("pages") for row in rows}
    if (
        len(distinct_page_counts) < 2
        or evidence["p95_seconds_per_page"] is None
        or evidence["max_cold_peak_rss_delta_mb"] is None
    ):
        evidence["reason"] = "at_least_two_document_sizes_are_required_to_estimate_memory_growth_per_page"
        return {"status": "insufficient_evidence", "evidence": evidence, "limits": None}

    p95_seconds = float(evidence["p95_seconds_per_page"])
    measured_rss = float(evidence["max_cold_peak_rss_delta_mb"])
    model_peak_rss = evidence["model_peak_rss_mb"] or 0
    latency_pages = math.floor(timeout_seconds / max(p95_seconds, 1e-9))
    available_memory = max(memory_budget_mb - float(model_peak_rss), 1)
    memory_pages = math.floor(available_memory / max(measured_rss * concurrency, 1))
    hard_pages = max(1, min(latency_pages, memory_pages))
    return {
        "status": "measured",
        "evidence": evidence,
        "limits": {
            "soft_max_pages": max(1, math.floor(hard_pages * 0.8)),
            "hard_max_pages": hard_pages,
            "hard_max_upload_mb": 50,
            "formula": "min(timeout / p95_seconds_per_page, (memory_budget - model_peak_rss) / (max_peak_rss_delta * concurrency))",
            "promotion_gate": "failure_rate <= 0.05 and representative table review is complete",
        },
    }


def _model_peak_rss(models: dict[str, Any]) -> float | None:
    """Return the largest recorded model-load RSS when model execution passed."""

    peaks = []
    for name in ("dense", "reranker"):
        metrics = models.get(name, {})
        value = metrics.get("load_peak_rss_mb")
        if isinstance(value, (int, float)):
            peaks.append(float(value))
    return max(peaks) if peaks else None


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(report: dict[str, Any], output: Path) -> None:
    """Write scalar parser metrics beside the JSON evidence artifact."""

    rows = report.get("parser", [])
    if not rows:
        return
    csv_path = output.with_suffix(".csv")
    fields = sorted({key for row in rows for key, value in row.items() if not isinstance(value, (dict, list))})
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evaluation/t2_results.json"))
    parser.add_argument("--max-mb", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=250)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-docling", action="store_true")
    parser.add_argument("--run-models", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--memory-budget-mb", type=int, default=2048)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.resume and args.output.exists():
        report = _load_report(args.output)
        report.setdefault("parser", [])
        report.setdefault("environment", environment(args.device))
        report.setdefault("fastembed", probe_fastembed())
        report.setdefault("models", {"status": "not_run", "reason": "not run in this artifact"})
    else:
        report = {
            "schema_version": REPORT_SCHEMA,
            "environment": environment(args.device),
            "fastembed": probe_fastembed(),
            "parser": [],
            "models": {
                "status": "not_run",
                "reason": "use --run-models for explicit model execution",
            },
        }

    files = sorted(args.input_dir.glob("*.pdf"))
    recorded = {row.get("sha256") for row in report["parser"]}
    for path in files:
        if sha256(path) in recorded:
            continue
        report["parser"].append(
            benchmark_parser(path, args.max_mb, args.max_pages, args.run_docling)
        )
        report["updated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.run_models:
        texts = _sample_texts(files)
        report["models"] = benchmark_models(
            texts,
            report["environment"]["device_selected"],
            args.batch_size,
            args.repeats,
        )

    report["limits"] = derive_limits(
        report,
        memory_budget_mb=args.memory_budget_mb,
        concurrency=args.concurrency,
        timeout_seconds=args.timeout_seconds,
    )
    report["summary"] = {
        "documents_discovered": len(files),
        "documents_recorded": len(report["parser"]),
        "successful": sum(row.get("status") == "success" for row in report["parser"]),
        "failed": sum(row.get("status") == "failed" for row in report["parser"]),
        "skipped": sum(row.get("status") == "skipped" for row in report["parser"]),
        "complete": len({row.get("sha256") for row in report["parser"]}) == len(files),
        "max_upload_mb": args.max_mb,
        "max_pages": args.max_pages,
        "acceptance_ready": (
            report["limits"]["status"] == "measured"
            and report["models"].get("status") == "success"
        ),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
