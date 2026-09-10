"""Deterministic question router for financial RAG."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Route:
    name: str
    needs_calculation: bool = False
    needs_table: bool = False

def route_question(question: str) -> Route:
    text = question.casefold()
    calculation = any(word in text for word in ("tăng bao nhiêu", "giảm bao nhiêu", "tỷ lệ", "phần trăm", "%", "tính"))
    table = any(word in text for word in ("bảng", "cột", "hàng", "doanh thu", "chi phí", "tài sản"))
    name = "calculation" if calculation else "table" if table else "fact"
    return Route(name, calculation, table)

class Router:
    def route(self, question: str) -> Route: return route_question(question)

