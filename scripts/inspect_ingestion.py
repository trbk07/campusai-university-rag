"""Create a compact manual-review sample and failure-case summary."""
import argparse
import json
from pathlib import Path
from agentic_rag.ingestion.pdf_parser import parse_pdf


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    chunks, tables, failures = [], [], []
    reason_counts: dict[str, int] = {}
    for path in sorted(args.input_dir.glob("*.pdf")):
        try:
            parsed = parse_pdf(path)
            chunks.extend({"text": x.text, "metadata": vars(x.metadata)} for x in parsed.chunks)
            for table in parsed.tables:
                for reason in table.diagnostics.get("review_reasons", []):
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
                tables.append({"table_id": table.table_id, "metadata": vars(table.metadata), "schema": table.schema,
                               "rows": len(table.dataframe), "columns": list(table.dataframe.columns),
                               "status": table.diagnostics.get("status"),
                               "review_reasons": table.diagnostics.get("review_reasons", []),
                               "quality_score": table.diagnostics.get("quality_score")})
        except Exception as exc:
            failures.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
    report = {"schema_version": 2, "sample_chunks": chunks[:30], "sample_tables": tables[:10],
              "failure_cases": failures, "reason_counts": dict(sorted(reason_counts.items())),
              "totals": {"chunks": len(chunks), "tables": len(tables), "failures": len(failures),
                         "tables_review_required": sum(table.get("status") == "review_required" for table in tables),
                         "distinct_review_reasons": len(reason_counts)}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
