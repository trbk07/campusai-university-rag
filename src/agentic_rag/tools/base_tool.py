"""Common tool result and validation primitives."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ToolResult:
    ok: bool
    value: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

def success(value: Any, **metadata: Any) -> ToolResult:
    return ToolResult(True, value=value, metadata=metadata)

def failure(error: str, **metadata: Any) -> ToolResult:
    return ToolResult(False, error=error, metadata=metadata)

