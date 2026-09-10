"""Conservative Unicode repair for text extracted from PDFs.

Some PDF font maps expose UTF-8 bytes as Latin-1/CP1252 characters, producing
strings such as ``BÃ¡o cÃ¡o``.  Repair is deliberately gated: valid Vietnamese
text must never be re-encoded merely because it contains non-ASCII characters.
"""
from __future__ import annotations

import re


# These are the byte-decoding artefacts produced by UTF-8 interpreted as
# Latin-1/CP1252.  A bare ``Ã`` or ``Â`` is not sufficient: ``XÃ HỘI`` and
# ``Âu Dương`` are valid Vietnamese and must remain untouched.
_MOJIBAKE_RE = re.compile(r"(?:Ã[\x80-\xBF¡-ÿ]|Â[\x80-\xBF°¹²³¼½¾]|Ä[\x80-\xBF‘’]|Æ[\x80-\xBF°]|â[\x80-\xBF])")
_VIETNAMESE = set("ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")


def _control_count(text: str) -> int:
    """Count non-printing controls while allowing normal text whitespace."""
    return sum(ord(char) < 32 and char not in "\\n\\r\\t" or 0x7F <= ord(char) <= 0x9F
               for char in text)


def mojibake_score(text: str) -> int:
    """Return a score for common broken UTF-8 and unrecoverable glyph signals."""
    return (len(_MOJIBAKE_RE.findall(text)) + _control_count(text)
            + text.count("�"))


def _candidate(text: str, encoding: str) -> str | None:
    try:
        return text.encode(encoding).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None


def _quality(text: str) -> tuple[int, int, int]:
    markers = mojibake_score(text)
    vietnamese = sum(char in _VIETNAMESE for char in text)
    controls = _control_count(text)
    return markers, controls, -vietnamese


def _remove_invalid_controls(text: str) -> str:
    """Remove PDF control artifacts but preserve tabs/newlines for normalization."""
    return "".join(char for char in text
                   if char in "\n\r\t" or (char != "\u00ad" and not (ord(char) < 32 or 0x7F <= ord(char) <= 0x9F)))


def repair_mojibake(text: str) -> tuple[str, bool]:
    """Repair one or more mojibake layers only when quality strictly improves."""
    current = text
    changed = False
    for _ in range(3):
        before = _quality(current)
        candidates = [candidate for encoding in ("latin-1", "cp1252")
                      if (candidate := _candidate(current, encoding)) is not None]
        if not candidates:
            break
        best = min(candidates, key=_quality)
        after = _quality(best)
        # Require fewer mojibake markers and no new control characters.
        if after[0] >= before[0] or after[1] > before[1]:
            break
        current = best
        changed = True
    return current, changed


def normalize_extracted_text(text: str) -> tuple[str, bool]:
    """Repair broken UTF-8, remove PDF controls, and normalize whitespace."""
    repaired, changed = repair_mojibake(text)
    cleaned = _remove_invalid_controls(repaired)
    changed = changed or cleaned != repaired
    return " ".join(cleaned.split()), changed
