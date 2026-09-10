"""Optional API factory; FastAPI remains an optional deployment dependency."""
from agentic_rag.pipeline.hybrid_rag import HybridRAG

def create_app(items=()):
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("Install FastAPI to expose the HTTP API") from exc
    pipeline = HybridRAG(items)
    app = FastAPI(title="Adaptive Financial RAG")
    @app.get("/health")
    def health(): return {"status": "ok"}
    @app.post("/query")
    def query(payload: dict):
        response = pipeline.answer(str(payload.get("question", "")), top_k=int(payload.get("top_k", 5)))
        return {"answer": response.answer, "citations": response.citations, "verification": response.verification}
    return app

