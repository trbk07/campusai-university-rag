"""Local OCR accuracy against known rasterized text; no AI judge or provider."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import unicodedata

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

from campusai.ingestion.ocr import ocr_pdf


PARAGRAPHS = [
    'TÀI LIỆU KIỂM THỬ OCR - DỮ LIỆU GIẢ LẬP',
    'Sinh viên đăng ký học phần theo kế hoạch của học kỳ.',
    'Điểm trung bình tích lũy được tính theo số tín chỉ.',
    'Người học phải hoàn thành các học phần bắt buộc.',
    'Học bổng được xét từ kết quả học tập và rèn luyện.',
    'Thời hạn nộp hồ sơ là ngày 25 tháng 10 năm 2026.',
    'Học phần INT2207 có 3 tín chỉ và mã lớp là ABC123.',
    'Không suy đoán thông tin không xuất hiện trong nguồn.',
]
ENGLISH = [
    'FICTIONAL OCR TEST SOURCE - NOT AN ACADEMIC POLICY',
    'Students submit the registration form before the deadline.',
    'The final grade includes attendance and examination scores.',
    'Course CS204 requires completion of the prerequisite module.',
    'The laboratory begins at 09:30 on 25 October 2026.',
    'A minimum of 120 credits is required in this fictional example.',
]


def normalized(value):
    return ' '.join(unicodedata.normalize('NFC',value).split())


def edits(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=row
    return previous[-1]


def fixture(root,font_path):
    """Gold is the exact string drawn into pixels; PDF has no text layer."""
    font=ImageFont.truetype(str(font_path),32)
    small=ImageFont.truetype(str(font_path),28)
    pages=[]
    for category,lines in [('vietnamese',PARAGRAPHS),('english',ENGLISH),('bilingual',PARAGRAPHS[:4]+ENGLISH[1:4])]:
        image=Image.new('RGB',(1900,1300),'white');draw=ImageDraw.Draw(image)
        for i,line in enumerate(lines):draw.text((80,65+i*85),line,font=font,fill='black')
        pages.append((category,image,'\n'.join(lines)))
    image=Image.new('RGB',(1900,1300),'white');draw=ImageDraw.Draw(image)
    left=['CỘT TRÁI - ĐĂNG KÝ HỌC PHẦN']+PARAGRAPHS[1:5]
    right=['CỘT PHẢI - HỒ SƠ NHẬP HỌC',
           'Người học chuẩn bị bản sao văn bằng.',
           'Hồ sơ cần có giấy xác nhận kết quả.',
           'Thời gian tiếp nhận là từ 08:00 đến 17:00.',
           'Thông tin thiếu phải được bổ sung đầy đủ.']
    for x,lines in [(65,left),(1030,right)]:
        for i,line in enumerate(lines):draw.text((x,80+i*90),line,font=small,fill='black')
    pages.append(('two_columns',image,'\n'.join(left+right)))
    image=Image.new('RGB',(1900,1300),'white');draw=ImageDraw.Draw(image)
    rows=[['Mã học phần','Tên học phần','Số tín chỉ'],
          ['INT2207','Cơ sở dữ liệu','3'],['MAT1093','Đại số tuyến tính','4'],
          ['PHY1100','Vật lý đại cương','3'],['ENG1001','Tiếng Anh cơ bản','2']]
    for i,row in enumerate(rows):
        for x,text in zip((80,600,1450),row):draw.text((x,80+i*100),text,font=font,fill='black')
        draw.line((60,60+i*100,1800,60+i*100),fill='black',width=2)
    draw.line((60,560,1800,560),fill='black',width=2)
    for x in (60,560,1400,1800):draw.line((x,60,x,560),fill='black',width=2)
    pages.append(('ruled_table',image,'\n'.join(' '.join(row) for row in rows)))
    rotated=pages[0][1].rotate(.7,resample=Image.Resampling.BICUBIC,fillcolor='white')
    pages.append(('small_scan_rotation',rotated,pages[0][2]))
    path=root/'known-raster-fixture.pdf'
    with fitz.open() as pdf:
        for _category,image,_gold in pages:
            stream=BytesIO();image.save(stream,format='PNG')
            page=pdf.new_page(width=760,height=520)
            page.insert_image(page.rect,stream=stream.getvalue())
        pdf.save(path)
    pages[0][1].save(root/'vietnamese-preview.png')
    pages[3][1].save(root/'columns-preview.png')
    pages[4][1].save(root/'table-preview.png')
    return path,[{'page':i,'category':kind,'gold':gold} for i,(kind,_image,gold) in enumerate(pages,1)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--font',type=Path,default=Path('C:/Windows/Fonts/arial.ttf'))
    parser.add_argument('--data-dir',type=Path,default=Path('.cache/ocr/tessdata_fast'))
    parser.add_argument('--compare-rapidocr',action='store_true')
    args=parser.parse_args();args.root.mkdir(parents=True,exist_ok=False)
    path,gold=fixture(args.root,args.font)
    report={'scope':'Known synthetic raster text accuracy, not independent real-scan accuracy or full-app acceptance',
            'source_sha256':sha256(path.read_bytes()).hexdigest(),'font_sha256':sha256(args.font.read_bytes()).hexdigest(),
            'documents_transmitted':0,'gold':gold,'results':{}}
    for backend in (['rapidocr','tesseract'] if args.compare_rapidocr else ['tesseract']):
        result=ocr_pdf(path,max_pages=6,timeout_seconds=120,backend=backend,data_dir=args.data_dir,scale=2.5)
        rows=[]
        for reference,actual in zip(gold,result.pages):
            expected,text=normalized(reference['gold']),normalized(str(actual['text']))
            distance=edits(expected,text)
            rows.append({'page':reference['page'],'category':reference['category'],'text':actual['text'],
                'edits':distance,'gold_characters':len(expected),'character_accuracy':1-distance/len(expected),
                'numeric_tokens_equal':re.findall(r'\d+',expected)==re.findall(r'\d+',text)})
        accuracy=1-sum(row['edits'] for row in rows)/sum(row['gold_characters'] for row in rows)
        report['results'][backend]={'engine':result.engine,'seconds':result.elapsed_seconds,
            'model_identity':result.model_identity,'rows':rows,'character_accuracy':accuracy,
            'threshold':.90,'status':'PASS' if accuracy>=.90 else 'FAIL'}
    (args.root/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({name:{k:v for k,v in result.items() if k!='rows'} for name,result in report['results'].items()}))


if __name__=='__main__':main()
