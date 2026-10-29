"""Physical column proofs for unruled PDF tables, never benchmark fixtures."""
import json
import pymupdf
import pytest
from campusai.ingestion.table_extractor import extract_tables, TABLE_EXTRACTOR_VERSION
from campusai.ingestion.chunker import _looks_like_heading
from campusai.rag.course_credits import headed_credit_rows
from campusai.rag.policies import has_conflicting_numeric_evidence
from campusai.retrieval.hybrid import RetrievalResult


def source(path,credits=3,header=True,misalign=False,boxed_bands=False):
    doc=pymupdf.open();page=doc.new_page()
    page.insert_text((40,40),'Unruled catalogue table',fontsize=14)
    if boxed_bands:page.draw_rect(pymupdf.Rect(36,64,550,97),fill=(.9,.95,.95))
    if header:
        for x,text in [(40,'Course code'),(170,'Course name'),(360,'Hours'),(450,'Credits')]:page.insert_text((x,80),text,fontsize=10)
    for i in range(5):
        y=110+i*22
        if boxed_bands and i%2==0:page.draw_rect(pymupdf.Rect(36,y-13,550,y+9),fill=(.95,.95,.95))
        for x,text in [(40,f'ZEN{3101+i}'),(170,f'Example Course {i+1}'),(360,'48'),(450,str(credits))]:
            page.insert_text((x,y+(7 if misalign and x==450 and i==2 else 0)),text,fontsize=10)
    doc.save(path);text=page.get_text();doc.close()
    return [{'page':1,'text':text}]


def test_coloured_bands_do_not_hide_remaining_rows_as_one_column_table(tmp_path):
    path=tmp_path/'bands.pdf';tables=extract_tables(source(path,boxed_bands=True),'source-a',path)
    assert len(tables)==1 and len(tables[0].headers)==4 and len(tables[0].rows)==5
    assert tables[0].rows[-1]==['ZEN3105','Example Course 5','48','3']


@pytest.mark.parametrize('old_version', ['table-v2-aligned-course-columns', 'table-v4-physical-course-scope', 'table-v5-partial-numeric-grid'])
def test_ingestion_records_new_producer_versions_and_preserves_course_rows(tmp_path, old_version):
    import json
    from campusai.ingestion.pipeline import ingest_document
    path=tmp_path/'ingested.pdf';source(path,boxed_bands=True)
    store=tmp_path/'store'
    document=ingest_document(path,store_dir=store)
    assert document.metadata['chunker_version']=='structure-v6'
    assert document.metadata['table_extractor_version']==TABLE_EXTRACTOR_VERSION
    tables=[c for c in document.chunks if c.content_type=='table']
    assert len(tables)==1 and len(headed_credit_rows(tables[0].content))==5
    assert not any(c.metadata.get('heading_path')==['ZEN3101'] for c in document.chunks)

    cached=ingest_document(path,store_dir=store)
    assert cached.cached
    metadata_path=store/document.doc_id/'meta.json'
    payload=json.loads(metadata_path.read_text(encoding='utf-8'))
    payload['metadata']['table_extractor_version']=old_version
    metadata_path.write_text(json.dumps(payload),encoding='utf-8')
    refreshed=ingest_document(path,store_dir=store)
    assert not refreshed.cached
    assert refreshed.metadata['table_extractor_version']==TABLE_EXTRACTOR_VERSION
    assert len([c for c in refreshed.chunks if c.content_type=='table'])==1


def test_unruled_columns_keep_headers_cells_units_and_source_coordinates(tmp_path):
    path=tmp_path/'unruled.pdf';tables=extract_tables(source(path), 'source-a',path)
    assert len(tables)==1
    table=tables[0]
    assert table.headers==['Course code','Course name','Hours','Credits']
    assert table.rows[0]==['ZEN3101','Example Course 1','48','3']
    assert table.schema['parser']=='pdfplumber-aligned-course-columns-v1'
    assert table.schema['raw_preserved'] and len(table.schema['row_bboxes'])==5
    rows=headed_credit_rows(json.dumps({'headers':table.headers,'rows':table.rows}))
    assert len(rows)==5 and rows[0][1]==3


def test_split_single_row_fragments_inherit_only_verified_semester_course_headers():
    from pathlib import Path

    source_pdf=Path('data/corpus/university/uet_mai_joint_curriculum_2022.pdf')
    assert source_pdf.is_file()
    with pymupdf.open(source_pdf) as document:
        pages=[{'page':number,'text':page.get_text()} for number,page in enumerate(document,start=1)]
    tables=extract_tables(pages,'mai-joint',source_pdf)
    semester_four=[table for table in tables if table.pages==[2] and
                   table.schema.get('parser')=='pdfplumber-inherited-course-columns-v2']

    assert len(semester_four)==3
    assert all('Credits' in table.headers for table in semester_four)
    rows=[row for table in semester_four for row in table.rows]
    assert ['2','Strength of Materials','3','VNU-UET'] in rows
    assert ['1','History of Vietnam Communist Party','2','VNU-UET'] in rows
    # Preserve the prior-semester spillover as unscoped; it must never acquire
    # the later Semester 4 marker merely because both share one table fragment.
    spillover = next(table for table in semester_four if
                     any('Fluid mechanics' in cell for row in table.rows for cell in row))
    assert not spillover.schema.get('section')
    fluid_index = next(i for i, row in enumerate(spillover.rows) if 'Fluid mechanics' in row)
    assert spillover.schema['row_scopes'][fluid_index] is None
    from campusai.ingestion.chunker import make_chunks
    chunks=make_chunks(pages,'mai-joint',{},tables)
    strength_chunk=next(chunk for chunk in chunks if chunk.content_type=='table' and
                        'Strength of Materials' in chunk.content)
    assert 'Table scope: Semester 4' in strength_chunk.content
    assert strength_chunk.metadata['table_scope_provenance']=='explicit_pdf_marker'
    strength_table=next(table for table in semester_four if
                        any('Strength of Materials' in cell for row in table.rows for cell in row))
    headed=headed_credit_rows(json.dumps({'headers':strength_table.headers,'rows':strength_table.rows}),identity='name')
    assert len(headed)==1 and headed[0][1]==3


@pytest.mark.parametrize('options',[{'header':False},{'misalign':True}])
def test_missing_header_or_ambiguous_row_alignment_cannot_invent_credit_table(tmp_path,options):
    path=tmp_path/'uncertain.pdf'
    assert extract_tables(source(path,**options),'source',path)==[]


def test_source_conflict_is_distinguished_from_a_wrong_model_claim(tmp_path):
    results=[]
    for name,credits in [('first',3),('second',4)]:
        path=tmp_path/(name+'.pdf');tables=extract_tables(source(path,credits),name,path)
        assert len(tables)==1
        table=tables[0]
        results.append(RetrievalResult(name,name,1,json.dumps({'headers':table.headers,'rows':table.rows}),'table',1.0,'source',{}))
    assert has_conflicting_numeric_evidence(results,'How many credits does ZEN3101 carry?')
    assert not has_conflicting_numeric_evidence(results,'Compare the credits of ZEN3101 in the two sources.')


@pytest.mark.parametrize('code',['ZEN3101','CS 201','CO.CS2101','ABC7101A'])
def test_course_ids_are_not_structural_headings(code):
    assert _looks_like_heading(code)[0] is False
