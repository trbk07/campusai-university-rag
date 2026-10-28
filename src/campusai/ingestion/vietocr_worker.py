"""Isolated, bounded Vietnamese OCR; stdout uses the existing OCR protocol."""
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time


def emit(value):
    print(json.dumps(value,ensure_ascii=True,allow_nan=False),flush=True)


def local_module(name):
    spec = importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def reading_order(lines, *, ruled=False):
    """Keep ruled/numeric tables row-major; split clear prose-column gutters."""
    if len(lines)<2: return list(lines)
    if not ruled and sum(row['text'].strip().isdigit() for row in lines)<len(lines)*.25:
        intervals = sorted((row['bbox'][0],row['bbox'][2]) for row in lines)
        lo,hi = intervals[0][0],max(right for _,right in intervals)
        union=[]
        for left,right in intervals:
            if union and left<=union[-1][1]+2: union[-1][1]=max(union[-1][1],right)
            else: union.append([left,right])
        gaps=[(b[0]-a[1],(b[0]+a[1])/2) for a,b in zip(union,union[1:])
            if b[0]-a[1]>.03*(hi-lo) and lo+.2*(hi-lo)<(b[0]+a[1])/2<lo+.8*(hi-lo)]
        if gaps:
            _,cut=max(gaps)
            left=[row for row in lines if row['bbox'][2]<cut]
            right=[row for row in lines if row['bbox'][0]>cut]
            if len(left)>=3 and len(right)>=3 and len(left)+len(right)==len(lines):
                return reading_order(left)+reading_order(right)
    ordered=sorted(lines,key=lambda r:(r['bbox'][1],r['bbox'][0]))
    # RapidOCR's physical top-edge ordering, expressed in PDF points rather
    # than render pixels. Centre grouping scrambles mixed-height table cells.
    for i in range(len(ordered)-1):
        for j in range(i,-1,-1):
            a,b=ordered[j],ordered[j+1]
            if abs(a['bbox'][1]-b['bbox'][1])<5 and b['bbox'][0]<a['bbox'][0]:
                ordered[j],ordered[j+1]=b,a
            else: break
    return ordered


