"""Observable benchmark families shared by repair and release validation."""
from __future__ import annotations

import hashlib
import re
import unicodedata


def question_template(question: str) -> str:
    prefix = re.split(r"\btopic\s*:\s*", question, maxsplit=1, flags=re.I)[0]
    prefix = unicodedata.normalize("NFC", prefix).casefold()
    # An uploaded filename is request scope, not a different query template.
    # Removing the wrapper prevents per-split PDF names from hiding duplicates.
    prefix = re.sub(
        r"^(?:use only the uploaded|chỉ dùng tài liệu đã tải lên)\s+['\"]?[^\r\n]+?\.pdf['\"]?\.\s*",
        "", prefix)
    prefix = re.sub(r"\b(?:page|trang)\s+\d+\b", "page <n>", prefix)
    return re.sub(r"\s+", " ", prefix).strip()


def intent_family(question: str) -> str:
    text = question_template(question)
    if "current academic year" in text:
        return "temporal-current-applicability"
    if "ignore previous instructions" in text:
        return "document-prompt-injection"
    if "scanned page" in text or "extractable evidence" in text or "without page text" in text:
        return "scan-evidence-sufficiency"
    if "two evidence spans" in text:
        return "multi-evidence-composition"
    if any(term in text for term in ("page <n>", "source page")):
        return "page-statement-source-lookup"
    return "template:" + hashlib.sha256(text.encode()).hexdigest()[:20]


def record_families(row: dict) -> tuple[tuple[str, str], ...]:
    sources = {str(row.get("source_group", ""))}
    sources.update(str(e.get("doc_id", "")) for claim in row.get("gold_claims", [])
                   for e in claim.get("evidence", []))
    selected = row.get("selected_doc_ids")
    if isinstance(selected, list):
        sources.update(item for item in selected if isinstance(item, str) and item.strip())
    return tuple([("source", source) for source in sorted(sources) if source]
                 + [("template", question_template(row["question"])),
                    ("intent-paraphrase", intent_family(row["question"]))])
