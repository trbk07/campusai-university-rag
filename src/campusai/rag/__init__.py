"""Grounded answer services built on CampusAI retrieval results."""

from .grounding import Citation, GroundedAnswer, GroundedAnswerGenerator
from .cache import RAGAnswerCache, build_rag_cache_key, normalize_question
from .service import CampusAIQueryService
from .evidence import EvidenceRecord, EvidenceRegistry
from .claims import Claim, extract_claims, align_claims
from .abstention import AbstentionReason
from .confidence import Confidence, POLICY_VERSION
from .calibration import IsotonicCalibrator, CALIBRATION_VERSION

__all__ = [
    "CampusAIQueryService",
    "Citation",
    "GroundedAnswer",
    "GroundedAnswerGenerator",
    "RAGAnswerCache",
    "build_rag_cache_key",
    "normalize_question",
    "EvidenceRecord",
    "EvidenceRegistry",
    "Claim",
    "extract_claims",
    "align_claims",
    "AbstentionReason",
    "Confidence",
    "POLICY_VERSION",
    "IsotonicCalibrator",
    "CALIBRATION_VERSION",
]
