"""Bounded arithmetic proofs for user premises and literal source conditions.

This never treats a user's reported score as a verified personal record. It
checks an explicitly hypothetical application, retaining all source thresholds,
units and other eligibility conditions. Unknown grammar keeps strict validation.
"""
import re
from decimal import Decimal

from .course_credits import folded

NUMBER=r'\d+(?:[.,]\d+)?'
APPLICATION_NUMBER=re.compile(r'(?<![\w.])(?<!\d,)'+NUMBER+r'(?!\w|[.,]\d)')
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
    explicit={decimal(m[1]) for m in re.finditer(r'\b'+field+r'\s*[:=]?\s*('+NUMBER+r')(?!\w|[.,]\d)',query)}
    if not explicit and topic:
        # Elliptical numeric follow-up, not a new amount or course-credit input.
        if re.search(r'\b(?:tc|tin chi|credits?|ngay|days?|tien|dong|vnd|%)\b',query):return None
        explicit={decimal(m[0]) for m in re.finditer(r'(?<![\w.,])'+NUMBER+r'(?![\w.,])',query)}
    if len(explicit)!=1:return None
    value=next(iter(explicit));thresholds=set()
    for claim in supported:
        text=folded(claim)
        pattern=r'\b'+field+r'\b[^.;!?]{0,180}?(?:dat tu|toi thieu|>=|≥|at least)\s*('+NUMBER+r')(?!\w|[.,]\d)'
        for m in re.finditer(pattern,text):thresholds.add((decimal(m[1]),True))
        pattern=r'\b'+field+r'\b[^.;!?]{0,180}?(?:lon hon|greater than|(?<![>=])>(?!=))\s*('+NUMBER+r')(?!\w|[.,]\d)'
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
        field_prefix=(r'(?:cpa|gpa|diem trung binh(?: chung)? tich luy)\)?'
            r'(?:\s+cua\s+(?:sinh vien|nguoi hoc|ban|em|minh|toi))?\s*(?:(?:la|dat|duoc)\s*)?$')
        # In a GPA-only follow-up, "with a score of X" refers to the same
        # proved input. A different unit or an unrelated amount stays strict.
        elliptical=r'\b(?:voi(?:\s+(?:muc|diem|muc diem))?|diem)$'
        if not (re.search(field_prefix,prefix) or topic and re.search(elliptical,prefix)):
            return m[0]
        if re.match(r'\s*(?:tc\b|t[ií]n\s+ch[iỉ]|credits?|ng[aà]y|days?|đồng|dong\b|vnd\b|usd\b|%)',answer[m.end():],re.I):return m[0]
        return ' '
    return APPLICATION_NUMBER.sub(premise,answer)


