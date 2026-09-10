"""Validation and loading helpers for JSON benchmark cases."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

REQUIRED = {"id", "question", "answer", "evidence"}

def validate_cases(cases: Iterable[dict]) -> list[dict]:
    validated = []
    for index, case in enumerate(cases):
        missing = REQUIRED - set(case)
        if missing:
            raise ValueError(f"Case {index} missing fields: {sorted(missing)}")
        if not isinstance(case["evidence"], list):
            raise ValueError(f"Case {case['id']} evidence must be a list")
        validated.append(case)
    ids = [case["id"] for case in validated]
    if len(ids) != len(set(ids)):
        raise ValueError("Benchmark case IDs must be unique")
    return validated

def load_cases(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload.get("cases", payload) if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("Benchmark must contain a list or a cases field")
    return validate_cases(cases)

def save_cases(cases: Iterable[dict], path: str | Path) -> None:
    validated = validate_cases(cases)
    Path(path).write_text(json.dumps({"schema_version": 1, "cases": validated}, ensure_ascii=False, indent=2), encoding="utf-8")

