"""Latency and cost metrics for reproducible evaluation."""
from __future__ import annotations
from dataclasses import dataclass
from statistics import mean, median
from time import perf_counter
from typing import Callable, Any

@dataclass(frozen=True)
class Timing:
    elapsed_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

def timed_call(function: Callable[..., Any], *args: Any, input_tokens: int = 0,
               output_tokens: int = 0, input_cost_per_1k: float = 0.0,
               output_cost_per_1k: float = 0.0, **kwargs: Any) -> tuple[Any, Timing]:
    started = perf_counter()
    result = function(*args, **kwargs)
    elapsed = (perf_counter() - started) * 1000
    cost = input_tokens / 1000 * input_cost_per_1k + output_tokens / 1000 * output_cost_per_1k
    return result, Timing(elapsed, input_tokens, output_tokens, cost)

def latency_report(samples: list[Timing]) -> dict[str, float]:
    if not samples:
        return {"count": 0, "mean_ms": 0.0, "median_ms": 0.0, "p95_ms": 0.0, "cost_usd": 0.0}
    values = sorted(sample.elapsed_ms for sample in samples)
    index = min(len(values) - 1, max(0, int(len(values) * 0.95 + 0.999) - 1))
    return {"count": len(values), "mean_ms": round(mean(values), 4),
            "median_ms": round(median(values), 4), "p95_ms": round(values[index], 4),
            "cost_usd": round(sum(sample.cost_usd for sample in samples), 8)}

