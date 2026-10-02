"""Deterministic scoring input transforms; evidence coordinates stay intact."""
from __future__ import annotations

import re
import json
import math
import unicodedata
from collections import Counter

INPUT_VERSION = "structured-input-v1"
QUERY_MAX_CHARS = 2048
CONTENT_MAX_CHARS = 8192

FORMATS = ("full_chunk", "body", "section_body", "table_text", "table_window", "body_table_window")
_KEYS = {"Document type", "Academic years", "Semester", "Institution", "Program", "Section", "Page", "Pages"}


def scoring_text(text: str, input_format: str, query: str = "") -> str:
    if input_format not in FORMATS:
        raise ValueError("unsupported reranker input format")
    if input_format == "full_chunk":
        return text
    table_format = input_format.startswith("table_") or input_format == "body_table_window"
    focus = input_format in {"table_window", "body_table_window"}
    header, separator, remainder = text.partition("]\n")
    # Text chunks use a blank line; generated table chunks use one newline.
    # Accept the latter only for the known structured table representation.
    complete_header = separator and (remainder.startswith("\n") or remainder.startswith("Table headers:"))
    if not text.startswith("[") or not complete_header:
        table = render_table(text,query,focus) if table_format else None
        return table if table is not None else text
    body = remainder[1:] if remainder.startswith("\n") else remainder
    fields = header[1:].split(" | ")
    parsed = {}
    for field in fields:
        key, separator, value = field.partition(": ")
        if not separator or key not in _KEYS or key in parsed:
            return text
        parsed[key] = value
    page = parsed.get("Page", parsed.get("Pages", ""))
    if not re.fullmatch(r"[1-9]\d*(?:-[1-9]\d*)?", page) or not body.strip():
        return text
    if table_format:
        table = render_table(body,query,focus)
        if input_format == "body_table_window":
            return table if table is not None else body
        return header + "]\n\n" + table if table is not None else text
    if input_format == "section_body" and parsed.get("Section"):
        return parsed["Section"] + "\n\n" + body
    return body


def _plain(text):
    return "".join(c for c in unicodedata.normalize("NFD",text.casefold().replace("đ","d"))
                   if unicodedata.category(c) != "Mn")


def render_table(body, query, focus):
    display, separator, payload = body.partition("\n\n")
    if not separator or not display.startswith("Table headers:"):
        return None
    try:
        table = json.loads(payload)
    except (ValueError,TypeError):
        return None
    if not isinstance(table,dict):
        return None
    headers, rows = table.get("headers"), table.get("rows")
    if (not isinstance(headers,list) or not headers or any(not isinstance(h,str) for h in headers)
            or not isinstance(rows,list) or not rows or len(rows)>512
            or any(not isinstance(row,list) or len(row)>len(headers)
                   or any(not isinstance(cell,str) for cell in row) for row in rows)):
        return None
    chosen = list(range(len(rows)))
    if focus and query:
        section = re.compile(r"\b(?:semesters?|terms?|quarters?|hoc ky|ky)\s*(\d+)\b")
        headings = [(index,section.search(_plain(" ".join(row)))) for index,row in enumerate(rows)
                    if sum(bool(cell.strip()) for cell in row)==1]
        headings = [(index,match.group(1)) for index,match in headings if match]
        normalized_query = _plain(query)
        targets = {match.group(1) for match in section.finditer(normalized_query)}
        # A coordinated number retains the same unit: "semesters 7 and 8".
        for match in section.finditer(normalized_query):
            tail = normalized_query[match.end():]
            continuation = re.match(r"(?:\s*(?:,|va|and|&|hoac|or)\s*\d+\b)+", tail)
            if continuation:
                targets.update(re.findall(r"\d+",continuation.group()))
            interval = re.match(r"\s*(?:-|\u2013|\u2014|to|through|den)\s*(?:(?:semesters?|terms?|quarters?|hoc ky|ky)\s*)?(\d+)\b",tail)
            if interval:
                first,last = int(match.group(1)),int(interval.group(1))
                if abs(last-first)>512:
                    targets.add("unknown_range")
                else:
                    targets.update(str(number) for number in range(min(first,last),max(first,last)+1))
        known = {value for _,value in headings}
        if targets and targets <= known:
            selected = set()
            for start,value in headings:
                if value in targets:
                    end = next((index for index,_ in headings if index>start),len(rows))
                    selected.update(range(start,end))
            chosen = sorted(selected)
        elif not targets:
            words = [set(re.findall(r"[a-z]{3,}",_plain(" ".join(row)))) for row in rows]
            counts = Counter(word for tokens in words for word in tokens)
            query_words = set(re.findall(r"[a-z]{3,}",_plain(query)))
            scores = [sum(math.log(1+len(rows)/(1+counts[word])) for word in tokens & query_words) for tokens in words]
            best = max(range(len(rows)),key=lambda index:(scores[index],-index))
            # A single generic institution/subject token cannot trigger a crop.
            if len(words[best]&query_words)>=2 and scores[best]>=2:
                # Repeated subjects may be the object of a comparison. Keep
                # every equally supported occurrence and its section heading.
                selected = set()
                for index,score in enumerate(scores):
                    if score != scores[best]:
                        continue
                    selected.update(range(max(0,index-3),min(len(rows),index+4)))
                    earlier = [heading for heading,_ in headings if heading<=index]
                    if earlier:
                        selected.add(earlier[-1])
                chosen = sorted(selected)
    lines = ["Columns: "+" | ".join(headers)]
    if len(chosen)<len(rows):
        lines.append("Query-focused rows; omitted rows remain in the original source chunk.")
    if table.get("truncated") is True:
        lines.append("Original extracted table payload is truncated.")
    lines.extend(" | ".join(" ".join(cell.split()) for cell in rows[index]).strip(" |") for index in chosen)
    return "\n".join(lines)