def registration_application_view(answer, supported, question, *, evidence=()):
    """Prove a negative registration decision above one unconditional cap.

    This is a hypothetical application of the user's input, not a verified
    student record. A ceiling never proves eligibility for values below it.
    Other conditions, conflicting caps or term ownership remain fail-closed.
    """
    raw,_,topic=str(question or '').partition('\nContext topic (untrusted user input): ')
    query=folded(raw);context=folded(topic)
    action=r'(?:dang k[yi]|register|enrol(?:l)?)'
    unit=r'(?:tc|tin(?: chi)?(?!\s+(?:dung|hieu)\b)|credits?)'
    values={decimal(m[1]) for m in re.finditer(r'\b'+action+r'\s*('+NUMBER+r')\s*'+unit+r'\b',query)}
    if len(values)!=1:return None
    value=next(iter(values))
    phases={
        'regular':r'(?:hoc )?k[yi] chinh|(?:main|regular) semester',
        'auxiliary':r'(?:hoc )?k[yi] phu|auxiliary semester',
        'summer':r'(?:hoc )?k[yi] he|summer semester',
    }
    terms=lambda text:{name for name,pattern in phases.items() if re.search(r'\b(?:'+pattern+r')\b',text)}
    asked=terms(query) or terms(context)
    bounds=set()
    cap=(r'\b'+action+r'\b[^.;!?]{0,80}?\b(?:toi da|khong (?:vuot )?qua|'
         r'at most|no more than|maximum(?: of)?)\s*('+NUMBER+r')\s*'+unit+r'\b')
    for claim in supported:
        text=folded(claim)
        found={decimal(m[1]) for m in re.finditer(cap,text)}
        if not found:continue
        scope=terms(text)
        if asked and not scope:return None  # An unscoped alternative may be an exception.
        if scope!=asked:continue
        # Optional existence of the named term is not a student condition.
        text=re.sub(r'\(neu co\)','',text)
        if re.search(r'\b(?:neu|truong hop|thuoc dien|khong thuoc|provided|unless|if)\b',text):return None
        # Do not infer a student's membership of an arbitrary target group.
        if re.search(r'\bdoi voi\s+(?!(?:hoc )?k[yi]\b)',text):return None
        bounds.update(found)
    if len(bounds)!=1 or value<=next(iter(bounds)):return None
    # The complete visible quotes may veto a proof, never license new facts.
    # A model cannot erase a conflicting limit/exception by omitting its claim.
    for quote in evidence:
        text=re.sub(r'\(neu co\)','',folded(quote))
        found={decimal(m[1]) for m in re.finditer(cap,text)}
        if not found:continue
        scope=terms(text)
        if asked and not scope:return None
        if scope!=asked:continue
        if (found-bounds or re.search(r'\b(?:neu|truong hop|thuoc dien|khong thuoc|provided|unless|if)\b',text)
                or re.search(r'\bdoi voi\s+(?!(?:hoc )?k[yi]\b)',text)):
            return None
    # Mask only this operand inside an explicit permission/refusal clause.
    # Repeating that value as a fee or a different fact still needs a source.
    from .footnotes import _fold_with_offsets
    text,offsets=_fold_with_offsets(answer);spans=set()
    permission=(r'\b(?P<modal>khong (?:duoc phep|duoc|the)|duoc phep|duoc|co the|'
                r'cannot|can|may|not allowed to)\s+'+action+r'\s*(?P<value>'+NUMBER+r')\s*'+unit+r'\b')
    for match in re.finditer(permission,text):
        if decimal(match['value'])!=value:continue
        if not re.search(r'\b(?:khong|cannot|not)\b',match['modal']):return False
        start,end=match.span('value');spans.add((offsets[start],offsets[end-1]+1))
    if not spans:return None
    return APPLICATION_NUMBER.sub(lambda m:' ' if m.span() in spans else m[0],answer)


