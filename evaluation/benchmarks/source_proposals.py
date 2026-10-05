"""Conservative source-fact history screen; no heldout approval or model calls."""
from __future__ import annotations

import re
from pathlib import Path

from .connected_groups import connected_groups, normalized_question
from .source_course_rows import normalized_header, source_course_rows
from evaluation.common.release_artifacts import sha256


def alias_key(text: str) -> str:
    return normalized_question(normalized_header(text))


def course_aliases(fact: dict) -> set[str]:
    """Include wrapped Vietnamese/English names without assuming a language split."""
    lines = [alias_key(line) for line in fact['name_lines'] if line.strip()]
    aliases = {alias_key(fact['name'])}
    aliases.update(' '.join(lines[start:end])
                   for start in range(len(lines))
                   for end in range(start + 1, len(lines) + 1))
    return {name for name in aliases if len(name) >= 8}


def history_inventory(directories: list[Path]) -> tuple[list[dict], list[dict]]:
    import json

    paths = sorted({p for directory in directories for p in directory.rglob('*.jsonl')})
    questions, datasets = [], []
    for path in paths:
        digest = sha256(path)
        datasets.append({'path': path.as_posix(), 'sha256': digest})
        for line_number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f'history row must be an object: {path}:{line_number}')
            question = row.get('question', row.get('query', ''))
            if question:
                if not isinstance(question, str):
                    raise ValueError(f'history question must be text: {path}:{line_number}')
                questions.append({'question': question, 'qid': row.get('qid'),
                                  'dataset': path.as_posix(), 'dataset_sha256': digest,
                                  'line': line_number})
    return questions, datasets


def screen_source_facts(evidence: dict, documents: set[str], history: list[dict]) -> dict:
    # Include indexed ancestors when forming families. The proposal scope
    # limits output only; an older PDF's translation can expose a new PDF row.
    facts = source_course_rows(evidence)
    normalized = [(alias_key(item['question']), item) for item in history]
    # Build families before screening: an exposed translation or spelling in
    # one PDF consumes the same course in every other PDF, including aliases
    # attached to another code. Keep this conservative, like alias screening.
    parent = list(range(len(facts)))

    def find(number):
        while parent[number] != number:
            parent[number] = parent[parent[number]]
            number = parent[number]
        return number

    seen = {}
    for number, fact in enumerate(facts):
        links = [('code', fact['code'])]
        links.extend(('alias', name.replace(' ', '')) for name in course_aliases(fact))
        for link in links:
            if link in seen:
                left, right = find(number), find(seen[link])
                parent[max(left, right)] = min(left, right)
            else:
                seen[link] = number
    matches = {}
    for number, fact in enumerate(facts):
        aliases = course_aliases(fact)
        letters, digits, suffix = re.fullmatch(r'([A-Z]+)(\d+)([A-Z]?)', fact['code']).groups()
        code = re.compile(r'(?<![a-z0-9])' + letters.casefold() + r'\s*' + digits
                          + suffix.casefold() + r'(?![a-z0-9])')
        match = None
        for question, origin in normalized:
            compact = question.replace(' ', '')
            alias = next((name for name in sorted(aliases) if name.replace(' ', '') in compact), None)
            if code.search(question) or alias:
                match = {'origin': origin, 'matched_alias': alias,
                         'code_mentioned': bool(code.search(question))}
                break
        if match:
            matches[number] = match
    exposed = {}
    for number, match in matches.items():
        exposed.setdefault(find(number), (number, match))
    proposed, excluded = [], []
    for number, fact in enumerate(facts):
        if fact['doc_id'] not in documents:
            continue
        if find(number) in exposed:
            origin_number, match = exposed[find(number)]
            excluded.append({'fact': fact,
                             'reason': ('historical_code_or_name_mention' if number in matches
                                        else 'connected_source_family_exposed'),
                             **matches.get(number, match),
                             'exposed_source_fact': facts[origin_number]})
        else:
            proposed.append(fact)
    groups = connected_groups([{'qid': str(i), 'question': '', 'source_group': str(find(number))}
                               for i, number in enumerate(n for n in range(len(facts))
                                                          if facts[n]['doc_id'] in documents
                                                          and find(n) not in exposed)])
    for number, fact in enumerate(proposed):
        fact['connected_group'] = groups[str(number)]
    return {'status': 'source_proposal', 'release_eligible': False,
            'explicit_course_rows': sum(f['doc_id'] in documents for f in facts),
            'indexed_family_rows_checked': len(facts), 'proposed_rows': len(proposed),
            'proposed_connected_groups': len(set(groups.values())),
            'excluded': excluded, 'proposals': proposed,
            'limits': ['Automatic exact code and bilingual/wrapped-name screening is not semantic exposure approval.',
                       'No benchmark questions, split eligibility, review approval or model scores are assigned.']}
