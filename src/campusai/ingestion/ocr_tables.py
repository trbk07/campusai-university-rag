"""Conservative ruled-table assembly from pixels and recognized word boxes.

No PDF text layer, filename, benchmark annotation or model answer is consulted.
A missing separator may be recovered only from disjoint literal header groups;
body words must fit a single physical row/column. Ambiguity rejects the table.
"""
import re
import unicodedata


OCR_TABLE_POLICY = 'ruled-ocr-cells-v1'


def _fold(value):
    text=unicodedata.normalize('NFD',value.casefold()).replace('đ','d')
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())


def _groups(values, tolerance=6):
    import numpy as np
    groups=[]
    for value in values:
        if groups and value-groups[-1][-1]<=tolerance: groups[-1].append(float(value))
        else: groups.append([float(value)])
    return [float(np.median(group)) for group in groups]


def _joined(words):
    return ' '.join(w['text'].strip() for w in sorted(words,key=lambda w:(w['bbox'][1],w['bbox'][0])))


def _tight_box(gray, bbox):
    """Crop real foreground without resizing a whole cell into a tiny glyph."""
    import cv2
    import numpy as np
    a,b,c,d=[int(v) for v in bbox]
    image=gray[b:d,a:c]
    if min(image.shape,default=0)<3:return None
    ink=cv2.threshold(image,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]
    _,_,parts,_=cv2.connectedComponentsWithStats(ink)
    boxes=[]
    for x,y,w,h,area in parts[1:]:
        if area < 3 or (h > 10*w and h > .7*image.shape[0]) or (w > 10*h and w > .7*image.shape[1]):
            continue
        boxes.append((int(x),int(y),int(x+w),int(y+h)))
    if not boxes:return None
    x0=max(0,min(v[0] for v in boxes)-2);y0=max(0,min(v[1] for v in boxes)-2)
    x1=min(image.shape[1],max(v[2] for v in boxes)+2);y1=min(image.shape[0],max(v[3] for v in boxes)+2)
    return [a+x0,b+y0,a+x1,b+y1]


def assemble_tables(gray, words, recognize_boxes):
    """One bounded pixel-only repair pass; unresolved tables stay unpublished."""
    jobs=[];groups=[]
    for table in ruled_tables(gray,words,include_incomplete=True):
        split_rows=set()
        for split in table['split_words']:
            split_rows.add(split['row'])
            boxes = [_tight_box(gray, part['bbox']) for part in split['parts']]
            if any(box is None for box in boxes):
                continue
            group = []
            for part, box in zip(split['parts'], boxes):
                group.append(len(jobs))
                jobs.append({'bbox': box, 'numeric': part['numeric']})
            groups.append({'remove':split['word'],'jobs':group})
        for cell in table['unresolved_cells']:
            if cell['row'] in split_rows or cell['value']:continue
            a,b,c,d=cell['bbox'];box=_tight_box(gray,[a+3,b+3,c-3,d-3])
            if box is not None:
                groups.append({'remove':None,'jobs':[len(jobs)]});jobs.append({'bbox':box,'numeric':True})
    if len(jobs)>16:return {'words':words,'tables':ruled_tables(gray,words),'repairs':[]}
    output=recognize_boxes([job['bbox'] for job in jobs]) if jobs else []
    if len(output)!=len(jobs):raise ValueError('OCR repair output count mismatch')
    changed=list(words);repairs=[]
    for group in groups:
        if not group['jobs']:continue
        accepted=[]
        for index in group['jobs']:
            text,confidence=output[index];job=jobs[index]
            valid=(isinstance(text,str) and type(confidence) in (int,float) and 0<=confidence<=1
                   and confidence>=(.9 if job['numeric'] else .5) and bool(text.strip())
                   and (not job['numeric'] or re.fullmatch(r'[0-9]{1,3}',text.strip())))
            if not valid:break
            accepted.append({'text':text.strip(),'bbox':job['bbox'],'confidence':confidence})
        else:
            if group['remove'] is not None:
                changed=[word for word in changed if word is not group['remove']]
            changed.extend(accepted);repairs.extend(accepted)
    return {'words':changed,'tables':ruled_tables(gray,changed),'repairs':repairs}


