"""Citation support checks for grounded answers."""
from typing import Iterable

def check_citations(predicted: Iterable[str], supported: Iterable[str]) -> dict[str, object]:
    predicted_set, supported_set = set(predicted), set(supported)
    unsupported = sorted(predicted_set - supported_set)
    missing = sorted(supported_set - predicted_set)
    return {"valid": not unsupported, "unsupported": unsupported, "missing": missing,
            "precision": len(predicted_set & supported_set) / len(predicted_set) if predicted_set else 1.0,
            "recall": len(predicted_set & supported_set) / len(supported_set) if supported_set else 1.0}

