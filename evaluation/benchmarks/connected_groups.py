"""Connected leakage families shared by splitting, audits and statistics.

Sharing a PDF does not imply dependence. Only declared family links and
normalized duplicate/paraphrase questions connect records.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

FAMILY_FIELDS = ("intent_family", "query_family", "paraphrase_group", "source_group", "template_group")


def normalized_question(text: str) -> str:
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


def connected_groups(rows: list[dict], *, near_matches: bool = True) -> dict[str, str]:
    qids = [row["qid"] for row in rows]
    if any(not isinstance(qid, str) or not qid for qid in qids) or len(qids) != len(set(qids)):
        raise ValueError("connected groups require unique nonempty qids")
    parent = {qid: qid for qid in qids}

    def find(qid):
        while parent[qid] != qid:
            parent[qid] = parent[parent[qid]]
            qid = parent[qid]
        return qid

    def union(left, right):
        left, right = find(left), find(right)
        parent[max(left, right)] = min(left, right)

    seen, questions = {}, []
    for row in rows:
        qid = row["qid"]
        links = [(field, row[field].strip().casefold()) for field in FAMILY_FIELDS
                 if isinstance(row.get(field), str) and row[field].strip()]
        question = normalized_question(row.get("question", ""))
        if question:
            links.append(("question", question))
        for link in links:
            if link in seen:
                union(qid, seen[link])
            else:
                seen[link] = qid
        questions.append((qid, set(question.split())))
    if near_matches:
        for index, (qid, tokens) in enumerate(questions):
            if len(tokens) < 6:
                continue
            for other_qid, other in questions[index + 1:]:
                if len(other) >= 6 and len(tokens & other) / len(tokens | other) >= .85:
                    union(qid, other_qid)
    members = {}
    for qid in qids:
        members.setdefault(find(qid), []).append(qid)
    names = {root: "family-" + hashlib.sha256("\n".join(sorted(group)).encode()).hexdigest()[:20]
             for root, group in members.items()}
    return {qid: names[find(qid)] for qid in qids}
