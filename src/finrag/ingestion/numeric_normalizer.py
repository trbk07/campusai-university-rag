"""Normalize common financial number formats without guessing aggressively."""

from __future__ import annotations

import re


_NUMBER_PATTERN = re.compile(r"[+-]?\d[\d.,]*")


def normalize_number(value: str) -> float | None:
    """Convert Vietnamese/English financial notation to ``float``.

    Separators are interpreted from the final separator when both are present.
    A single three-digit separator is treated as a thousands separator, which
    matches common financial reports (``1.234`` and ``1,234``).
    """
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    text = text.replace("−", "-").replace("–", "-").replace("'", "")
    if not text or text in {"-", "—", "–", "N/A", "n/a"}:
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
