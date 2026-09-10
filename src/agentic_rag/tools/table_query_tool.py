"""Safe, explicit operations over extracted pandas tables."""
from typing import Any
from .base_tool import ToolResult, failure, success

_ALLOWED = {"head", "columns", "sum", "mean", "row_count"}

def query_table(table: Any, operation: str, column: str | None = None, *, limit: int = 20) -> ToolResult:
    if operation not in _ALLOWED:
        return failure(f"Unsupported table operation: {operation}")
    try:
        if operation == "columns": return success([str(value) for value in table.columns])
        if operation == "row_count": return success(int(len(table)))
        if operation == "head": return success(table.head(max(0, min(limit, 100))).to_dict(orient="records"))
        if not column or column not in table.columns: return failure("A valid column is required")
        values = table[column].dropna()
        return success(float(values.sum() if operation == "sum" else values.mean()))
    except (AttributeError, TypeError, ValueError) as exc:
        return failure(f"Table query failed: {exc}")

class TableQueryTool:
    def run(self, table: Any, operation: str, column: str | None = None, *, limit: int = 20) -> ToolResult:
        return query_table(table, operation, column, limit=limit)
