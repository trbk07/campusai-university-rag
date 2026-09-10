"""Safe loader for common JSON/JSONL benchmark formats."""
import json
from pathlib import Path

def load_external(path: str | Path) -> list[dict]:
    source = Path(path)
    if source.suffix.casefold() == ".jsonl":
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
        rows = payload.get("data", payload.get("cases", payload)) if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows): raise ValueError("Benchmark must be a list of objects")
    return rows