def score_threshold_application_view(answer, supported, question, *, evidence=()):
    """Prove only a named average-score minimum, not overall eligibility.

    Require a user score with an explicit scale, a matching source field and
    scale, and a question confined to that threshold. Unknown/compound rules
    retain ordinary claim validation instead of licensing an inference.
    """
    raw=str(question or '').partition('\nContext topic (untrusted user input): ')[0]
    query=folded(raw)
    if not re.search(r'\b(?:rieng|chi xet)\s+(?:nguong|yeu cau|dieu kien)\s+diem\b',query):return None
    field=r'\bdiem trung binh\s+(?P<label>[a-z ]{2,65}?)\s+'
    premises=list(re.finditer(field+r'(?:la|=|:)\s*(?P<value>'+NUMBER+r')\s*/\s*(?P<scale>'+NUMBER+r')(?!\w|[.,]\d)',query))
    if len(premises)!=1:return None
    premise=premises[0]
    labels=lambda text:set(text.split())-{'cua','muc','diem','la'}
    asked=labels(premise['label'])
    if not asked:return None
    value,scale=decimal(premise['value']),decimal(premise['scale'])
    if not 0<=value<=scale or scale<=0:return None
    bound=re.compile(field+r'dat tu\s+(?:diem\s+)?(?P<minimum>'+NUMBER+r')\s+tro len\s+(?:theo\s+)?thang diem\s+(?P<scale>'+NUMBER+r')(?!\w|[.,]\d)')
    def bounds(claims):
        found=set()
        for claim in claims:
            text=folded(claim)
            for match in bound.finditer(text):
                named=labels(match['label'])
                if not named or not named<=asked:continue
                # The source must define this score as the passing condition.
                # Do not discard another premise in a compound eligibility rule.
                clause=text[max(0,text.rfind('.',0,match.start())+1):match.start()]
                if not re.search(r'\bduoc danh gia la dat neu\s*$',clause):continue
                suffix=text[match.end():].lstrip()
                if re.match(r'(?:va|hoac|nhung|tru|neu|and|or|unless)\b',suffix):return None
                found.add((decimal(match['minimum']),decimal(match['scale'])))
        return found
    thresholds=bounds(supported)
    if not thresholds or len(thresholds)!=1:return None
    minimum,source_scale=next(iter(thresholds))
    if scale!=source_scale or not 0<=minimum<=scale:return None
    alternatives=bounds(evidence)
    if alternatives is None or alternatives-thresholds:return None
    meets=value>=minimum
    text=folded(answer)
    negative=r'\b(?:chua|khong) dat (?:nguong(?: diem)?|yeu cau)\b'
    positive=r'\b(?:da dat (?:nguong(?: diem)?|yeu cau)|dap ung nguong(?: diem)?)\b'
    verdicts=set()
    if re.search(negative,text):verdicts.add(False)
    if re.search(positive,text):verdicts.add(True)
    if not verdicts:return None
    if verdicts!={meets}:return False
    if re.search(r'\b(?:du (?:moi |tat ca )?dieu kien|duoc bao ve|duoc tot nghiep|tu dong|chac chan)\b',text):return False
    from .footnotes import _fold_with_offsets
    text,offsets=_fold_with_offsets(answer);spans=set()
    repeated=re.compile(r'\bdiem trung binh(?:\s+(?:[a-z]+)){0,9}?\s*(?:la\s*)?(?P<value>'+NUMBER+r')\s*/\s*(?P<scale>'+NUMBER+r')(?!\w|[.,]\d)')
    for match in repeated.finditer(text):
        prefix=text[match.start():match.start('value')]
        named=labels(re.sub(r'^diem trung binh\s*','',prefix).strip())
        if named and not named<=asked:continue
        if decimal(match['value'])!=value or decimal(match['scale'])!=scale:return False
        start,end=match.span('value');spans.add((offsets[start],offsets[end-1]+1))
    if not spans:return None
    return APPLICATION_NUMBER.sub(lambda m:' ' if m.span() in spans else m[0],answer)


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
    roles=set()
    for index,(role,value) in enumerate(role_patterns):
        # An explicitly user-named term may separate the registration verb
        # from its operand. Never infer a different term from answer wording.
        phases=[pattern for pattern in [r'(?:hoc )?k[yi] chinh',r'(?:hoc )?k[yi] phu',
                                         r'(?:hoc )?k[yi] he',r'(?:main|regular) semester',r'summer semester']
                if re.search(r'\b'+pattern+r'\b',query)] if index==0 else []
        named_term=r'(?:\s+(?:'+'|'.join(phases)+r'))?' if phases else ''
        for pattern in [r'\b'+role+named_term+r'\s*('+NUMBER+r')\s*'+unit+r'\b',
                        r'(?<![\w.,])('+NUMBER+r')\s*'+unit+r'\s+(?:da\s+)?'+role+r'\b']:
            for m in re.finditer(pattern,text):
                if decimal(m[1])!=value:return False
                roles.add(index);mark(m)
    product=(r'(?P<p>'+NUMBER+r')\s*%\s*(?:cua|of)\s*(?P<d>'+NUMBER+r')'
             r'(?:\s*'+unit+r')?\s*(?:la|equals?|=)\s*(?P<x>'+NUMBER+r')')
    for m in re.finditer(product,text):
        if (decimal(m['p']),decimal(m['d']),decimal(m['x']))!=(percent,denominator,intermediate):return False
        if re.match(r'\s*%',text[m.end():]):return False
        mark(m)
    ratio_pattern=(r'(?P<n>'+NUMBER+r')\s*/\s*(?P<d>'+NUMBER+r')\s*'
                   r'(?:=|la|chiem|\(\s*(?:khoang|approximately|about))\s*(?P<r>'+NUMBER+r')\s*%')
    proved_ratio=False
    for m in re.finditer(ratio_pattern,text):
        places=len(m['r'].replace(',','.').partition('.')[2])
        if places>2 or (decimal(m['n']),decimal(m['d']))!=(numerator,denominator):return False
        if decimal(m['r'])!=ratio.quantize(Decimal(10)**-places):return False
        proved_ratio=True;mark(m)
    # A separately worded percentage must name the failed-credit ratio and
    # bind both operands elsewhere in this answer. Do not authorize the same
    # number as a fee, credit count, or an unrelated percentage.
    if roles=={0,1} or proved_ratio:
        ratio_description=(r'\b(?:ty le (?:tin chi )?khong dat|so tin chi khong dat|failed credit (?:ratio|percentage))'
            r'\s*(?:la|chiem|is|equals?)?\s*(?:khoang|approximately|about)?\s*(?P<r>'+NUMBER+r')\s*%')
        for m in re.finditer(ratio_description,text):
            places=len(m['r'].replace(',','.').partition('.')[2])
            if places>2 or decimal(m['r'])!=ratio.quantize(Decimal(10)**-places):return False
            mark(m)
    comparison=(r'(?P<n>'+NUMBER+r')\s*(?:vuot qua|lon hon|greater than|>)\s*'
                r'(?P<p>'+NUMBER+r')\s*%\s*(?:cua|of)\s*(?P<d>'+NUMBER+r')')
    for m in re.finditer(comparison,text):
        if not meets or (decimal(m['n']),decimal(m['p']),decimal(m['d']))!=(numerator,percent,denominator):return False
        mark(m)
    if not spans:return None
    return APPLICATION_NUMBER.sub(lambda m:' ' if m.span() in spans else m[0],answer)


