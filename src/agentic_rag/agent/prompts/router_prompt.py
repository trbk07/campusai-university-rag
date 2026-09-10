"""Prompt template for routing financial questions."""

def build_router_prompt(question: str) -> str:
    return f"Chọn fact, table hoặc calculation cho câu hỏi tài chính sau: {question}"

