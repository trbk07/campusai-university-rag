"""Prompt template for grounded financial answers."""

def build_answer_prompt(question: str, context: str) -> str:
    return f"""Trả lời câu hỏi tài chính bằng tiếng Việt, chỉ dùng bằng chứng bên dưới. Nếu thiếu bằng chứng, nói rõ không đủ dữ liệu.\nCâu hỏi: {question}\nBằng chứng:\n{context}\nNêu số liệu chính xác và citation ID."""

