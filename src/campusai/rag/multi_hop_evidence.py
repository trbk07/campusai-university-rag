"""Source-owned premises from bounded retrieved tables, never the corpus/gold.

Rows retain their physical chunk/page and original column values. A projection
is only a context view; its coordinates refer to the unchanged source table.
"""
from dataclasses import asdict, dataclass, replace
import json
import re

from .course_credits import course_code_key, folded, headed_credit_rows
from .multi_hop import CODE


@dataclass(frozen=True)
class Premise:
    result: object
    headers: tuple
    row: tuple
    row_index: int
    code: str
    credits: int | None

    def proof(self):
        return dict(doc_id=self.result.doc_id, chunk_id=self.result.chunk_id,
                    page=self.result.page, table_row=self.row_index, code=self.code,
                    credits=self.credits, headers=list(self.headers), cells=list(self.row))


def table(content):
    start = content.find('{"headers"')
    try:
        value = json.loads(content[start:]) if start >= 0 else None
        if (isinstance(value, dict) and isinstance(value.get('headers'), list)
                and all(isinstance(h, str) for h in value['headers'])
                and isinstance(value.get('rows'), list)):
            return value
    except (ValueError, TypeError):
        pass
    return None


def name_matches(name, cell):
    def label(value):
        return folded(str(value).rstrip().rstrip('*').rstrip())
    if label(name) == label(cell):
        return True
    # Explicit bilingual table cells contain a Vietnamese name followed by
    # its English translation. Accept a complete language segment, never an
    # arbitrary substring such as 'Điện tử' inside 'Điện tử y sinh'.
    lines = str(cell).splitlines()
    return any(label(name) == label(' '.join(lines[:i]))
               and ' '.join(lines[i:]).isascii() for i in range(1, len(lines)))


def find_premise(results, doc_id, *, code=None, name=None, require_credits=True):
    matches = []
    for result in results:
        if result.doc_id != doc_id:
            continue
        value = table(result.content)
        if not value:
            continue
        name_cols = [i for i, h in enumerate(value['headers'])
                     if re.fullmatch(r'(?:hoc phan|ten hoc phan|course name|discipline)(?:\s*\(.*\))?',folded(h))]
        for found, credits, row in headed_credit_rows(result.content) or []:
            if code and found != code:
                continue
            if name and (len(name_cols) != 1 or len(row) <= name_cols[0]
                         or not name_matches(name, str(row[name_cols[0]]))):
                continue
            matches.append(Premise(result, tuple(value['headers']), tuple(row),
                                   value['rows'].index(row), found, credits))
    # Duplicated views of the same row are harmless. Conflicting values, names,
    # or prerequisite cells within this source are not silently pruned.
    identities = {(m.code, m.credits, m.headers, m.row) for m in matches}
    return matches[0] if len(identities) == 1 and (not require_credits or matches[0].credits is not None) else None


def prerequisite(premise):
    cols = [i for i, h in enumerate(premise.headers)
            if folded(h) in {'ma so hoc phan tien quyet', 'ma hoc phan tien quyet',
                             'hoc phan tien quyet', 'prerequisite', 'prerequisites',
                             'prerequisite code'}]
    if len(cols) != 1 or len(premise.row) <= cols[0]:
        return None
    cell = str(premise.row[cols[0]]).strip()
    # Only a single explicit identifier is supported as a dependent hop. OR,
    # several prerequisites, blank and prose do not become an invented edge.
    return course_code_key(cell) if CODE.fullmatch(cell) else None