def percentage_application_completion(answer, question, evidence, *, language='vi'):
    """Complete an explicit percentage-threshold application from one cited rule.

    The user supplies both operands and the provider must already give a
    consistent yes/no conclusion. This adds only the reproducible arithmetic;
    it cannot establish overall eligibility or select between conflicting
    source rules.
    """
    query=folded(str(question or '').partition('\nContext topic (untrusted user input): ')[0])
    unit=r'(?:tc|tin chi|credits?)'
    total={decimal(m[1]) for m in re.finditer(
        r'\b(?:dang k[yi]|registered|enrolled|(?:hoc )?k[yi] chinh)\s*('+NUMBER+r')\s*'+unit+r'\b',query)}
    failed={decimal(m[1]) for m in re.finditer(
        r'\b(?:khong dat|truot|rot|failed)\s*('+NUMBER+r')\s*'+unit+r'\b',query)}
    if len(total)!=1 or len(failed)!=1:return None
    denominator=next(iter(total));numerator=next(iter(failed))
    if denominator<=0 or not 0<=numerator<=denominator:return None
    quotes=[str(item) for item in evidence if str(item).strip()]
    if not quotes:return None
    owners={folded(quote) for quote in quotes}
    if len(owners)!=1:return None
    bounds=set()
    for quote in quotes:
        text=folded(quote)
        vietnamese_rule=('khong dat' in text and re.search(r'\bdang k[yi]\b',text))
        english_rule=('failed' in text and 'registered' in text)
        if not (re.search(r'\b(?:tin chi|tc|credits?)\b',text)
                and (vietnamese_rule or english_rule)):
            continue
        bounds.update(decimal(m[1]) for m in re.finditer(
            r'\b(?:vuot qua|lon hon|greater than)\s*('+NUMBER+r')\s*%',text))
    if len(bounds)!=1:return None
    threshold=next(iter(bounds))
    if not 0<=threshold<=100 or percentage_application_view(answer,quotes,question) is False:
        return None
    # Required source statements and a matching threshold must be represented
    # in the model's answer before arithmetic is added.
    value=folded(answer)
    if not re.search(r'\b(?:vuot qua|lon hon|greater than|above|exceeds|more than)\s*'
                     +re.escape(str(threshold))+r'\s*%',value):
        return None
    applies=numerator*100>threshold*denominator
    conclusion=_decision(answer)
    if conclusion is None or conclusion!=applies:return None
    ratio=(numerator*100/denominator).quantize(Decimal('0.01'))
    def fmt(number):
        raw=format(number,'f').rstrip('0').rstrip('.') if '.' in format(number,'f') else format(number,'f')
        return raw if str(language).casefold().startswith('en') else raw.replace('.',',')
    total_text=fmt(denominator);failed_text=fmt(numerator);ratio_text=fmt(ratio);threshold_text=fmt(threshold)
    if not str(language).casefold().startswith('en'):
        relation='lớn hơn' if applies else 'không lớn hơn'
        outcome='vượt' if applies else 'không vượt'
        result=('Đối chiếu riêng tiêu chí này: '+failed_text+'/'+total_text+' ≈ '+ratio_text+
                '%, '+relation+' ngưỡng '+threshold_text+'%; vì vậy số tín chỉ không đạt '+
                outcome+' ngưỡng của tiêu chí này.')
    else:
        result=('For this criterion, '+failed_text+'/'+total_text+' is approximately '+ratio_text+
                '%, which is '+('above' if applies else 'not above')+' the '+threshold_text+'% threshold.')
    return result


