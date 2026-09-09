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
    for path in sorted(args.input_dir.glob("*.pdf")):
        try:
            parsed = parse_pdf(path)
            chunks.extend({"text": x.text, "metadata": vars(x.metadata)} for x in parsed.chunks)
            tables.extend({"table_id": x.table_id, "metadata": vars(x.metadata), "schema": x.schema,
                           "rows": len(x.dataframe), "columns": list(x.dataframe.columns)} for x in parsed.tables)
        except Exception as exc:
            failures.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})
    report = {"sample_chunks": chunks[:30], "sample_tables": tables[:10], "failure_cases": failures,
              "totals": {"chunks": len(chunks), "tables": len(tables), "failures": len(failures)}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
