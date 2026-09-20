"""Small bilingual tokenizer with an optional Vietnamese word segmenter."""

from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


def tokenize(text: str, language: str | None = None) -> list[str]:
    """Tokenize Vietnamese/English text without making segmentation mandatory."""

    value = str(text).casefold()
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
        unicodedata.normalize("NFKD", token)
        .encode("ascii", "ignore")
        .decode("ascii")
        for token in tokens
    ]
    return tokens + [token for token in folded if token and token not in tokens]
