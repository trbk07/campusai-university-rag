"""Deterministic failure taxonomy for benchmark reports."""
from collections import Counter

def classify_case(case: dict) -> str:
    if not case.get("retrieved", []): return "retrieval_miss"
    if case.get("prediction", "") != case.get("answer", ""): return "answer_mismatch"
    if set(case.get("citations", [])) - set(case.get("supported", [])): return "unsupported_citation"
    return "pass"

def error_report(cases: list[dict]) -> dict[str, int]:
    return dict(Counter(classify_case(case) for case in cases))
