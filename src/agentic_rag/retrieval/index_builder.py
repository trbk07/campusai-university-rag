"""Small, portable JSON index persistence helpers."""
import json
from pathlib import Path
from typing import Any, Iterable


def build_index(items: Iterable[Any], path: str | Path, *, text_key: str = "text") -> dict[str, Any]:
    records = list(items)
    payload = {"version": 1, "text_key": text_key, "items": records}
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    return payload


def load_index(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("items"), list):
        raise ValueError("Unsupported or invalid index format")
    return payload["items"]

