from campusai.rag.abstention import canonicalize_abstention_reason
from campusai.rag.claims import Claim, align_claims
from campusai.rag.claims import extract_claims
from campusai.rag.evidence import EvidenceRegistry
from campusai.rag.schemas import validate_release_response
from campusai.retrieval.hybrid import RetrievalResult
from campusai.retrieval.bm25_index import BM25Index


def evidence(chunk_id, content):
    return RetrievalResult(chunk_id, "doc", 1, content, "text", 1.0, "hybrid", {
        "page_range": [1, 1], "source_name": "catalog",
    })


def test_provider_reason_is_canonicalized_for_public_contract():
    assert canonicalize_abstention_reason("provider_abstained") == "provider_abstention"
    assert canonicalize_abstention_reason("citation_not_in_evidence") == "invalid_citation"


def test_multi_evidence_claim_keeps_only_supporting_chunks():
    registry = EvidenceRegistry([
        evidence("credits", "The programme requires 130 credits."),
        evidence("internship", "The programme also requires an internship."),
        evidence("unrelated", "The library closes at 17:00."),
    ])
    claim = Claim("claim-1", "The programme requires 130 credits and an internship.", citation_ids=("credits", "internship"))
    aligned = align_claims([claim], registry, {"claim-1": claim.citation_ids})
    assert aligned[0].status == "supported"
    assert aligned[0].citation_ids == ("credits", "internship")


def test_release_schema_rejects_unmapped_or_unquoted_citations():
    valid, errors = validate_release_response({
        "answer": "ok", "citations": [{
            "chunk_id": "c1", "doc_id": "d", "page": 1,
            "page_range": [1, 1], "quote": "fact", "source_name": "catalog",
        }],
        "claims": [{"claim_id": "claim-1", "text": "fact", "citation_ids": ["c1"]}],
        "confidence": "high", "abstained": False, "schema_version": "grounding-public-v2",
    })
    assert valid, errors
    invalid, errors = validate_release_response({
        "answer": "ok", "citations": [{"chunk_id": "c1", "doc_id": "d", "page": 1}],
        "claims": [], "confidence": "high", "abstained": False,
        "schema_version": "grounding-public-v2",
    })
    assert not invalid
    assert "citation_0_quote_missing" in errors


def test_release_schema_rejects_internal_nested_fields():
    valid, errors = validate_release_response({
        "answer": "ok", "citations": [{
            "chunk_id": "c1", "doc_id": "d", "page": 1,
            "page_range": [1, 1], "quote": "fact", "source_name": "catalog",
            "source_hash": "secret",
        }],
        "claims": [{"claim_id": "claim-1", "text": "fact", "citation_ids": ["c1"], "support_score": 1.0}],
        "confidence": "high", "abstained": False, "schema_version": "grounding-public-v2",
    })
    assert not valid
    assert "citation_0_unknown_source_hash" in errors
    assert "claim_0_unknown_support_score" in errors


def test_claim_markers_distinguish_year_polarity_and_qualifier():
    registry = EvidenceRegistry([evidence("c1", "CS201 is not required. At least 3 credits are needed in 2025.")])
    claims = extract_claims("CS201 is required. At least 3 credits are needed in 2026.")
    aligned = align_claims(claims, registry, {claim.claim_id: ("c1",) for claim in claims})
    assert any(claim.status == "contradicted" for claim in aligned)


def test_retrieval_indexes_stable_provenance_metadata():
    index = BM25Index([{
        "chunk_id": "c1", "doc_id": "doc-a", "content": "130 credits",
        "metadata": {"source_name": "computer_engineering_program.pdf"},
    }])
    assert index.search("computer_engineering_program", top_k=1)[0][0] == "c1"
