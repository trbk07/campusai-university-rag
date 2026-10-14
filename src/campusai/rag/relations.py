"""Bounded relation request shapes and source-validated local composition."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .course_credits import course_code_key,folded
from .multi_hop import CODE,PDF,SourceRole,_names
from .multi_hop_evidence import project


@dataclass(frozen=True)
class RelationRequest:
    kind: str
    source: SourceRole | None = None
    code: str | None = None
    credits: bool = False
    name: bool = False
    problem: str | None = None


def answer_policy_fingerprint():
    base=Path(__file__).parent
    return hashlib.sha256(b''.join((base/name).read_bytes() for name in [
        'relations.py','claims.py','grounding.py','evidence.py','schemas.py','confidence.py','decision.py'])).hexdigest()


def plan_relation(question,documents):
    """Recognize bounded shapes; do not silently discard extra conditions."""
    raw=str(question);clean=PDF.sub(' ',raw);text=folded(clean)
    if not re.search(r'\b(?:tien quyet|prerequisites?)\b',text):
        return None
    if re.search(r'\b(?:automatic equivalence|tu dong duoc cong nhan|cong nhan thay the|transferable)\b',text):
        return None
    codes=tuple(dict.fromkeys(course_code_key(m[1]) for m in CODE.finditer(clean)))
    body=CODE.sub('code',text)
    body=re.sub(r'[,.?;:]+',' ',body)
    body=' '.join(body.split())
    body=re.sub(r'^(?:theo|trong|in|according to)\s+','',body)
    direct=(r'(?:hoc phan |mon )?tien quyet(?: truc tiep)? cua code (?:co ma gi va )?(?:co )?bao nhieu tin chi(?: trong cung tai lieu)?'
            r'|xac dinh duy nhat mot mon tien quyet truc tiep cua code va so tin chi mon do'
            r'|what is the direct prerequisite of code and how many credits does it have')
    inverse=(r'liet ke (?:day du )?cac hoc phan co code la tien quyet truc tiep dan nguon cho tung quan he'
             r'|which courses list code as a direct prerequisite list all of them with source evidence')
    chain=(r'di theo (?:hai buoc tien quyet lien tiep|chuoi hai buoc tien quyet) bat dau tu code neu ca hai quan he va (?:so tin chi cua mon|ten mon) cuoi chuoi'
           r'|follow two consecutive direct prerequisite links from code state both links and (?:the credit value|the name) of the last course')
    kind=next((k for k,pattern in [('direct',direct),('inverse',inverse),('chain2',chain)] if re.fullmatch(pattern,body)),None)
    if kind is None:
        assertion=(r'(?:chung minh|prove|confirm) (?:mon |course )?code '
                   r'(?:la (?:mon )?tien quyet (?:truc tiep )?cua|is (?:a )?(?:direct )?prerequisite of) '
                   r'(?:mon |course )?code')
        if re.fullmatch(assertion,body) or not codes and not re.search(r'\b(?:buoc|steps?|links?|liet ke|which courses)\b',body):
            return None
        return RelationRequest('unresolved',problem='unsupported_relation_request_shape')
    if len(codes)!=1:
        return RelationRequest(kind,problem='relation_entity_ambiguous')
    names=_names(documents);roles=[]
    refs=list(PDF.finditer(raw))
    for ref in refs:
        found=names.get(ref[1].casefold(),[])
        if len(found)!=1:
            return RelationRequest(kind,problem='relation_source_missing_or_ambiguous')
        if found[0] not in roles:
            roles.append(found[0])
    if not refs:
        roles=[r for values in names.values() for r in values]
    if len(roles)!=1:
        return RelationRequest(kind,problem='relation_source_role_ambiguous')
    return RelationRequest(kind,roles[0],codes[0],bool(re.search(r'\b(?:tin chi|credits?|credit value)\b',body)),
                           bool(re.search(r'\b(?:ten mon|the name)\b',body)))


def relation_results(outcome):
    results=project(outcome['premises'])
    have={r.chunk_id for r in results}
    for entry in outcome['edge_evidence'].values():
        if entry['result'].chunk_id not in have:
            results.append(entry['result']);have.add(entry['result'].chunk_id)
    return results


def compose_relation(plan,outcome,generator,language='vi'):
    """Use actual source rows and the existing validators; no LLM boundary."""
    from .grounding import (Citation,_abstention,_grounding_finalize,build_context,
                            validate_citation,estimate_tokens)
    if outcome['trace']['problem']:
        return _abstention('insufficient_evidence')
    results=relation_results(outcome)
    context=build_context(results,min(12000,generator.max_context_chars),max_tokens=generator.max_context_tokens)
    if ('[truncated=true]' in context or any('chunk_id='+r.chunk_id+'\n' not in context for r in results)
            or any(json.dumps(list(p.row),ensure_ascii=False) not in context for p in outcome['premises'])):
        return _abstention('context_budget_exceeded')
    citations={};claims=[];source_rows={}
    for premise in sorted(outcome['premises'],key=lambda p:(p.result.chunk_id,p.row_index)):
        group=source_rows.setdefault(premise.result.chunk_id,[])
        if list(premise.row) not in group:
            group.append(list(premise.row))
    def row_quote(premise):
        group=source_rows[premise.result.chunk_id]
        return json.dumps(group[0] if len(group)==1 else group,ensure_ascii=False)
    def cite(result,quote):
        existing=citations.get(result.chunk_id)
        if existing is not None:
            return existing.chunk_id
        c=Citation(result.chunk_id,result.doc_id,result.page,quote,
            ' > '.join(result.metadata.get('heading_path',[])),result.metadata.get('source_name',''),
            tuple(result.metadata.get('page_range',[result.page,result.page])),
            result.metadata.get('table_id',''),result.metadata.get('source_hash',''))
        if not validate_citation(c,result,require_quote=True).valid:
            raise ValueError('relation_citation_invalid')
        citations[c.chunk_id]=c
        return c.chunk_id
    def claim(text,cid):
        claims.append(dict(claim_id=f'r{len(claims)+1}',text=text,citation_ids=[cid],type='fact'))
    try:
        for parent,child in outcome['edges']:
            statement=outcome['edge_evidence'].get((parent.code,child.code))
            if statement:
                text=statement['quote'];cid=cite(statement['result'],text)
            else:
                cid=cite(parent.result,row_quote(parent))
                text=(f'Course {child.code} is a direct prerequisite of {parent.code}.' if language.startswith('en')
                      else f'Môn {child.code} là tiên quyết trực tiếp của {parent.code}.')
            claim(text,cid)
        final=outcome['final']
        if plan.credits:
            if final.credits is None:
                return _abstention('insufficient_evidence')
            cid=cite(final.result,row_quote(final))
            claim(f'Course {final.code} has {final.credits} credits.' if language.startswith('en')
                  else f'Môn {final.code} có {final.credits} tín chỉ.',cid)
        if plan.name:
            name=outcome['nodes'][final.code].get('name')
            if not name:
                return _abstention('insufficient_evidence')
            name=' '.join(name.split());cid=cite(final.result,row_quote(final))
            claim(f'Course {name} has course code {final.code}.' if language.startswith('en')
                  else f'Môn {name} có mã {final.code}.',cid)
        answer=f"{plan.source.source_name}:\n"+'\n'.join(c['text'] for c in claims)
        payload=dict(claims=claims)
        output_cap=min(1024,(getattr(generator.llm,'generation_config',None) or {}).get('maxOutputTokens',1024))
        if len(answer)>1600 or estimate_tokens(json.dumps(dict(answer=answer,claims=claims,
                citations=[c.to_dict() for c in citations.values()]),ensure_ascii=False))>output_cap:
            return _abstention('context_budget_exceeded')
        result=_grounding_finalize(answer,tuple(citations.values()),payload,results,language,calibrator=generator.calibrator)
        if result.abstained or len(result.claims)!=len(claims) or any(c.status!='supported' for c in result.claims):
            return _abstention('unsupported_claim')
        return result
    except (KeyError,TypeError,ValueError):
        return _abstention('invalid_citation')
