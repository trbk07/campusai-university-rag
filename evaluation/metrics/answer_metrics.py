"""Normalization-aware metrics for Vietnamese financial answers."""
from __future__ import annotations
import re
import unicodedata
from typing import Iterable


def normalize_answer(value: object) -> str:
    text = unicodedata.normalize("NFC", str(value)).casefold()
    text = re.sub(r"[^\w\s%.,()\-/đĐ]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def exact_match(predicted: object, expected: object) -> float:
    return float(normalize_answer(predicted) == normalize_answer(expected))


def token_f1(predicted: object, expected: object) -> float:
    left, right = normalize_answer(predicted).split(), normalize_answer(expected).split()
    if not left or not right:
        return float(left == right)
    overlap = len(set(left) & set(right))
    if not overlap:
        return 0.0
    precision, recall = overlap / len(left), overlap / len(right)
    return round(2 * precision * recall / (precision + recall), 4)


def answer_report(cases: Iterable[dict]) -> dict[str, float]:
    rows = list(cases)
    if not rows:
        return {"exact_match": 0.0, "token_f1": 0.0}
    return {"exact_match": round(sum(exact_match(r.get("prediction", ""), r.get("answer", "")) for r in rows) / len(rows), 4),
            "token_f1": round(sum(token_f1(r.get("prediction", ""), r.get("answer", "")) for r in rows) / len(rows), 4)}