def resolve_premises(plan, results):
    """Return (premises, edge, missing-hop search, problem). No retrieval here."""
    if plan.kind in {'compare', 'sum', 'difference'}:
        premises = [find_premise(results, r.doc_id, code=r.code) for r in plan.roles]
        if any(p is None for p in premises):
            return (), None, None, 'missing_or_conflicting_operand'
        return tuple(premises), None, None, None
    if plan.kind not in {'prerequisite_lookup', 'prerequisite_assertion', 'name_code_lookup'}:
        return (), None, None, plan.problem or 'unsupported_composition'
    role = plan.roles[0]
    parent = find_premise(results, role.doc_id, code=plan.target_code,
                          name=plan.lookup_name if plan.kind == 'name_code_lookup' else None,
                          require_credits=False)
    if parent is None:
        return (), None, None, 'missing_or_ambiguous_first_hop'
    bridge = parent.code if plan.kind == 'name_code_lookup' else prerequisite(parent)
    if not bridge or (plan.kind == 'prerequisite_assertion' and bridge != plan.claimed_bridge):
        return (parent,), None, None, 'direct_edge_not_established'
    edge = dict(kind='name_to_code_lookup' if plan.kind == 'name_code_lookup' else 'prerequisite',
                bridge_code=bridge, parent=parent.proof(), lookup_name=plan.lookup_name)
    if plan.kind == 'prerequisite_assertion':
        return (parent,), edge, None, None
    target_doc = plan.roles[1].doc_id if plan.kind == 'name_code_lookup' else role.doc_id
    child = find_premise(results, target_doc, code=bridge)
    if child is None:
        return (parent,), edge, dict(doc_id=target_doc, code=bridge), 'missing_or_conflicting_second_hop'
    return (parent, child), edge, None, None


def project(premises):
    """Keep exact required rows/headers within the existing context budget."""
    groups = {}
    for premise in premises:
        key = premise.result.chunk_id
        if key not in groups:
            groups[key] = [premise.result, premise.headers, [], []]
        group = groups[key]
        if premise.row_index not in group[3]:
            group[2].append(list(premise.row)); group[3].append(premise.row_index)
    return [replace(result, content=json.dumps(dict(headers=list(headers), rows=rows), ensure_ascii=False),
                    metadata={**result.metadata, 'source_table_rows':indices})
            for result, headers, rows, indices in groups.values()]


def retrieve_composition(plan, search, *, filters, mode, top_k):
    """One bounded pass, optionally one source-proved dependent lookup."""
    trace = dict(kind=plan.kind, roles=[asdict(r) for r in plan.roles],
                 search_calls=0, returned_candidates=0, premises=[], edge=None, problem=plan.problem)
    if plan.problem or top_k <= 0:
        trace['problem'] = plan.problem or 'retrieval_budget_empty'
        return [], trace
    dependent = plan.kind in {'prerequisite_lookup', 'prerequisite_assertion', 'name_code_lookup'}
    # This bounded composition path has no reranker or additional routing
    # searches, including when the application's historical default is Phase7.
    mode = 'hybrid' if mode in {'phase7', 'rerank', 'hybrid_rerank'} else mode
    scope = [plan.roles[0].doc_id] if dependent else list(dict.fromkeys(r.doc_id for r in plan.roles))
    query = (plan.lookup_name or plan.target_code if dependent
             else ' '.join(dict.fromkeys(r.code for r in plan.roles)))
    if not plan.lookup_name:
        query += ' credits prerequisite' if dependent else ' credits'
    candidates = search(query, doc_ids=scope, filters=filters, top_k=20, mode=mode, required_course_rows=True)
    trace.update(search_calls=1, returned_candidates=len(candidates))
    if len(candidates) > 20:
        trace['problem'] = 'retrieval_candidate_budget_exceeded'
        return [], trace
    # Do not accept an out-of-scope result from a faulty/custom retriever.
    candidates = [r for r in candidates[:20] if r.doc_id in scope]
    premises, edge, missing, problem = resolve_premises(plan, candidates)
    if missing:
        more = search(missing['code'], doc_ids=[missing['doc_id']], filters=filters, top_k=20, mode=mode, required_course_rows=True)
        trace.update(search_calls=2, returned_candidates=trace['returned_candidates']+len(more))
        if len(more) > 20:
            trace['problem'] = 'retrieval_candidate_budget_exceeded'
            return [], trace
        more = [r for r in more[:20] if r.doc_id == missing['doc_id']]
        premises, edge, _missing, problem = resolve_premises(plan, candidates+more)
    trace.update(premises=[p.proof() for p in premises], edge=edge, problem=problem)
    return ([] if problem else project(premises)), trace


