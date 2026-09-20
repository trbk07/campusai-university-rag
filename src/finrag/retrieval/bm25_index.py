"""A dependency-light BM25 index persisted as JSON."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from .tokenizer_vi import normalized_tokens


class BM25Index:
    """BM25Okapi-style index over chunks from exactly one document."""

    def __init__(self, items: list[dict] | None = None, language: str | None = None) -> None:
        self.language = language
        self.items: list[dict] = []
        self.tokens: list[list[str]] = []
        self.term_frequency: list[Counter] = []
        self.document_frequency: Counter = Counter()
        self.avgdl = 0.0
        if items:
            self.build(items)

    def build(self, items: list[dict]) -> None:
        self.items = items
        self.tokens = [normalized_tokens(item.get("content", ""), self.language) for item in items]
        self.term_frequency = [Counter(tokens) for tokens in self.tokens]
        self.document_frequency = Counter()
        for tokens in self.tokens:
            self.document_frequency.update(set(tokens))
        self.avgdl = sum(map(len, self.tokens)) / max(1, len(self.tokens))

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        query_tokens = normalized_tokens(query, self.language)
        n = len(self.items)
        if not n:
            return []
        k1, b = 1.5, 0.75
        scored = []
        for index, frequencies in enumerate(self.term_frequency):
            length = len(self.tokens[index]) or 1
            score = 0.0
            for term in query_tokens:
                if not frequencies.get(term):
                    continue
                df = self.document_frequency.get(term, 0)
                idf = math.log(1.0 + (n - df + 0.5) / (df + 0.5))
                tf = frequencies[term]
                norm = tf + k1 * (1 - b + b * length / max(self.avgdl, 1e-9))
                score += idf * (tf * (k1 + 1)) / norm
            if score > 0:
                scored.append((self.items[index]["chunk_id"], score))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:top_k]

    def to_dict(self) -> dict:
        return {"language": self.language, "items": self.items}

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BM25Index":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["items"], data.get("language"))
