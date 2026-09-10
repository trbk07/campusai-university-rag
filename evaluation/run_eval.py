"""Run deterministic retrieval, answer, and citation evaluation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Callable
from .benchmark_builder import load_cases
from .metrics.answer_metrics import answer_report
from .metrics.citation_metrics import citation_report
from .metrics.retrieval_metrics import retrieval_report

def evaluate(cases: list[dict], predict: Callable[[dict], dict]) -> dict:
    rows = [predict(case) for case in cases]
    answers = [{"prediction": row.get("answer", ""), "answer": case["answer"]} for case, row in zip(cases, rows)]
    retrieval = [{"retrieved": row.get("retrieved", []), "relevant": case.get("evidence", [])} for case, row in zip(cases, rows)]
    citations = [{"citations": row.get("citations", []), "supported": case.get("evidence", [])} for case, row in zip(cases, rows)]
    return {"cases": len(cases), "answer": answer_report(answers), "retrieval": retrieval_report(retrieval), "citation": citation_report(citations)}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load_cases(args.benchmark)
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in predictions}
    report = evaluate(cases, lambda case: by_id.get(case["id"], {}))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output: args.output.write_text(text, encoding="utf-8")
    else: print(text)

if __name__ == "__main__": main()