def credit_share_application_view(answer, supported, question):
    """Verify an explicit part/whole credit calculation against one upper cap.

    Only typed occurrences belonging to the user's operands or the computed
    maximum are masked. A matching number elsewhere is still untrusted. This
    establishes a comparison, never permission or full student eligibility.
    """
    query=folded(str(question or '').partition('\nContext topic (untrusted user input): ')[0])
    unit=r'(?:tin chi|tc|credits?)'
    cross_school=r'\b(?:truong (?:khac|doi tac)|(?:other|another|partner) (?:school|university|institution)|transfer(?:ring)?)\b'
    if not re.search(cross_school,query):return None
    total_pattern=(r'\b(?:chuong trinh(?: (?:dao tao|hoc))?(?: (?:co|gom))?|'
                   r'(?:program(?:me)?|curriculum)(?: (?:has|of|with))?)\s*('+NUMBER+r')\s*'+unit+r'\b')
    part_pattern=r'\b(?:tich luy|transfer(?:ring)?)\s*('+NUMBER+r')\s*'+unit+r'\b'
    totals={decimal(m[1]) for m in re.finditer(total_pattern,query)}
    parts={decimal(m[1]) for m in re.finditer(part_pattern,query)}
    if len(totals)!=1 or len(parts)!=1:return None
    total=next(iter(totals));part=next(iter(parts))
    if total<=0 or not 0<=part<=total:return None
    bounds=set()
    for claim in supported:
        rule=folded(claim)
        if not (re.search(r'\b'+unit+r'\b',rule)
                and re.search(r'\b(?:tong khoi luong|total|program(?:me)?|chuong trinh)\b',rule)
                and re.search(r'\b(?:tich luy|transfer)\b',rule)
                and re.search(cross_school,rule)):
            continue
        bounds.update(decimal(m[1]) for m in re.finditer(
            r'\b(?:khong (?:duoc )?(?:vuot qua|qua)|toi da|at most|no more than)\s*('+NUMBER+r')\s*%',rule))
    if len(bounds)!=1:return None
    percent=next(iter(bounds))
    if not 0<=percent<=100:return None
    maximum=total*percent/100
    from .footnotes import _fold_with_offsets
    text,offsets=_fold_with_offsets(answer)
    negative=r'\b(?:(?:khong|chua) vuot(?: qua)? (?:gioi han|muc|nguong)|does not exceed (?:the )?(?:limit|cap))\b'
    positive=r'\b(?:vuot(?: qua)? (?:gioi han|muc|nguong)|exceeds? (?:the )?(?:limit|cap))\b'
    no_excess=bool(re.search(negative,text))
    has_excess=bool(re.search(positive,re.sub(negative,' ',text)))
    if no_excess and has_excess:return False
    if no_excess:exceeds=False
    elif has_excess:exceeds=True
    else:return None
    if exceeds!=(part>maximum):return False
    if re.search(r'\b(?:chac chan|tu dong|du moi dieu kien|duoc phep|automatically|guaranteed|fully eligible)\b',text):
        return False
    spans=set()
    roles=set()
    for role,pattern,expected in [('total',total_pattern,total),('part',part_pattern,part),
        ('maximum',r'\b(?:gioi han(?: toi da)?|toi da|maximum|cap)\s*(?:(?:la|tuong ung|is|of)\s*)?('+NUMBER+r')\s*'+unit+r'\b',maximum)]:
        for match in re.finditer(pattern,text):
            if decimal(match[1])!=expected:return False
            start,end=match.span(1)
            spans.add((offsets[start],offsets[end-1]+1));roles.add(role)
    # Both operands must be visible and correctly labelled. Do not validate
    # a bare result just because a question happens to contain two numbers.
    if not {'total','part'}<=roles:return None
    return APPLICATION_NUMBER.sub(lambda m:' ' if m.span() in spans else m[0],answer)


def user_application_view(answer, supported, question, *, evidence=()):
    """Use identical typed premise proofs at presentation and owner checks."""
    visible=answer
    for proof in (gpa_application_view,percentage_application_view,registration_application_view,
                  score_threshold_application_view,
                  credit_share_application_view):
        applied=(proof(visible,supported,question,evidence=evidence)
                 if proof in (registration_application_view,score_threshold_application_view)
                 else proof(visible,supported,question))
        if applied is False:return False
        if isinstance(applied,str):visible=applied
    return visible


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
