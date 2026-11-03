"""Bounded arithmetic proofs for user premises and literal source conditions.

This never treats a user's reported score as a verified personal record. It
checks an explicitly hypothetical application, retaining all source thresholds,
units and other eligibility conditions. Unknown grammar keeps strict validation.
"""
import re
from decimal import Decimal

from .course_credits import folded

NUMBER=r'\d+(?:[.,]\d+)?'
APPLICATION_NUMBER=re.compile(r'(?<![\w.])(?<!\d,)'+NUMBER+r'(?![\w,]|\.\d)')
def decimal(value):return Decimal(value.replace(',','.'))


def _spaced_application(text):
    return re.sub(r'\b(CPA|GPA|của|of|là|equals?)(?=\d)',r'\1 ',text,flags=re.I)


def _decision(text):
    value=folded(text)
    if re.search(r'\b(?:chua dat|khong dat (?:nguong|chuan|dieu kien|yeu cau)|chua du|khong du|khong thuoc|khong vuot|not eligible|does not meet|below the minimum)\b',value):return False
    if re.match(r'^\s*(?:khong|no)\b',value):return False
    if re.match(r'^\s*(?:co|yes)\b',value) or re.search(r'\b(?:dat nguong|dap ung (?:nguong|dieu kien)|thuoc dieu kien canh bao)\b',value):return True
    return None


def gpa_application_view(answer, supported, question):
    """Mask only a correctly applied, explicitly user-supplied GPA premise."""
    raw,_,topic=str(question or '').partition('\nContext topic (untrusted user input): ')
    query=folded(raw);context=folded(topic)
    field=r'(?:cpa|gpa|diem trung binh(?: chung)? tich luy)'
    if not re.search(r'\b'+field+r'(?=\b|\d)',query+' '+context):return None
    explicit={decimal(m[1]) for m in re.finditer(r'\b'+field+r'\s*[:=]?\s*('+NUMBER+r')(?![\w,]|\.\d)',query)}
    if not explicit and topic:
        # Elliptical numeric follow-up, not a new amount or course-credit input.
        if re.search(r'\b(?:tc|tin chi|credits?|ngay|days?|tien|dong|vnd|%)\b',query):return None
        explicit={decimal(m[0]) for m in re.finditer(r'(?<![\w.,])'+NUMBER+r'(?![\w.,])',query)}
    if len(explicit)!=1:return None
    value=next(iter(explicit));thresholds=set()
    for claim in supported:
        text=folded(claim)
        pattern=r'\b'+field+r'\b[^.;!?]{0,180}?(?:dat tu|toi thieu|>=|≥|at least)\s*('+NUMBER+r')(?![\w,]|\.\d)'
        for m in re.finditer(pattern,text):thresholds.add((decimal(m[1]),True))
        pattern=r'\b'+field+r'\b[^.;!?]{0,180}?(?:lon hon|greater than|(?<![>=])>(?!=))\s*('+NUMBER+r')(?![\w,]|\.\d)'
        for m in re.finditer(pattern,text):thresholds.add((decimal(m[1]),False))
    if len(thresholds)!=1:return None
    threshold,inclusive=next(iter(thresholds));meets=value>=threshold if inclusive else value>threshold
    decision=_decision(answer)
    if meets and decision is False and not re.search(r'\b(?:chua dat nguong|khong dat nguong|does not meet the minimum)\b',folded(answer)):
        # Meeting a necessary GPA condition need not establish full eligibility.
        # A correct "not enough to conclude" must not be read as below-minimum.
        return None
    if decision is not None and decision!=meets:return False
    if decision is None:return None
    # A minimum is necessary, not sufficient for complete thesis eligibility.
    if meets and re.search(r'\b(?:chac chan|tu dong|duoc lam ngay|automatically|guaranteed)\b',folded(answer)):
        return False
    answer=_spaced_application(answer)
    def premise(m):
        if decimal(m[0])!=value:return m[0]
        prefix=folded(answer[max(0,m.start()-100):m.start()])
        if not re.search(r'(?:cpa|gpa|diem trung binh(?: chung)? tich luy)\)?\s*(?:(?:la|dat|duoc)\s*)?$',prefix):
            return m[0]
        if re.match(r'\s*(?:tc\b|tín\s+chỉ|credits?|ngày|days?|%)',answer[m.end():],re.I):return m[0]
        return ' '
    return APPLICATION_NUMBER.sub(premise,answer)


