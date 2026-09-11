"""Evaluate PDF ingestion outputs and create a reproducible review report.

This evaluator reports extracted image artifacts and geometry separately from
chart semantic extraction, which requires a chart-specific interpretation layer.
"""
import argparse
import json
from pathlib import Path
from agentic_rag.ingestion.pdf_parser import parse_pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ocr", action="store_true", help="OCR pages without a usable text layer")
    parser.add_argument("--ocr-language", default="eng", help="Tesseract language(s), e.g. eng+vie")
    args = parser.parse_args()
    chunks, tables, figures, failures = [], [], [], []
    reason_counts: dict[str, int] = {}
    page_dimensions: dict[str, dict[str, float]] = {}
    for path in sorted(args.input_dir.glob("*.pdf")):
        try:
            parsed = parse_pdf(path, use_ocr=args.ocr, ocr_language=args.ocr_language)
            chunks.extend({"text": x.text, "metadata": vars(x.metadata)} for x in parsed.chunks)
            figures.extend({"figure_id": item.figure_id, "page": item.page, "bbox": item.bbox,
                            "kind": item.kind, "image_index": item.image_index}
                           for item in parsed.figures)
            page_dimensions.update({f"{path.name}:p{page}": dimensions
                                    for page, dimensions in parsed.page_dimensions.items()})
            for table in parsed.tables:
                for reason in table.diagnostics.get("review_reasons", []):
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                tables.append({"table_id": table.table_id, "metadata": vars(table.metadata), "schema": table.schema,
                               "rows": len(table.dataframe), "columns": list(table.dataframe.columns),
                               "status": table.diagnostics.get("status"),
                               "review_reasons": table.diagnostics.get("review_reasons", []),
                               "quality_score": table.diagnostics.get("quality_score"),
                               "numeric_candidates": table.diagnostics.get("numeric_candidates", 0),
                               "numeric_parsed": table.diagnostics.get("numeric_parsed", 0),
                               "numeric_unparsed": table.diagnostics.get("numeric_unparsed", 0)})
        except Exception as exc:
            failures.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
    review_required = sum(table.get("status") == "review_required" for table in tables)
    numeric_candidates = 0
    numeric_parsed = 0
    for table in tables:
        # The compact report does not retain raw rows, so derive numeric quality
        # from the diagnostics collected by the parser below when available.
        numeric_candidates += int(table.get("numeric_candidates", 0) or 0)
        numeric_parsed += int(table.get("numeric_parsed", 0) or 0)
    numeric_coverage = (numeric_parsed / numeric_candidates) if numeric_candidates else 1.0
    report = {"schema_version": 4, "mode": {"ocr": args.ocr, "ocr_language": args.ocr_language},
              "capabilities": {
                  "document_pages": "supported",
                  "native_text": "supported",
                  "ocr_fallback": "supported",
                  "reading_order": "supported_with_heuristics",
                  "tables": "supported_with_review_queue",
                  "figures": "image_artifacts_supported",
                  "charts": "chart_semantics_not_supported",
                  "bounding_boxes": "supported_for_text_tables_figures",
              },
              "sample_chunks": chunks[:30], "sample_tables": tables[:10],
              "figures": figures, "page_dimensions": page_dimensions,
              "failure_cases": failures, "reason_counts": dict(sorted(reason_counts.items())),
              "totals": {"chunks": len(chunks), "tables": len(tables), "failures": len(failures),
                         "tables_review_required": review_required,
                         "tables_usable": len(tables) - review_required,
                         "table_usable_rate": round((len(tables) - review_required) / len(tables), 4) if tables else 1.0,
                         "numeric_candidates": numeric_candidates,
                         "numeric_parsed": numeric_parsed,
                         "numeric_coverage": round(numeric_coverage, 4),
                         "distinct_review_reasons": len(reason_counts)},
              "acceptance": {"corpus_parse": not failures,
                             "manual_quality": not failures and review_required == 0,
                             "numeric_quality": numeric_coverage >= 0.95,
                             "overall": not failures and review_required == 0 and numeric_coverage >= 0.95,
                             "unsupported_features_blocking": ["chart_semantics"]}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
