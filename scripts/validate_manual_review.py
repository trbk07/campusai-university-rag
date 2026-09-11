"""Create and verify an auditable manual-review ledger for ingestion tables.

This tool deliberately never marks tables as reviewed automatically.  A human
must fill reviewer, reviewed_at, decision, source_checked and notes for every
row before the report can claim full manual validation.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from agentic_rag.ingestion.provenance import sha256_file

REQUIRED = ("table_id", "reviewer", "reviewed_at", "decision", "source_checked", "notes")
DECISIONS = {"accepted", "corrected", "rejected"}


def source_hash(path: Path) -> str:
    return sha256_file(path)


def build_ledger(manifest: Path, output: Path) -> None:
    documents = json.loads(manifest.read_text(encoding="utf-8"))
    rows = []
    for document in documents:
        for table in document.get("tables", []):
            diagnostics = table.get("diagnostics", {})
            rows.append({
                "table_id": table["table_id"],
                "doc_id": document["doc_id"],
                "source": document["source"],
                "source_sha256": document.get("source_sha256", ""),
                "start_page": table.get("start_page"),
                "end_page": table.get("end_page"),
                "status_before_review": diagnostics.get("status", table.get("status")),
                "review_reasons": ";".join(diagnostics.get("review_reasons", [])),
                "reviewer": "",
                "reviewed_at": "",
                "decision": "",
                "source_checked": "",
                "notes": "",
                "correction_notes": "",
                "rejection_reason": "",
            })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"tables": len(rows), "output": str(output)}, ensure_ascii=False))


def verify(ledger: Path, output: Path | None, manifest: Path | None = None) -> int:
    with ledger.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    problems = []
    expected = {}
    if manifest:
        documents = json.loads(manifest.read_text(encoding="utf-8"))
        expected = {table["table_id"]: (document, table)
                    for document in documents for table in document.get("tables", [])}
    seen = set()
    for index, row in enumerate(rows, 2):
        table_id = row.get("table_id", "")
        if not table_id or table_id in seen:
            problems.append(f"line {index}: missing or duplicate table_id")
        seen.add(table_id)
        if manifest and table_id not in expected:
            problems.append(f"line {index} ({table_id}): table_id not present in manifest")
        elif manifest:
            document, _ = expected[table_id]
            if row.get("source_sha256", "") != document.get("source_sha256", ""):
                problems.append(f"line {index} ({table_id}): source_sha256 does not match manifest")
        for field in REQUIRED[1:]:
            if not row.get(field, "").strip():
                problems.append(f"line {index} ({table_id}): missing {field}")
        decision = row.get("decision")
        if decision not in DECISIONS:
            problems.append(f"line {index} ({table_id}): decision must be accepted/corrected/rejected")
        if row.get("source_checked", "").lower() not in {"yes", "true"}:
            problems.append(f"line {index} ({table_id}): source_checked must be yes")
        if row.get("reviewed_at"):
            try:
                parsed = datetime.fromisoformat(row["reviewed_at"].replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError
            except ValueError:
                problems.append(f"line {index} ({table_id}): reviewed_at must be timezone-aware ISO-8601")
        if decision == "corrected" and not row.get("correction_notes", "").strip():
            problems.append(f"line {index} ({table_id}): corrected decision requires correction_notes")
        if decision == "rejected" and not row.get("rejection_reason", "").strip():
            problems.append(f"line {index} ({table_id}): rejected decision requires rejection_reason")
    if manifest:
        missing = set(expected) - seen
        problems.extend(f"manifest table missing from ledger: {table_id}" for table_id in sorted(missing))
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_sha256": source_hash(ledger),
        "tables": len(rows),
        "reviewed": sum(bool(row.get("reviewer", "").strip()) for row in rows),
        "fully_manually_validated": not problems and bool(rows),
        "problems": problems,
    }
    if output:
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["fully_manually_validated"] else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--manifest", type=Path, required=True)
    init.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("check")
    check.add_argument("--ledger", type=Path, required=True)
    check.add_argument("--manifest", type=Path)
    check.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.command == "init":
        build_ledger(args.manifest, args.output)
    else:
        raise SystemExit(verify(args.ledger, args.report, args.manifest))


if __name__ == "__main__":
    main()
