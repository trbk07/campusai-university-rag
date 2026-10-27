"""Physical parallel decoding must preserve ordered cross-page table semantics."""
from dataclasses import asdict
from types import SimpleNamespace

import pymupdf as fitz
import pytest

from campusai.ingestion import table_extractor as module


@pytest.fixture
def continuation(tmp_path):
    path = tmp_path/'controlled-continuation.pdf'
    with fitz.open() as pdf:
        for number in range(1,49):
            page = pdf.new_page()
            page.insert_text((50,50), f'CONTROLLED TEST - native page {number}')
            if number not in (24,25): continue
            rows = ([['No','Subject','Credits','Resources'],['1','Course A','3','Provider A'],
                     ['2','Course B','5','Provider A']] if number==24 else
                    [['3','Course C','4','Provider A'],['4','Course D','6','Provider A']])
            xs = (50,90,300,380,500); ys = [80+30*i for i in range(len(rows)+1)]
            for x in xs: page.draw_line((x,ys[0]),(x,ys[-1]))
            for y in ys: page.draw_line((xs[0],y),(xs[-1],y))
            for y,row in zip(ys,rows):
                for x,value in zip(xs,row):page.insert_text((x+5,y+20),value,fontsize=10)
        pdf.save(path)
    return path


def test_real_workers_preserve_header_inheritance_across_batch_boundary(continuation, monkeypatch):
    monkeypatch.setattr(module.os,'cpu_count',lambda:4)
    parallel = module._extract_pdfplumber(continuation,'controlled')
    monkeypatch.setattr(module,'_table_page_packets',lambda path,doc,visibility:
                        module._read_page_batch(path,doc,range(1,49),visibility))
    sequential = module._extract_pdfplumber(continuation,'controlled')
    assert [asdict(t) for t in parallel] == [asdict(t) for t in sequential]
    later = next(t for t in parallel if t.pages==[25])
    assert later.headers==['No','Subject','Credits','Resources']
    assert later.rows==[['3','Course C','4','Provider A'],['4','Course D','6','Provider A']]
    assert later.schema['header_source']['page']==24


def test_broken_pool_discards_partial_results_before_sequential_fallback(continuation, monkeypatch):
    from concurrent.futures.process import BrokenProcessPool
    import concurrent.futures
    class Pool:
        def __init__(self, **kwargs): self.calls=0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self,*args):
            self.calls+=1
            def result():
                if self.calls==2: raise BrokenProcessPool('controlled unavailable worker')
                return [{'page':999}]
            # Freeze submission order, independent of when result() is called.
            if self.calls==1: return SimpleNamespace(result=lambda:[{'page':999}])
            return SimpleNamespace(result=result)
    monkeypatch.setattr(concurrent.futures,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(module.os,'cpu_count',lambda:4)
    packets=module._table_page_packets(continuation,'controlled',None)
    assert [p['page'] for p in packets]==list(range(1,49))
    assert any(p['records'] for p in packets)
