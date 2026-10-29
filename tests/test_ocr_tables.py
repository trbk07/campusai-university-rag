"""Pixel-geometry unit tests; mocked word recognition is not OCR accuracy."""
import copy
import hashlib
import json

import numpy as np
from PIL import Image,ImageDraw,ImageFont
import pytest

from campusai.ingestion.docling_parser import TEXT_COVERAGE_VERSION
from campusai.ingestion.ocr_tables import ruled_tables,assemble_tables,validate_tables


def fixture(*, missing_rule=False, joined_word=False, offset=0):
    image=Image.new('L',(1000,430),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=17);small=ImageFont.load_default(size=14)
    xs=[20,100,280,650,740,900,980];ys=[20,90,160,230,300,370]
    for x in xs:
        if not (missing_rule and x==650):draw.line((x,20,x,370),fill=0,width=2)
    for y in ys:draw.line((20,y,980,y),fill=0,width=2)
    words=[]
    def text(value,x,y,*,chosen=font):
        box=draw.textbbox((x,y),value,font=chosen);draw.text((x,y),value,font=chosen,fill=0)
        words.append({'text':value,'bbox':list(box),'confidence':.99});return words[-1]
    for label,x in [('No',40),('Course code',130),('Course name',410),('Credits',660),('Hours',785),('Prerequisite',903)]:
        text(label,x,35,chosen=small if label=='Prerequisite' else font)
    qualifier='(in English and in Vietnamese)'
    width=draw.textlength(qualifier,font=small)
    text(qualifier,643-width,61,chosen=small)
    expected=[]
    for i,name in enumerate(['Analysis','embedded','Networks','Laboratory']):
        y=110+70*i;code=f'ABC{101+i+offset}';credit=str([2,4,7,9][i]);hours=str([30,60,21,70][i])
        text(str(i+1),40,y);text(code,125,y);name_word=text(name,565 if joined_word and i==1 else 300,y)
        numeric=text(credit,680,y);text(hours,790,y);text('XYZ100',906,y,chosen=small)
        if joined_word and i==1:
            words.remove(numeric);name_word['bbox'][2]=numeric['bbox'][2]+2
        expected.append((code,credit,hours,'XYZ100'))
    return np.array(image),words,expected


@pytest.mark.parametrize('missing_rule',[False,True])
@pytest.mark.parametrize('offset',[0,217])
def test_literal_headers_and_pixels_keep_credit_hours_and_prerequisite_columns(missing_rule,offset):
    gray,words,expected=fixture(missing_rule=missing_rule,offset=offset)
    tables=ruled_tables(gray,words)
    assert len(tables)==1
    table=tables[0]
    assert table['headers'][1:]==['Course code','Course name','Credits','Hours','Prerequisite']
    assert [(row[1],row[3],row[4],row[5]) for row in table['rows']]==expected
    assert bool(table['inferred_columns'])==missing_rule
    assert 'in English' in table['header_notes']['2']


def test_joined_name_and_credit_box_cannot_publish_a_table_without_pixel_reinspection():
    gray,words,_=fixture(missing_rule=True,joined_word=True)
    assert ruled_tables(gray,words)==[]
    seen=[]
    def recognize(boxes):
        seen.extend(boxes)
        assert len(boxes)==2 and boxes[0][2]<boxes[1][0]
        return [('embedded',.98),('4',.97)]
    result=assemble_tables(gray,words,recognize)
    assert len(seen)==2 and len(result['tables'])==1
    assert result['tables'][0]['rows'][1][2:5]==['embedded','4','60']
    assert len(result['repairs'])==2
    assert words[10:]  # Caller-owned recognized words remain available for audit.


@pytest.mark.parametrize('prediction',[[('embedded',.98),('4',.89)],[('embedded',.98),('unknown',.99)]])
def test_uncertain_or_non_numeric_reinspection_never_gets_a_default_value(prediction):
    gray,words,_=fixture(missing_rule=True,joined_word=True)
    result=assemble_tables(gray,words,lambda boxes:prediction)
    assert result['tables']==[] and result['repairs']==[] and result['words']==words


def test_unheaded_or_cross_row_words_fail_closed():
    gray,words,_=fixture()
    assert ruled_tables(gray,[w for w in words if w['text']!='Credits'])==[]
    broken=copy.deepcopy(words)
    body=next(w for w in broken if w['text']=='ABC101');body['bbox'][1]=145;body['bbox'][3]=185
    assert ruled_tables(gray,broken)==[]


