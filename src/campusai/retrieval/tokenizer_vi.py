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


def normalize_retrieval_query(text: str) -> str:
    """Normalize common bilingual academic query variants.

    The original query is still retained by the caller for provenance and
    page constraints; this expanded form is used only for candidate recall.
    """
    original = repair_mojibake(str(text)).strip()
    value = re.sub(r"[_/\\-]+", " ", original)
    aliases = []
    lowered = value.casefold()
    if re.search(r"tín\s*chỉ|tin\s*chi|credits?", lowered):
        aliases.extend(("tín chỉ", "tin chi", "credits"))
    if re.search(r"thực\s*tập|thuc\s*tap|internship", lowered):
        aliases.extend(("thực tập", "thuc tap", "internship"))
    if re.search(r"tiên\s*quyết|tien\s*quyet|prerequisite", lowered):
        aliases.extend(("tiên quyết", "tien quyet", "prerequisite"))
    # Preserve codes and academic years exactly; normalized_tokens adds the
    # accent-folded form without changing these markers.
    return " ".join([original, value, *aliases])


def retrieval_text(item: dict) -> str:
    """Return searchable content plus stable provenance metadata."""
    metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
    values = [
        str(item.get("content", "")), str(item.get("doc_id", "")),
        str(metadata.get("source_name", "")), str(metadata.get("document_type", "")),
        str(metadata.get("program", "")), str(metadata.get("institution", "")),
        str(metadata.get("version", "")),
        " ".join(str(value) for value in item.get("heading_path", []) or metadata.get("heading_path", [])),
    ]
    return " ".join(value for value in values if value)
