"""Bounded raster verification of ambiguous printed grade-label modifiers.

No grade scale or expected answer enters this pass. Only an independently read
label may replace its suspect modifier; every original word/number stays intact.
"""
import math
import re
import unicodedata

SYMBOL_POLICY = 'raster-grade-label-v1'
_SUSPECT = re.compile(r'(?m)^[ \t]*(?P<label>[ABCDF][tTyY*†\x27’])(?=\s*:)')
_READ = re.compile(r'^[ \t]*(?P<label>[ABCDF][+\-])(?=\s*:)')
_NUMBER = re.compile(r'\d+(?:[.,]\d+)?')


def has_ambiguous_label(text):
    return bool(_SUSPECT.search(text))


def _interval(text):
    value=''.join(c for c in unicodedata.normalize('NFD',text.casefold())
                  if not unicodedata.combining(c)).replace('đ','d')
    return bool(re.search(r':\s*(?:tu\s+|from\s+)?\d+(?:[.,]\d+)?\s+'
                          r'(?:den|to|[-–—÷])\s+\d+(?:[.,]\d+)?',value))


def verified_label_replacement(original, observed, confidence):
    """A changed number, letter, uncertain glyph or low confidence cannot pass."""
    old=_SUSPECT.match(original);new=_READ.match(observed)
    if (not old or not new or old['label'][0]!=new['label'][0]
            or isinstance(confidence,bool) or not isinstance(confidence,(int,float))
            or not math.isfinite(confidence) or not .9<=confidence<=1
            or not _interval(original) or not _interval(observed)):
        return None
    numbers=lambda s:[n.replace(',','.').rstrip('0').rstrip('.') if '.' in n.replace(',','.')
                      else n for n in _NUMBER.findall(s)]
    if numbers(original)!=numbers(observed):return None
    return original[:old.start('label')]+new['label']+original[old.end('label'):]


def _valid_box(box):
    return (isinstance(box,(list,tuple)) and len(box)==4
            and all(not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v) for v in box)
            and box[0]<box[2] and box[1]<box[3])


def _same_line(first,second):
    if not _valid_box(first) or not _valid_box(second):return False
    overlap=max(0,min(first[3],second[3])-max(first[1],second[1]))
    width=max(0,min(first[2],second[2])-max(first[0],second[0]))
    return (overlap>=.6*min(first[3]-first[1],second[3]-second[1])
            and width>=.6*min(first[2]-first[0],second[2]-second[0]))