def validate_tables(tables, bounds=None):
    """Validate the isolated worker's bounded, publication-ready table payload."""
    import math
    def box(value):
        return (isinstance(value,list) and len(value)==4
            and all(type(n) in (int,float) and math.isfinite(n) for n in value)
            and value[0]<value[2] and value[1]<value[3]
            and (bounds is None or bounds[0]<=value[0]<=value[2]<=bounds[2]
                 and bounds[1]<=value[1]<=value[3]<=bounds[3]))
    if not isinstance(tables,list) or len(tables)>16:raise ValueError('OCR table count bound')
    for table in tables:
        if not isinstance(table,dict) or table.get('parser')!=OCR_TABLE_POLICY:
            raise ValueError('invalid OCR table parser')
        headers,rows=table.get('headers'),table.get('rows')
        if (not isinstance(headers,list) or not 2<=len(headers)<=32
            or not all(isinstance(v,str) and 0<len(v)<=4096 for v in headers)
            or not isinstance(rows,list) or not 1<=len(rows)<=200
            or any(not isinstance(row,list) or len(row)!=len(headers)
                   or any(not isinstance(v,str) or len(v)>16384 for v in row) for row in rows)
            or table.get('unresolved_cells') or table.get('split_words') or not box(table.get('bbox'))
            or not isinstance(table.get('row_bboxes'),list) or len(table['row_bboxes'])!=len(rows)
            or not isinstance(table.get('header_bboxes'),list) or len(table['header_bboxes'])!=len(headers)
            or any(not box(v) for v in table['row_bboxes']+table['header_bboxes'])):
            raise ValueError('invalid or unresolved OCR table')
    return tables


