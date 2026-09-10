"""Deterministic execution planner."""
from dataclasses import dataclass
from .router import Route, route_question

@dataclass(frozen=True)
class Plan:
    route: Route
    steps: tuple[str, ...]

def plan_question(question: str) -> Plan:
    route = route_question(question)
    steps = ("retrieve", "calculate", "verify") if route.needs_calculation else ("retrieve", "verify")
    return Plan(route, steps)

class Planner:
    def plan(self, question: str) -> Plan: return plan_question(question)

