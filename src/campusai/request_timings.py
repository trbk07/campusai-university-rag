"""Request-local internal timing; never added to the public answer contract."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import time

_current = ContextVar("campusai_request_timings", default=None)


def record_stage(name: str, milliseconds: float):
    trace = _current.get()
    if trace is not None:
        trace["stages_ms"][name] = trace["stages_ms"].get(name, 0.0) + max(0.0, milliseconds)
        trace["stage_calls"][name] = trace["stage_calls"].get(name, 0) + 1


@contextmanager
def capture_request():
    trace = {"stages_ms": {}, "stage_calls": {}}
    token = _current.set(trace)
    started = time.perf_counter()
    try:
        yield trace
    finally:
        trace["server_total_ms"] = (time.perf_counter() - started) * 1000
        _current.reset(token)


@contextmanager
def stage(name: str):
    if _current.get() is None:
        yield
        return
    started = time.perf_counter()
    try:
        yield
    finally:
        record_stage(name, (time.perf_counter() - started) * 1000)


def timed_stage(name: str):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            with stage(name):
                return function(*args, **kwargs)
        return call
    return decorate
