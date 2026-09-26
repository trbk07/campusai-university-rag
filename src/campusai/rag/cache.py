"""Versioned, credential-free cache for grounded RAG answers."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from typing import Any

from ..llm.cache import SQLiteLLMCache
from .claims import Claim
from .confidence import POLICY_VERSION
from .grounding import Citation, GroundedAnswer
from .schemas import SCHEMA_VERSION


PROMPT_VERSION = "phase5-v1"
GROUNDING_POLICY_VERSION = "phase5-v1"
ABSTENTION_POLICY_VERSION = "phase5-v1"


def normalize_question(question: str) -> str:
    """Normalize harmless formatting differences without changing meaning."""

    return re.sub(r"\s+", " ", question.strip()).casefold()


def build_rag_cache_key(
    *,
    question: str,
    language: str,
    doc_ids: list[str] | None,
    filters: dict[str, Any] | None,
    top_k: int,
    mode: str,
    corpus_version: str,
    model: str | None,
    context_budget: dict[str, int | float | None],
    prompt_version: str = PROMPT_VERSION,
    grounding_policy_version: str = GROUNDING_POLICY_VERSION,
    confidence_policy_version: str = POLICY_VERSION,
    abstention_policy_version: str = ABSTENTION_POLICY_VERSION,
    schema_version: str = SCHEMA_VERSION,
) -> str:
    """Hash only canonical request semantics; never store secrets in the key."""

    payload = {
        "question": normalize_question(question),
        "language": language.casefold(),
        "doc_ids": sorted(doc_ids) if doc_ids else None,
        "filters": filters or {},
        "top_k": int(top_k),
        "mode": mode,
        "corpus_version": corpus_version,
        "prompt_version": prompt_version,
        "grounding_policy_version": grounding_policy_version,
        "confidence_policy_version": confidence_policy_version,
        "abstention_policy_version": abstention_policy_version,
        "schema_version": schema_version,
        "model": model or "none",
        "context_budget": context_budget,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class RAGAnswerCache:
    """SQLite-backed cache with process-local single-flight protection."""

    def __init__(self, path: str = ":memory:") -> None:
        self._store = SQLiteLLMCache(path)
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.RLock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def get(self, key: str) -> GroundedAnswer | None:
        cached = self._store.get(key)
        if cached is None:
            return None
        try:
            payload = json.loads(cached.text)
            citations = tuple(Citation(
                chunk_id=str(item["chunk_id"]),
                doc_id=str(item["doc_id"]),
                page=int(item["page"]),
                quote=str(item.get("quote", "")),
                section_path=str(item.get("section_path", "")),
                source_name=str(item.get("source_name", "")),
                page_range=tuple(item.get("page_range", [item["page"], item["page"]])),
                table_id=str(item.get("table_id", "")),
                source_hash=str(item.get("source_hash", "")),
            ) for item in payload.get("citations", []))
            return GroundedAnswer(
                answer=str(payload["answer"]),
                citations=citations,
                confidence=str(payload["confidence"]),
                abstained=bool(payload["abstained"]),
                reason=payload.get("reason"),
                cache_hit=True,
                claims=tuple(Claim(str(item.get("claim_id", "")), str(item.get("text", "")), str(item.get("type", "fact")), 1,
                                   tuple(item.get("citation_ids", [])), str(item.get("status", "supported")), float(item.get("support_score", 0.0)), ())
                              for item in payload.get("claims", []) if isinstance(item, dict)),
                evidence_status=str(payload.get("evidence_status", "found")),
                confidence_score=payload.get("confidence_score"),
                policy_version=str(payload.get("confidence_policy_version", POLICY_VERSION)),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def put(self, key: str, answer: GroundedAnswer) -> None:
        cacheable_abstentions = {
            "no_retrieval_evidence",
            "no_relevant_evidence",
            "context_budget_exceeded",
            "model_abstained",
            "unsupported_claim",
            "provider_abstained",
            "conflicting_evidence",
            "ambiguous_question",
        }
        if answer.abstained and answer.reason not in cacheable_abstentions:
            return
        if not answer.abstained and not answer.citations:
            return
        payload = json.dumps(answer.to_dict(), ensure_ascii=False, sort_keys=True)
        self._store.put(key, payload, {"kind": "phase4_grounded_answer"}, 0.0)

    def lock(self, key: str) -> threading.Lock:
        return self._lock_for(key)

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> "RAGAnswerCache":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
