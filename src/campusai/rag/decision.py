"""Deterministic final decision policy, independent of provider labels."""

from __future__ import annotations

from dataclasses import dataclass

from .claims import Claim


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str | None = None


def decide(claims: list[Claim], *, invalid_citation: bool = False,
           provider_error: bool = False, provider_abstained: bool = False,
           has_conflict: bool = False, ambiguous: bool = False,
           allow_partial: bool = False) -> Decision:
    if provider_error:
        return Decision("abstained", "provider_error")
    if invalid_citation:
        return Decision("abstained", "invalid_citation")
    hard_conflict = any(claim.status == "contradicted" for claim in claims)
    numeric_conflict = any(claim.numeric_conflict for claim in claims)
    if has_conflict or hard_conflict:
        return Decision("abstained", "conflicting_evidence")
    if numeric_conflict:
        # Preserve the public legacy reason while retaining the stronger
        # internal numeric_conflict flag on the claim trace.
        return Decision("abstained", "unsupported_claim")
    if any(claim.status == "ambiguous" for claim in claims) or ambiguous:
        return Decision("abstained", "ambiguous_question")
    unsupported = [claim for claim in claims if claim.status in {"unsupported", "partial", "partially_supported"}]
    if unsupported and not allow_partial:
        return Decision("abstained", "unsupported_claim")
    if provider_abstained:
        return Decision("abstained", "provider_abstained")
    return Decision("answered")
