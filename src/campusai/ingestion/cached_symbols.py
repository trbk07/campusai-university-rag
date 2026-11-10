"""Upgrade old OCR grade modifiers from pixels without replacing source prose.

Only audited label changes may enter cached text/tables. Numeric values and
unrelated page text remains unchanged. A short-lived intent makes a
crash between parsed text and metadata publication recoverable without OCR.
"""
from dataclasses import replace
import hashlib
import json
import re
from pathlib import Path

from ..schemas import Document
from .chunker import make_chunks
from .ocr_symbols import (SYMBOL_POLICY, _SUSPECT, _numeric_field,
                          validate_symbol_review)


def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()


def source_digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def source_pages(text, count):
    markers=list(re.finditer(r'(?m)^## Page (\d+)\s*$',text))
    if [int(m[1]) for m in markers]!=list(range(1,count+1)):
        raise ValueError('cached symbol upgrade requires complete physical pages')
    return {int(m[1]):(m.end(),markers[i+1].start() if i+1<len(markers) else len(text))
            for i,m in enumerate(markers)}


def apply_patches(text, count, patches):
    spans=source_pages(text,count)
    for patch in sorted(patches,key=lambda p:spans[p['page']][0],reverse=True):
        start,end=spans[patch['page']];body=text[start:end]
        if body.count(patch['original'])!=1:raise ValueError('cached symbol line binding changed')
        text=text[:start]+body.replace(patch['original'],patch['replacement'],1)+text[end:]
    return text


def recover_upgrade(directory, source_sha256, *, atomic_text, table_writer):
    directory=Path(directory);intent_path=directory/'symbol-upgrade.json'
    if not intent_path.exists():return
    intent=json.loads(intent_path.read_text(encoding='utf-8'))
    document=Document.from_dict(intent['document'])
    if (intent['source_sha256']!=source_sha256 or document.doc_id!=source_sha256
            or document.metadata.get('source_hash')!=source_sha256):
        raise ValueError('symbol upgrade source identity mismatch')
    metadata_path=directory/'meta.json';parsed_path=directory/'parsed.md'
    new_metadata=json.dumps(document.to_dict(),ensure_ascii=False,indent=2)
    if (hashlib.sha256(metadata_path.read_bytes()).hexdigest()!=intent['previous_metadata_sha256']
            and metadata_path.read_text(encoding='utf-8')!=new_metadata):
        raise ValueError('symbol upgrade metadata changed concurrently')
    text=parsed_path.read_text(encoding='utf-8')
    if digest(text)==intent['previous_text_sha256']:
        text=apply_patches(text,document.page_count,intent['patches'])
    if digest(text)!=intent['updated_text_sha256']:raise ValueError('symbol upgrade text identity mismatch')
    atomic_text(parsed_path,text,encoding='utf-8')
    for table in document.tables:
        if table.table_id in intent['changed_table_ids']:table_writer(table,directory)
    atomic_text(metadata_path,new_metadata,encoding='utf-8')
    intent_path.unlink()