@pytest.mark.parametrize('fault',['outside','nan','unresolved','row_width','parser'])
def test_worker_table_schema_cannot_escape_page_or_publish_unresolved_values(fault):
    gray,words,_=fixture();table=ruled_tables(gray,words)[0]
    if fault=='outside':table['bbox']=[-1,0,100,100]
    if fault=='nan':table['row_bboxes'][0][0]=float('nan')
    if fault=='unresolved':table['unresolved_cells']=[{'value':''}]
    if fault=='row_width':table['rows'][0].pop()
    if fault=='parser':table['parser']='untrusted'
    with pytest.raises(ValueError):validate_tables([table],[0,0,1000,430])


def test_optical_tables_keep_document_page_and_have_typed_grounding():
    from campusai.ingestion.table_extractor import extract_tables
    from campusai.rag.course_credits import course_credit_support
    gray,words,_=fixture(missing_rule=True)
    tables=extract_tables([{'page':3,'text':'original OCR source','ocr_tables':ruled_tables(gray,words)}],'document')
    assert len(tables)==1 and tables[0].doc_id=='document' and tables[0].pages==[3]
    payload=json.dumps({'headers':tables[0].headers,'rows':tables[0].rows})
    assert course_credit_support('ABC101 has 2 credits.',payload) is True
    assert course_credit_support('ABC101 has 30 credits.',payload) is False
    assert course_credit_support('XYZ100 has 2 credits.',payload) is None


def test_new_optical_policy_invalidates_job_cache_but_retains_old_vietocr_identity():
    from campusai.ingestion.background.state import normalize_options,job_identity,accepted_job_identities
    from campusai.ingestion.table_extractor import TABLE_EXTRACTOR_VERSION
    options=normalize_options({'ocr_backend':'vietocr'})
    old=hashlib.sha256(json.dumps({'source_sha256':'a'*64,'options':options,'text_coverage_version':3},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert old!=job_identity('a'*64,options) and old in accepted_job_identities('a'*64,options)
    default=normalize_options({})
    previous_options={k:v for k,v in default.items() if k!='progressive_ocr'}
    expected=hashlib.sha256(json.dumps({'source_sha256':'a'*64,'options':previous_options,
        'text_coverage_version':TEXT_COVERAGE_VERSION,'table_extractor_version':TABLE_EXTRACTOR_VERSION},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert expected==job_identity('a'*64,default)
    assert job_identity('a'*64,{**default,'progressive_ocr':True})!=expected


def test_missing_pixels_in_a_split_never_discard_the_original_word():
    gray,words,_=fixture(missing_rule=True,joined_word=True)
    original=copy.deepcopy(words)
    gray[175:205,560:650]=255
    result=assemble_tables(gray,words,lambda boxes:pytest.fail('Incomplete split must not be recognized'))
    assert result['words']==original and not result['tables'] and not result['repairs']


@pytest.mark.parametrize('overlap',[False,True])
def test_hybrid_native_overlay_never_becomes_an_optical_table(overlap):
    from campusai.ingestion.pipeline import _merge_hybrid_page
    gray,words,_=fixture()
    table=ruled_tables(gray,words)[0]
    native_box=[30,110,60,130] if overlap else [30,1,60,10]
    native={'hybrid_layout':[{'text':'Native source','bbox':native_box}],
            'ocr_regions':[[0,0,1000,430]],'lines_meta':[]}
    recognized={'text':'Read from pixels','lines':[{'text':'Read from pixels','bbox':[300,110,400,130]}],
                'image_audit':[{'outcome':'recognized','bbox':[0,0,1000,430]}],'ocr_tables':[table]}
    merged=_merge_hybrid_page(native,recognized)
    assert 'Native source' in merged['text'] and 'Read from pixels' in merged['text']
    assert len(merged['ocr_tables'])==int(not overlap)


def test_other_worker_backend_cannot_claim_optical_table_provenance(tmp_path,monkeypatch):
    from test_tesseract_process import worker,recognize
    from campusai.ingestion.ocr import OCRUnavailable
    gray,words,_=fixture()
    row={'type':'page','page':2,'text':'source','confidence':.99,'ocr_tables':ruled_tables(gray,words)}
    worker(monkeypatch,'print('+repr(json.dumps(row))+',flush=True)')
    with pytest.raises(OCRUnavailable,match='table'):
        recognize(tmp_path)
