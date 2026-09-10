"""Prompt template for planning a financial QA task."""

def build_planner_prompt(question: str) -> str:
    return f"Phân loại câu hỏi và chọn các bước retrieve, calculate, verify cho câu hỏi: {question}"

