"""Dependency-free Pareto frontier calculation for evaluation reports."""

def pareto_frontier(rows: list[dict], *, accuracy_key: str = "accuracy", latency_key: str = "latency_ms") -> list[dict]:
    """Return rows not dominated by another row (higher accuracy, lower latency)."""
    frontier = []
    for candidate in rows:
        dominated = any(other is not candidate and other.get(accuracy_key, 0) >= candidate.get(accuracy_key, 0)
                        and other.get(latency_key, float("inf")) <= candidate.get(latency_key, float("inf"))
                        and (other.get(accuracy_key, 0) > candidate.get(accuracy_key, 0)
                             or other.get(latency_key, float("inf")) < candidate.get(latency_key, float("inf")))
                        for other in rows)
        if not dominated: frontier.append(candidate)
    return frontier
