"""Dependency-free request/response schemas for the optional API."""
from dataclasses import dataclass, field

@dataclass
class QueryRequest:
    question: str
    top_k: int = 5

@dataclass
class QueryResponse:
    answer: str
    citations: list[str] = field(default_factory=list)
    verification: dict = field(default_factory=dict)