def ruled_tables(gray, words, *, include_incomplete=False):
    """Return only geometrically supported, explicitly headed course tables."""
    import cv2
    import numpy as np
    if gray.ndim!=2 or gray.size>20_000_000 or len(words)>4096:
        raise ValueError('OCR table input bound')
    height,width=gray.shape
    ink=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,35,15)
    horizontal=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,max(25,width//40)),np.uint8))
    vertical=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((max(40,height//40),1),np.uint8))
    combined=cv2.dilate(horizontal|vertical,np.ones((3,3),np.uint8))
    _count,_labels,components,_centers=cv2.connectedComponentsWithStats(combined)
    tables=[]
    candidates=[tuple(map(int,c)) for c in components[1:] if c[2]>=120 and c[3]>=80 and c[4]>=300]
    # Faded horizontal strokes can disconnect a single ruled grid. A combined
    # candidate still requires closed outer edges, populated explicit headers,
    # unambiguous cells and unique identity/credit columns below. Separate
    # closed tables retain their empty gutter column and cannot pass as one.
    if len(candidates)>1:
        left=min(c[0] for c in candidates);top=min(c[1] for c in candidates)
        right=max(c[0]+c[2] for c in candidates);bottom=max(c[1]+c[3] for c in candidates)
        candidates.append((left,top,right-left,bottom-top,0))
    for x,y,w,h,area in candidates:
        hb=cv2.dilate(horizontal[y:y+h,x:x+w],np.ones((7,1),np.uint8))
        vb=cv2.dilate(vertical[y:y+h,x:x+w],np.ones((1,7),np.uint8))
        xs=[x+value for value in _groups(np.flatnonzero((vb>0).sum(axis=0)>.2*h))]
        ys=[y+value for value in _groups(np.flatnonzero((hb>0).sum(axis=1)>.6*w))]
        if not 4<=len(xs)<=33 or not 4<=len(ys)<=201: continue
        # An open/faded outside edge is not permission to drop the last row.
        if min(xs)-x>10 or x+w-max(xs)>10 or min(ys)-y>10 or y+h-max(ys)>10: continue
        inside=[word for word in words if xs[0]<=(word['bbox'][0]+word['bbox'][2])/2<=xs[-1]
                and ys[0]<=(word['bbox'][1]+word['bbox'][3])/2<=ys[-1]]
        header=[word for word in inside if (word['bbox'][1]+word['bbox'][3])/2<ys[1]]
        inferred=[]
        # A partially ruled name/credit column can still have separate, explicit
        # header text. Use its actual whitespace gutter, never body numbers.
        for lo,hi in list(zip(xs,xs[1:])):
            group=[]
            candidates=[word for word in header if lo<=(word['bbox'][0]+word['bbox'][2])/2<hi
                        and word['bbox'][2]-word['bbox'][0]<hi-lo]
            for word in sorted(candidates,key=lambda a:a['bbox'][0]):
                if group and word['bbox'][0]<=max(a['bbox'][2] for a in group[-1])+2: group[-1].append(word)
                else: group.append([word])
            for left,right in zip(group,group[1:]):
                if (_fold(_joined(right)) not in {'so tin chi','credits'}
                        or not _fold(_joined(left)).startswith(('hoc phan','course name'))): continue
                edge=(max(a['bbox'][2] for a in left)+min(a['bbox'][0] for a in right))/2
                if lo+10<edge<hi-10:
                    xs.append(edge);inferred.append({'edge':edge,'basis':'explicit_header_gutter',
                        'left_label':_joined(left),'right_label':_joined(right)})
        xs=sorted(xs)
        if any(b-a<8 for a,b in zip(xs,xs[1:])): continue
        cells=[[[] for _ in range(len(xs)-1)] for _ in range(len(ys)-1)]
        spans=[];body_spans=[];split_words=[];ambiguous=False
        for word in inside:
            a,b,c,d=word['bbox'];word_area=(c-a)*(d-b)
            if word_area<=0: ambiguous=True;break
            row=max(range(len(ys)-1),key=lambda i:max(0,min(d,ys[i+1])-max(b,ys[i])))
            overlaps=[max(0,min(c,hi)-max(a,lo)) for lo,hi in zip(xs,xs[1:])]
            column=max(range(len(overlaps)),key=overlaps.__getitem__)
            vertical_overlap=max(0,min(d,ys[row+1])-max(b,ys[row]))/(d-b)
            if row==0 and overlaps[column]/(c-a)<.8:
                cols=[i for i,overlap in enumerate(overlaps) if overlap/(c-a)>.1]
                if len(cols)<2:ambiguous=True;break
                spans.append({'columns':cols,'text':word['text'],'bbox':word['bbox']});continue
            if row>0 and overlaps[column]/(c-a)<.8 and vertical_overlap>=.8:
                cols=[i for i,overlap in enumerate(overlaps) if overlap/(c-a)>.1]
                if len(cols)<2:ambiguous=True;break
                if any(abs(xs[i]-edge['edge'])<1 for i in cols[1:] for edge in inferred):
                    parts=[{'bbox':[max(a,xs[i]),b,min(c,xs[i+1]),d],
                            'numeric':i==cols[-1] and _fold(_joined([
                                z for z in header if xs[i]<(z['bbox'][0]+z['bbox'][2])/2<xs[i+1]
                            ])) in {'so tin chi','credits'}} for i in cols]
                    split_words.append({'word':word,'parts':parts,'row':row-1})
                    cells[row][cols[0]].append(word)
                    continue
                top,bottom=int(ys[row])+3,int(ys[row+1])-3
                borders=[vertical[top:bottom,max(0,int(xs[i])-2):int(xs[i])+3] for i in cols[1:]]
                if any(not border.size or np.count_nonzero(border)/border.size>=.1 for border in borders):
                    ambiguous=True;break
                body_spans.append({'row':row-1,'columns':cols,'bbox':word['bbox']})
                cells[row][cols[0]].append(word)
                continue
            if overlaps[column]/(c-a)<.8 or vertical_overlap<.8:
                ambiguous=True;break
            cells[row][column].append(word)
        if ambiguous: continue
        headers=[_joined(cell) for cell in cells[0]]
        for span in sorted(spans,key=lambda span:span['bbox'][1],reverse=True):
            for column in span['columns']:headers[column]=span['text']+' / '+headers[column]
        # Preserve a literal parenthetical qualifier separately from its label.
        notes={}
        for i,label in enumerate(headers):
            if '(' in label and label.endswith(')'):
                headers[i],notes[str(i)]=[part.strip() for part in label.split('(',1)]
                notes[str(i)]='('+notes[str(i)]
        folded=[_fold(label) for label in headers]
        codes=[i for i,label in enumerate(folded) if label in {'ma hoc phan','ma so hoc phan','course code'}]
        credits=[i for i,label in enumerate(folded) if label in {'so tin chi','credits'}]
        if len(codes)!=1 or len(credits)!=1 or not all(headers): continue
        for span in body_spans:
            row=cells[span['row']+1];first=span['columns'][0]
            for column in span['columns'][1:]:row[first].extend(row[column]);row[column]=[]
        rows=[[_joined(cell) for cell in row] for row in cells[1:]]
        course_rows=[i for i,row in enumerate(rows) if re.fullmatch(r'[A-Za-z]{2,5}\s*[0-9]{3,5}',row[codes[0]])]
        unresolved=[{'row':i,'column':credits[0],'value':rows[i][credits[0]],
            'bbox':[xs[credits[0]],ys[i+1],xs[credits[0]+1],ys[i+2]]}
            for i in course_rows if not re.fullmatch(r'[0-9]{1,3}',rows[i][credits[0]])]
        if len(course_rows)<3 or (unresolved or split_words) and not include_incomplete: continue
        bbox=[xs[0],ys[0],xs[-1],ys[-1]]
        if any(min(bbox[2],t['bbox'][2])-max(bbox[0],t['bbox'][0])>0
               and min(bbox[3],t['bbox'][3])-max(bbox[1],t['bbox'][1])>0 for t in tables):continue
        tables.append({'headers':headers,'rows':rows,'bbox':bbox,
            'row_bboxes':[[xs[0],a,xs[-1],b] for a,b in zip(ys[1:],ys[2:])],
            'header_bboxes':[[a,ys[0],b,ys[1]] for a,b in zip(xs,xs[1:])],
            'column_edges':xs,'row_edges':ys,'inferred_columns':inferred,
            'header_spans':spans,'header_notes':notes,'row_spans':body_spans,
            'unresolved_cells':unresolved,'split_words':split_words,'parser':OCR_TABLE_POLICY})
        if len(tables)>=16: break
    return tables