def prerequisite_claim_support(text, evidence):
    """Direct relation needs a source row/statement, never endpoint overlap."""
    value = folded(text)
    if not re.search(r'\b(?:prerequisites?|tien quyet)\b', value):
        return None
    codes = [course_code_key(m[1]) for m in CODE.finditer(value)]
    if len(codes) != 2:
        # Existing single-code requirements use their established grounding.
        return None
    forward = (re.fullmatch(r'(?:course |mon )?' + re.escape(codes[0].lower())
        + r' (?:is (?:a )?(?:direct )?prerequisite of|la (?:mon )?tien quyet (?:truc tiep )?cua) '
        + r'(?:course |mon )?' + re.escape(codes[1].lower()) + r'[.!]?', value))
    if not forward:
        # Unrecognized two-endpoint relation must not fall back to lexical
        # composition. Additional supported forms can be added with tests.
        return False, ()
    used = []
    for record in evidence:
        p = find_premise([record], record.doc_id, code=codes[1],require_credits=False)
        if p and prerequisite(p) == codes[0]:
            used.append(record.chunk_id)
        # Exact standalone source statements also prove an edge; two separate
        # endpoint statements never do. No metadata or generated table header.
        elif not table(record.content):
            from ..retrieval.tokenizer_vi import source_body
            body=source_body({'content':record.content},decode_tables=False)
            if any(folded(sentence).rstrip('.!')==value.rstrip('.!')
                   for sentence in re.split(r'(?<=[.!?])\s+|\n+',body)):
                used.append(record.chunk_id)
    return bool(used), tuple(dict.fromkeys(used))


def name_code_claim_support(text, evidence):
    """Prove a named course's identifier from its own headed row.

    Canonical spacing of a code is not a numeric assertion. Bare numbers,
    prerequisite mentions and an unrelated row cannot prove this relation.
    Non-table statements retain their established text-grounding path.
    """
    value=folded(text)
    match=(re.fullmatch(r'(?:mon|hoc phan) (.+?) co ma(?: hoc phan)? ('+CODE.pattern+r')[.!]?',value)
           or re.fullmatch(r'(?:course )?(.+?) has (?:course )?code ('+CODE.pattern+r')[.!]?',value))
    if not match:
        return None
    name,code=match[1],course_code_key(match[2])
    tables=[r for r in evidence if headed_credit_rows(r.content) is not None]
    if not tables:
        return None
    supporting=[];conflict=False
    for record in tables:
        premise=find_premise([record],record.doc_id,name=name,require_credits=False)
        if premise:
            if premise.code==code:supporting.append(record.chunk_id)
            else:conflict=True
    correct=bool(supporting) and not conflict
    return correct,tuple(dict.fromkeys(supporting)) if correct else ()


def calculation_text(kind, roles, values, language='vi'):
    left, right = (f'{r.code} in {r.source_name}' for r in roles)
    a, b = values
    if language.casefold().startswith('en'):
        return (f'Total credits for {left} and {right} are {a+b}.' if kind == 'sum' else
                f'Credit difference for {left} minus {right} is {a} - {b} = {a-b} credits.')
    left, right = (f'{r.code} trong {r.source_name}' for r in roles)
    return (f'Tổng số tín chỉ của {left} và {right} là {a+b}.' if kind == 'sum' else
            f'Chênh lệch tín chỉ của {left} trừ {right} là {a} - {b} = {a-b} tín chỉ.')


