"""Bounded physical page selections; never expand user-sized numeric ranges."""
import re

PAGE_REQUEST = re.compile(r'\b(?:pages?|trang)\s+(\d+)(?:\s*(?:[-–]|đến|den|to|through)\s*(\d+))?', re.I)


def page_intervals(question):
    return [(int(start), int(end or start)) for start,end in PAGE_REQUEST.findall(question)]


def select_physical_pages(question, count, *, maximum=12):
    intervals = page_intervals(question)
    if not intervals:
        return None, None
    if any(start < 1 or end < start or end > count for start,end in intervals):
        return [], 'page_scope_unavailable'
    # Iterate only the actual validated PDF count, not an attacker's range.
    selected = [page for page in range(1,count+1) if any(start <= page <= end for start,end in intervals)]
    if len(selected) > maximum:
        return [], 'page_scope_too_large'
    return selected, None