def upgrade_cached_symbols(document, pdf_path, directory, *, reader, max_pages,
                           timeout_seconds, data_dir, atomic_text, table_writer, progress=lambda *args:None):
    """Read at most three suspect pages; never adopt unrelated fresh OCR text."""
    directory=Path(directory);parsed_path=directory/'parsed.md'
    text=parsed_path.read_text(encoding='utf-8');spans=source_pages(text,document.page_count)
    if (document.status!='succeeded' or document.metadata.get('source_hash')!=document.doc_id
            or document.metadata.get('coverage_complete') is False or source_digest(pdf_path)!=document.doc_id):
        raise ValueError('symbol upgrade requires a complete source-bound cache')
    if (document.metadata.get('ocr_symbol_policy')==SYMBOL_POLICY
            and document.metadata.get('ocr_symbol_text_sha256')==digest(text)):
        return document
    bodies={n:text[a:b] for n,(a,b) in spans.items()}
    old_checks=document.metadata.get('ocr_symbol_checked_pages',{})
    import pymupdf
    native={}
    ocr_pages=set((document.metadata.get('ocr') or {}).get('page_numbers',[]))
    normalize=lambda value:' '.join(value.split())
    with pymupdf.open(pdf_path) as pdf:
        for number,body in bodies.items():
            if number not in ocr_pages:continue
            suspect=[line for line in body.splitlines() if _SUSPECT.match(line) and _numeric_field(line)]
            if suspect:native[number]=normalize(pdf[number-1].get_text(sort=True))
    candidates=[n for n,body in bodies.items() if n in native
        and any(_SUSPECT.match(line) and _numeric_field(line) and normalize(line) not in native[n] for line in body.splitlines())
        and old_checks.get(str(n))!={'policy':SYMBOL_POLICY,'text_sha256':digest(body)}]
    selected=candidates[:min(3,max_pages)];patches=[];checks=dict(old_checks);overlays=[];blocked=[]
    tables=list(document.tables);changed_tables=set()
    if selected:
        progress('ocr',0.)
        result=reader(pdf_path,max_pages=len(selected),page_numbers=selected,
            timeout_seconds=min(timeout_seconds,30),backend='tesseract',data_dir=data_dir,include_layout=True)
        if [p['page'] for p in result.pages]!=selected:raise ValueError('symbol upgrade OCR page coverage mismatch')
        with pymupdf.open(pdf_path) as pdf:
            for page in result.pages:
                number=page['page'];audit=page.get('symbol_review')
                if audit is not None:validate_symbol_review(audit,list(pdf[number-1].rect))
                for correction in (audit or {}).get('corrections',[]):
                    old,new=correction['original'],correction['replacement']
                    if bodies[number].count(old)!=1 or normalize(old) in native[number]:continue
                    before=_SUSPECT.match(old)
                    if before is None:raise ValueError('symbol upgrade original label missing')
                    old_label=before['label'];new_label=new[before.start('label'):before.start('label')+2]
                    affected=[i for i,t in enumerate(tables) if number in t.pages
                        and any(old_label in cell for row in [t.headers,*t.rows] for cell in row)]
                    # A derived table can be relabelled only when every covered
                    # source page contains exactly one occurrence in total.
                    # This prevents changing another semester/table's same tag.
                    if any(sum(bodies[n].count(old_label) for n in tables[i].pages)!=1 for i in affected):
                        blocked.append({'page':number,'label':old_label,'reason':'ambiguous_table_source_label'});continue
                    patches.append({'page':number,'original':old,'replacement':new})
                    overlays.append({'page':number,'correction':correction,'model_identity':result.model_identity})
                    for i in affected:
                        table=tables[i]
                        schema={**table.schema,'source_symbol_overlay':[
                            *table.schema.get('source_symbol_overlay',[]),{'page':number,**correction}]}
                        tables[i]=replace(table,headers=[c.replace(old_label,new_label) for c in table.headers],
                            rows=[[c.replace(old_label,new_label) for c in row] for row in table.rows],schema=schema)
                        changed_tables.add(table.table_id)
                checks[str(number)]={'policy':SYMBOL_POLICY,'text_sha256':digest(bodies[number])}
        progress('ocr',1.)
    updated=apply_patches(text,document.page_count,patches)
    updated_spans=source_pages(updated,document.page_count)
    for number in selected:
        a,b=updated_spans[number];checks[str(number)]['text_sha256']=digest(updated[a:b])
        for line in updated[a:b].splitlines():
            label=_SUSPECT.match(line)
            if label and _numeric_field(line) and normalize(line) not in native[number]:
                if not any(x['page']==number and x['label']==label['label'] for x in blocked):
                    blocked.append({'page':number,'label':label['label'],'reason':'not_independently_verified'})
    metadata={**document.metadata,'ocr_symbol_checked_pages':checks,
        'ocr_symbol_pending_pages':candidates[len(selected):],
        'ocr_symbol_unresolved':blocked,'ocr_symbol_overlays':[
            *document.metadata.get('ocr_symbol_overlays',[]),*overlays]}
    if not metadata['ocr_symbol_pending_pages']:
        metadata.update(ocr_symbol_policy=SYMBOL_POLICY,ocr_symbol_text_sha256=digest(updated))
    # A historical OCR checkpoint remains retained, but cannot overwrite the
    # newly verified source when a future parser upgrade resumes ingestion.
    if patches:
        metadata['ocr_symbol_invalidated_checkpoint']=metadata.pop('ocr_pages_sha256',None)
        metadata.pop('ocr_resume_identity',None)
    pages=[{'page':n,'text':updated[a:b]} for n,(a,b) in updated_spans.items()]
    diagnostics={};chunks=make_chunks(pages,document.doc_id,metadata,tables,diagnostics=diagnostics)
    metadata['chunk_diagnostics']=diagnostics
    refreshed=replace(document,metadata=metadata,chunks=chunks,tables=tables)
    progress('chunking',1.)
    if source_digest(pdf_path)!=document.doc_id:raise ValueError('symbol upgrade source changed during OCR')
    intent={'source_sha256':document.doc_id,'previous_metadata_sha256':hashlib.sha256((directory/'meta.json').read_bytes()).hexdigest(),
        'previous_text_sha256':digest(text),'updated_text_sha256':digest(updated),
        'patches':patches,'changed_table_ids':sorted(changed_tables),'document':refreshed.to_dict()}
    atomic_text(directory/'symbol-upgrade.json',json.dumps(intent,ensure_ascii=False,indent=2),encoding='utf-8')
    recover_upgrade(directory,document.doc_id,atomic_text=atomic_text,table_writer=table_writer)
    return refreshed
