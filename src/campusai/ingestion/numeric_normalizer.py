"""Normalize common numeric formats without guessing aggressively."""

from __future__ import annotations

import re


_NUMBER_PATTERN = re.compile(r"[+-]?\d[\d.,]*")


def normalize_spoken_decimals(value: str) -> str:
    """Normalize explicit digit/delimiter/digit input, never infer a value.

    This is query grammar only. Source text/quotes and ingestion numbers remain
    untouched; ambiguous number words and thousands separators are not guessed.
    """
    return re.sub(r'(?<!\w)(\d+)\s+(?:phẩy|phay|chấm|cham|point)\s+(\d+)(?!\w)',
                  lambda m:m[1]+'.'+m[2],value,flags=re.I)


def normalize_number(value: str) -> float | None:
    """Convert Vietnamese/English numeric notation to ``float``.

    Separators are interpreted from the final separator when both are present.
    A single three-digit separator is treated as a thousands separator, which
    matches common academic and administrative tables.
    """

    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    text = text.replace("−", "-").replace("–", "-")
    text = text.replace("âˆ’", "-").replace("â€“", "-").replace("'", "")
    if not text or text in {"-", "—", "N/A", "n/a"}:
        return None

    is_negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if text.endswith("%"):
        text = text[:-1]
    if not _NUMBER_PATTERN.fullmatch(text):
        return None

    if "." in text and "," in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        if len(parts) > 2 or len(parts[-1]) == 3:
            text = "".join(parts)
        else:
            text = ".".join(parts)
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 2 or len(parts[-1]) == 3:
            text = "".join(parts)

    try:
        number = float(text)
    except ValueError:
        return None
    return -number if is_negative else number