def scoped_calculation_support(text, evidence):
    from .multi_hop import PDF, plan_request
    if not PDF.search(text) or not re.search(r'\b(?:total|difference|tong|chenh lech)\b', folded(text)):
        return None
    docs = {r.doc_id:dict(doc_id=r.doc_id, items=[dict(metadata={'source_name':r.source_name})])
            for r in evidence}
    plan = plan_request(text, list(docs.values()))
    if plan.kind not in {'sum', 'difference'} or plan.problem:
        return False, ()
    premises, _edge, _missing, problem = resolve_premises(plan, evidence)
    if problem:
        return False, ()
    expected = [calculation_text(plan.kind, plan.roles, [p.credits for p in premises], lang)
                for lang in ['en', 'vi']]
    correct = folded(text) in {folded(t) for t in expected}
    return correct, tuple(dict.fromkeys(p.result.chunk_id for p in premises)) if correct else ()


def deterministic_calculation(context, results, language):
    """Use already resolved, source-qualified operands; revalidate all claims."""
    from .grounding import Citation, _abstention, _grounding_finalize, validate_citation
    from .multi_hop import SourceRole
    if context['kind'] not in {'sum', 'difference'}:
        return None
    citations, claims = {}, []
    by_id = {r.chunk_id:r for r in results}
    for index, proof in enumerate(context['premises']):
        result = by_id[proof['chunk_id']]
        cite = Citation(result.chunk_id, result.doc_id, result.page,
                        json.dumps(proof['cells'], ensure_ascii=False),
                        ' > '.join(result.metadata.get('heading_path', [])),
                        result.metadata.get('source_name', ''),
                        tuple(result.metadata.get('page_range', [result.page, result.page])),
                        result.metadata.get('table_id', ''), result.metadata.get('source_hash', ''))
        if not validate_citation(cite, result, require_quote=True).valid:
            return _abstention('citation_not_in_evidence')
        citations[cite.chunk_id] = cite
        code, n = proof['code'], proof['credits']
        claims.append(dict(claim_id=str(index),text=f'Course {code} has {n} credits.' if language.startswith('en')
            else f'Môn {code} có {n} tín chỉ.',citation_ids=[cite.chunk_id],type='numeric_fact'))
    text = calculation_text(context['kind'], [SourceRole(**r) for r in context['roles']],
                            [p['credits'] for p in context['premises']], language)
    claims.append(dict(claim_id='calculation', text=text, citation_ids=list(citations), type='calculation',
                       required_citations=len(citations)))
    return _grounding_finalize(text, tuple(citations.values()), {'claims':claims}, results, language)


def composition_complete(answer, context, results):
    """Supported answer must cover each requested role and the actual edge."""
    if answer.abstained:
        return True
    claims = answer.claims
    for premise in context['premises']:
        code, credit, cid = premise['code'], premise['credits'], premise['chunk_id']
        # Parent rows of dependent joins prove an edge/name, not a requested
        # credit value. Child rows and both comparison arms require credits.
        parent = context['edge'] and context['edge']['parent'] == premise
        if parent:
            continue
        if not any(cid in c.citation_ids and c.status == 'supported'
                   and course_code_key(code) in {course_code_key(m[1]) for m in CODE.finditer(c.text)}
                   and re.search(r'\b' + str(credit) + r'\s+(?:credits?|tin chi)\b', folded(c.text))
                   for c in claims):
            return False
    edge = context['edge']
    if edge:
        cid = edge['parent']['chunk_id']
        if edge['kind'] == 'prerequisite':
            if not any(cid in c.citation_ids
                and [course_code_key(m[1]) for m in CODE.finditer(c.text)] == [edge['bridge_code'], edge['parent']['code']]
                and prerequisite_claim_support(c.text, [r for r in results if r.chunk_id == cid]) == (True, (cid,))
                for c in claims):
                return False
        else:
            if not any(cid in c.citation_ids and folded(edge['lookup_name']) in folded(c.text)
                       and edge['bridge_code'] in {course_code_key(m[1]) for m in CODE.finditer(c.text)}
                       and c.status == 'supported' for c in claims):
                return False
    return True
