"""Small bilingual tokenizer with tolerant Unicode normalization."""

from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"[\w\u00c0-\u024f]+", re.UNICODE)


def repair_mojibake(text: str) -> str:
    """Repair common UTF-8 decoded as CP1252/Latin-1 corruption."""
    value = str(text)
    markers = ("\u00c3", "\u00c2", "\u00c6", "\u00c4", "\u00e1\u00bb", "\u00e2")
    if not any(marker in value for marker in markers):
        return value
    before = sum(value.count(marker) for marker in markers)
    for encoding in ("cp1252", "latin1"):
        try:
            repaired = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if sum(repaired.count(marker) for marker in markers) < before:
            return repaired
    return value


def tokenize(text: str, language: str | None = None) -> list[str]:
    """Tokenize Vietnamese/English text without mandatory segmentation."""
    value = repair_mojibake(text).casefold()
    if language == "vi":
        try:
            from underthesea import word_tokenize
            value = word_tokenize(value, format="text")
        except ImportError:
            pass
    return _WORD.findall(value)


def normalized_tokens(text: str, language: str | None = None) -> list[str]:
    """Return original tokens plus accent-folded forms for tolerant matching."""
    tokens = tokenize(text, language)
    folded = [
        unicodedata.normalize("NFKD", token).encode("ascii", "ignore").decode("ascii")
        for token in tokens
    ]
    return tokens + [token for token in folded if token and token not in tokens]