def percentage_application_view(answer, supported, question):
    """Prove failed/registered credit percentage against one printed bound."""
    query=folded(str(question or '').partition('\nContext topic (untrusted user input): ')[0])
    unit=r'(?:tc|tin chi|credits?)'
    total={decimal(m[1]) for m in re.finditer(r'\b(?:dang k[yi]|registered|enrolled|(?:hoc )?k[yi] chinh)\s*('+NUMBER+r')\s*'+unit+r'\b',query)}
    failed={decimal(m[1]) for m in re.finditer(r'\b(?:khong dat|truot|rot|failed)\s*('+NUMBER+r')\s*'+unit+r'\b',query)}
    if len(total)!=1 or len(failed)!=1:return None
    denominator=next(iter(total));numerator=next(iter(failed))
    if denominator<=0 or not 0<=numerator<=denominator:return None
    bounds=set()
    for claim in supported:
        text=folded(claim)
        if not (re.search(r'\b(?:tin chi|tc|credits?)\b',text) and 'khong dat' in text
                and re.search(r'\b(?:dang k[yi]|registered)\b',text)):continue
        for m in re.finditer(r'\b(?:vuot qua|lon hon|greater than)\s*('+NUMBER+r')\s*%',text):bounds.add(decimal(m[1]))
    if len(bounds)!=1:return None
    percent=next(iter(bounds))
    if not 0<=percent<=100:return None
    meets=numerator*100>percent*denominator
    decision=_decision(answer)
    if decision is not None and decision!=meets:return False
    if decision is None:return None
    intermediate=percent*denominator/100;ratio=numerator/denominator*100
    answer=_spaced_application(answer)
    from .footnotes import _fold_with_offsets
    text,offsets=_fold_with_offsets(answer)
    spans=set()
    def mark(match):
        # Whitelist numeric occurrences in this proved expression, never the
        # same numeric value used in an unrelated fee/cap/course/percentage.
        for number in re.finditer(NUMBER,match[0]):
            start=match.start()+number.start();end=match.start()+number.end()
            if decimal(number[0])!=percent:spans.add((offsets[start],offsets[end-1]+1))
    role_patterns=[(r'(?:dang k[yi]|registered|enrolled)',denominator),
                   (r'(?:khong dat|truot|rot|failed)',numerator)]
    for role,value in role_patterns:
        for m in re.finditer(r'\b'+role+r'\s*('+NUMBER+r')\s*'+unit+r'\b',text):
            if decimal(m[1])!=value:return False
            mark(m)
    product=(r'(?P<p>'+NUMBER+r')\s*%\s*(?:cua|of)\s*(?P<d>'+NUMBER+r')'
             r'(?:\s*'+unit+r')?\s*(?:la|equals?|=)\s*(?P<x>'+NUMBER+r')')
    for m in re.finditer(product,text):
        if (decimal(m['p']),decimal(m['d']),decimal(m['x']))!=(percent,denominator,intermediate):return False
        if re.match(r'\s*%',text[m.end():]):return False
        mark(m)
    ratio_pattern=(r'(?P<n>'+NUMBER+r')\s*/\s*(?P<d>'+NUMBER+r')\s*'
                   r'(?:=|la|chiem)\s*(?P<r>'+NUMBER+r')\s*%')
    for m in re.finditer(ratio_pattern,text):
        places=len(m['r'].replace(',','.').partition('.')[2])
        if places>2 or (decimal(m['n']),decimal(m['d']))!=(numerator,denominator):return False
        if decimal(m['r'])!=ratio.quantize(Decimal(10)**-places):return False
        mark(m)
    comparison=(r'(?P<n>'+NUMBER+r')\s*(?:vuot qua|lon hon|greater than|>)\s*'
                r'(?P<p>'+NUMBER+r')\s*%\s*(?:cua|of)\s*(?P<d>'+NUMBER+r')')
    for m in re.finditer(comparison,text):
        if not meets or (decimal(m['n']),decimal(m['p']),decimal(m['d']))!=(numerator,percent,denominator):return False
        mark(m)
    if not spans:return None
    return APPLICATION_NUMBER.sub(lambda m:' ' if m.span() in spans else m[0],answer)


def elective_application_conflict(answer, quotes, question):
    query=folded(str(question or '').partition('\nContext topic (untrusted user input): ')[0])
    query=re.sub(r'\b(tinh du|du)(?=\d)',r'\1 ',query)
    if not re.search(r'\b(?:chon ca|ca hai|both|all of)\b',query):return False
    if not re.search(r'\b(?:tinh du|du|bat buoc|required|count)\b',query):return False
    groups=set();bound_groups=set()
    from .course_credits import COURSE_CODE,course_code_key
    code_pattern=re.compile(r'(?<!\w)'+COURSE_CODE+r'(?!\w)',re.I)
    codes={course_code_key(m[0]) for m in code_pattern.finditer(query)}
    for quote in quotes:
        text=folded(quote)
        markers=list(re.finditer(r'\b(?:chon|choose|select)\s*(\d+)\s*/\s*(\d+)\s*(?:tin chi|tc|credits?)',text))
        for i,m in enumerate(markers):
            pair=tuple(map(int,m.groups()));groups.add(pair)
            segment=text[m.end():markers[i+1].start() if i+1<len(markers) else len(text)]
            if codes and codes<={course_code_key(c[0]) for c in code_pattern.finditer(segment)}:bound_groups.add(pair)
    if bound_groups:groups=bound_groups
    requested={tuple(map(int,m.groups())) for m in re.finditer(
        r'\b(?:chon|choose|select)\s*(\d+)\s*/\s*(\d+)\s*(?:tin chi|tc|credits?)',query)}
    if len(requested)==1:groups &= requested
    if len(groups)!=1:return False
    required,offered=next(iter(groups))
    if not 0<required<offered:return False
    # Choosing N from M establishes the required subtotal N. It does not
    # independently authorize counting all M as that requirement.
    return bool(_decision(answer) is True and re.search(r'\b(?:chon ca|ca hai|both|all)\b',folded(answer)))
