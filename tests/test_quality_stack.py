"""Regression tests for retrieval, tools, verification, and evaluation contracts."""
import pandas as pd
import pytest
from agentic_rag.retrieval.bm25_retriever import BM25Retriever
from agentic_rag.retrieval.dense_retriever import DenseRetriever
from agentic_rag.retrieval.reranker import LexicalReranker
from agentic_rag.tools.calculator_tool import calculate
from agentic_rag.tools.table_query_tool import query_table
from agentic_rag.verification.answer_verifier import verify_answer
from evaluation.benchmark_builder import validate_cases
from evaluation.run_eval import evaluate
from agentic_rag.pipeline.hybrid_rag import HybridRAG
from agentic_rag.pipeline.adaptive_agentic_rag import AdaptiveAgenticRAG
from agentic_rag.agent.router import route_question

ITEMS = [{"id": "revenue", "text": "Doanh thu năm 2024 là 100 tỷ đồng"}, {"id": "cost", "text": "Chi phí năm 2024 là 40 tỷ đồng"}]

def test_retrieval_and_reranking():
    assert BM25Retriever(ITEMS).retrieve("doanh thu")[0].item["id"] == "revenue"
    assert DenseRetriever(ITEMS).retrieve("doanh thu")[0].item["id"] == "revenue"
    results = BM25Retriever(ITEMS).retrieve("doanh thu")
    assert LexicalReranker().rerank("doanh thu", results)[0].item["id"] == "revenue"

def test_safe_tools():
    assert calculate("2 * (3 + 4)").value == 14
    assert not calculate("__import__('os').system('x')").ok
    table = pd.DataFrame({"amount": [10, 20]})
    assert query_table(table, "sum", "amount").value == 30.0
    assert not query_table(table, "eval", "amount").ok

def test_grounded_answer():
    result = verify_answer("100 tỷ đồng", evidence={"revenue": "Doanh thu năm 2024 là 100 tỷ đồng"}, citations=["revenue"], expected="100 tỷ đồng")
    assert result["reliable"] and result["answer_match"]

def test_evaluation_contract():
    cases = validate_cases([{"id": "q1", "question": "Doanh thu?", "answer": "100 tỷ đồng", "evidence": ["revenue"]}])
    report = evaluate(cases, lambda _: {"answer": "100 tỷ đồng", "retrieved": ["revenue"], "citations": ["revenue"]})
    assert report["answer"]["exact_match"] == 1.0
    assert report["retrieval"]["recall@5"] == 1.0
    assert report["citation"]["citation_precision"] == 1.0

def test_end_to_end_rag_pipeline():
    response = AdaptiveAgenticRAG(ITEMS).answer("Doanh thu năm 2024 là bao nhiêu?")
    assert response.evidence and response.citations
    assert response.route == "table"
    assert response.verification["reliable"]
    assert route_question("Tính tỷ lệ tăng trưởng").name == "calculation"


def test_benchmark_validation_rejects_duplicate_ids():
    case = {"id": "q1", "question": "?", "answer": "x", "evidence": []}
    with pytest.raises(ValueError): validate_cases([case, case])