class RasterLabelVerifier:
    """Lazy CPU reader, at most four labels/page and twelve/worker invocation."""
    def __init__(self):
        self.engine=None
        self.identity=None
        self.unavailable=False
        self.remaining=12

    def _load(self):
        if self.unavailable:raise RuntimeError('label verifier unavailable')
        if self.engine is None:
            from contextlib import redirect_stdout
            import sys
            with redirect_stdout(sys.stderr):
                from .ocr_assets import validate_rapidocr_assets
                self.identity=validate_rapidocr_assets()
                import cv2
                cv2.setNumThreads(1)
                from rapidocr_onnxruntime import RapidOCR
                self.engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1,print_verbose=False,
                    det_use_cuda=False,cls_use_cuda=False,rec_use_cuda=False,
                    det_use_dml=False,cls_use_dml=False,rec_use_dml=False)

    @staticmethod
    def _image(page,box):
        import pymupdf as fitz
        import numpy as np
        bounds=page.rect*page.derotation_matrix
        rect=(fitz.Rect(box)+(-20,-5,20,5)) & bounds
        if rect.is_empty or rect.get_area()*9>600_000:return None
        pix=page.get_pixmap(matrix=fitz.Matrix(3,3),clip=rect*page.rotation_matrix,
                            colorspace=fitz.csRGB,alpha=False)
        data=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
        return data,pix

    def _group(self,page,boxes):
        import pymupdf as fitz
        box=[min(b[0] for b in boxes),min(b[1] for b in boxes),
             max(b[2] for b in boxes),max(b[3] for b in boxes)]
        if box[3]-box[1]>160:return []
        image=self._image(page,box)
        if image is None:return []
        data,pix=image
        output,_=self.engine(data)
        rows=[]
        for points,text,score in output or []:
            rect=fitz.Rect(min(p[0] for p in points),min(p[1] for p in points),
                           max(p[0] for p in points),max(p[1] for p in points))
            rect=fitz.Rect((rect.x0+pix.x)/3,(rect.y0+pix.y)/3,
                           (rect.x1+pix.x)/3,(rect.y1+pix.y)/3)*page.derotation_matrix
            rows.append({'text':text,'confidence':float(score),'bbox':list(rect)})
        return rows

    def _lines(self,page,boxes):
        images=[];valid=[]
        for box in boxes:
            # A recognizer-only pass must contain just this line, not its neighbour.
            image=self._image(page,[box[0],box[1]+3,box[2],box[3]-3]) if box[3]-box[1]>6 else None
            if image is not None:images.append(image[0]);valid.append(box)
        if not images:return []
        output,_=self.engine.text_rec(images)
        if len(output)!=len(valid):return []
        return [{'text':text,'confidence':float(score),'bbox':box}
                for (text,score),box in zip(output,valid)]

    def refine(self,page,text,lines):
        candidates=[r for r in lines if isinstance(r.get('text'),str)
                    and _SUSPECT.match(r['text']) and _interval(r['text'])
                    and _valid_box(r.get('bbox')) and len(r['text'])<=512
                    and text.count(r['text'])==1]
        if not candidates:return text,lines,None
        audit={'policy':SYMBOL_POLICY,'status':'budget_exhausted','model_identity':None,'corrections':[]}
        selected=candidates[:min(4,self.remaining)]
        if not selected:return text,lines,audit
        self.remaining-=len(selected)
        try:
            self._load()
            observed=self._group(page,[r['bbox'] for r in selected])
            audit.update(status='checked',model_identity=self.identity)
            def match(row,observations):
                choices=[]
                for other in observations:
                    if not _same_line(row['bbox'],other['bbox']):continue
                    replacement=verified_label_replacement(row['text'],other['text'],other['confidence'])
                    if replacement is not None:choices.append((replacement,other))
                return choices[0] if len(choices)==1 else False if choices else None
            matches={i:match(row,observed) for i,row in enumerate(selected)}
            pending=[i for i in range(len(selected)) if matches[i] is None]
            if pending:
                alternatives=self._lines(page,[selected[i]['bbox'] for i in pending])
                for i in pending:matches[i]=match(selected[i],alternatives)
            changes={}
            for i,choice in matches.items():
                if not choice:continue
                replacement,other=choice;row=selected[i]
                changes[row['text']]=replacement
                audit['corrections'].append({'original':row['text'],'replacement':replacement,
                    'observed':other['text'],'confidence':other['confidence'],'bbox':list(row['bbox'])})
            for old,new in changes.items():text=text.replace(old,new,1)
            lines=[{**r,'text':changes.get(r['text'],r['text'])} for r in lines]
            return text,lines,audit
        except Exception:
            # Optional quality recovery never destroys the primary OCR output.
            self.unavailable=True
            audit.update(status='unavailable',model_identity=None,corrections=[])
            return text,lines,audit


def validate_symbol_review(audit,bounds=None):
    """Check the isolated worker's proof and exact permitted text change."""
    from .ocr_assets import RAPIDOCR_SHA256
    expected={'package':'rapidocr-onnxruntime1.4.4','model_sha256':dict(RAPIDOCR_SHA256)}
    if (not isinstance(audit,dict) or set(audit)!={'policy','status','model_identity','corrections'}
            or audit['policy']!=SYMBOL_POLICY or audit['status'] not in {'checked','unavailable','budget_exhausted'}
            or audit['model_identity']!=(expected if audit['status']=='checked' else None)
            or not isinstance(audit['corrections'],list) or len(audit['corrections'])>4
            or audit['status']!='checked' and audit['corrections']):
        raise ValueError('invalid OCR symbol audit')
    for row in audit['corrections']:
        if (not isinstance(row,dict) or set(row)!={'original','replacement','observed','confidence','bbox'}
                or any(not isinstance(row[k],str) or len(row[k])>512 for k in ['original','replacement','observed'])
                or not _valid_box(row['bbox'])
                or verified_label_replacement(row['original'],row['observed'],row['confidence'])!=row['replacement']
                or bounds and (row['bbox'][0]<bounds[0] or row['bbox'][1]<bounds[1]
                              or row['bbox'][2]>bounds[2] or row['bbox'][3]>bounds[3])):
            raise ValueError('invalid OCR symbol correction')
    return audit