def main():
    os.environ.update(OMP_THREAD_LIMIT='1',OMP_NUM_THREADS='1')
    raw=sys.stdin.readline(2*1024*1024+1)
    if len(raw)>2*1024*1024: raise ValueError('OCR request bound')
    request=json.loads(raw)
    assets=local_module('ocr_assets')
    identity=assets.validate_vietocr_assets(request['data_dir'])
    if request['model_sha256']!=assets.VIETOCR_SHA256: raise ValueError('OCR identity mismatch')
    import cv2
    import numpy as np
    import pymupdf as fitz
    from PIL import Image
    import torch
    from rapidocr_onnxruntime.ch_ppocr_det import TextDetector
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    Recognizer=local_module('vietocr_recognizer').Recognizer
    grid=local_module('ocr_tables')
    root=Path(request['data_dir'])
    recognizer=Recognizer(root/'vgg_seq2seq.pth')
    detector=TextDetector({'model_path':str(root/'detector.onnx'),
        'intra_op_num_threads':1,'inter_op_num_threads':1,'use_cuda':False,'use_dml':False,
        'limit_side_len':736,'limit_type':'min','std':[.5]*3,'mean':[.5]*3,
        'thresh':.3,'box_thresh':.5,'max_candidates':1000,'unclip_ratio':1.6,
        'use_dilation':True,'score_mode':'fast'})
    scale=request['scale']
    if type(scale) not in (int,float) or not math.isfinite(scale) or not 2<=scale<=4:
        raise ValueError('OCR scale bound')
    emit({'type':'ready','engine':identity['engine'],'model_sha256':assets.VIETOCR_SHA256,
          'device':recognizer.device})
    with fitz.open(request['path']) as pdf:
        for number in request['page_numbers']:
            if type(number) is not int or not 1<=number<=len(pdf): raise ValueError('OCR page bound')
            page=pdf[number-1];bounds=page.rect*page.derotation_matrix
            regions=request.get('hybrid_regions',{}).get(str(number))
            lines,audits,confidences,tables=[],[],[],[]
            for region in regions or [list(bounds)]:
                area=fitz.Rect(region)
                if area.is_empty or not bounds.contains(area): raise ValueError('OCR region outside page')
                if area.get_area()*scale**2>20_000_000: emit({'type':'limit'});return 2
                pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=area*page.rotation_matrix,
                                    alpha=False,colorspace=fitz.csRGB)
                image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                array=np.asarray(image)
                boxes,_=detector(array[:,:,::-1].copy())
                boxes=[] if boxes is None else sorted(boxes,key=lambda b:(b[0][1],b[0][0]))
                if len(boxes)>4096: raise ValueError('OCR detection bound')
                crops=[]
                for box in boxes:
                    x0,y0=box.min(axis=0);x1,y1=box.max(axis=0)
                    crops.append(image.crop((max(0,int(x0)-2),max(0,int(y0)-2),
                        min(image.width,int(x1)+3),min(image.height,int(y1)+3))))
                recognized=recognizer.predict(crops)
                pixel_words=[]
                for box,(text,confidence) in zip(boxes,recognized):
                    if not text.strip() or not math.isfinite(confidence) or confidence<.5: continue
                    x0,y0=box.min(axis=0);x1,y1=box.max(axis=0)
                    pixel_words.append({'text':text.strip(),'bbox':[float(x0),float(y0),float(x1),float(y1)],
                                        'confidence':confidence})
                # Ruling lines prevent table columns being mistaken for prose columns.
                gray=cv2.cvtColor(array,cv2.COLOR_RGB2GRAY)
                def read_boxes(boxes):
                    return recognizer.predict([image.crop(tuple(box)) for box in boxes])
                assembled=grid.assemble_tables(gray,pixel_words,read_boxes)
                def physical(box):
                    x0,y0,x1,y1=box
                    return list(fitz.Rect((x0+pix.x)/scale,(y0+pix.y)/scale,
                        (x1+pix.x)/scale,(y1+pix.y)/scale)*page.derotation_matrix)
                current=[{'text':word['text'],'bbox':physical(word['bbox'])} for word in assembled['words']]
                confidences.extend(word['confidence'] for word in assembled['words'])
                for table in assembled['tables']:
                    table={**table,'bbox':physical(table['bbox']),
                        'row_bboxes':[physical(box) for box in table['row_bboxes']],
                        'header_bboxes':[physical(box) for box in table['header_bboxes']],
                        'header_spans':[{**span,'bbox':physical(span['bbox'])} for span in table['header_spans']],
                        'row_spans':[{**span,'bbox':physical(span['bbox'])} for span in table['row_spans']],
                        'geometry_coordinates':'PDF points for boxes;render pixels for grid edges',
                        'render_scale':scale,'render_origin':[pix.x,pix.y]}
                    tables.append(table)
                ink=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]
                horizontal=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,max(40,pix.width//5)),np.uint8))
                vertical=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((max(40,pix.height//5),1),np.uint8))
                ruled=bool(np.count_nonzero(horizontal)>pix.width*2 and np.count_nonzero(vertical)>pix.height*2)
                lines.extend(reading_order(current,ruled=ruled))
                if regions: audits.append({'bbox':region,'outcome':'recognized' if current else 'unreadable'})
            row={'type':'page','page':number,'text':'\n'.join(line['text'] for line in lines),
                 'confidence':sum(confidences)/len(confidences) if confidences else 0.}
            if request.get('include_layout'): row['lines']=lines
            if regions: row['image_audit']=audits
            if tables: row['ocr_tables']=tables
            emit(row)
    emit({'type':'done'});return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception:
        emit({'type':'error'});raise SystemExit(1)
