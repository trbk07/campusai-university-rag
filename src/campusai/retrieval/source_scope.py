"""Require source support for explicitly requested academic subjects."""
from __future__ import annotations

import re
import unicodedata

from .routing import detected_course_codes
from .tokenizer_vi import source_body


def _fold(text: str) -> str:
    value = unicodedata.normalize('NFKD', text.casefold().replace('đ', 'd'))
    return ' '.join(value.encode('ascii', 'ignore').decode('ascii').split())


def unsupported_source_reason(query: str, records: dict[str, dict]) -> str | None:
    """Reject absent subjects using the actual selected and filtered sources.

    A positive subject match only permits normal retrieval; it never certifies
    that the retrieved evidence answers a question. Candidate generation uses
    the same scope check. No benchmark labels or source identities are used.
    """
    raw = query.split('\nContext topic (untrusted user input): ', 1)[0]
    question = _fold(raw)
    bodies = [_fold(source_body(item)) for item in records.values()]
    personal_grade = re.search(r'\b(?:gpa|diem thi|diem (?:trung binh|tich luy)|exam score|grades?)\b', question)
    personal_owner = re.search(r'\b(?:cua (?:minh|em|toi|t)|my|of mine)\b', question)
    if personal_grade and personal_owner:
        # Institutional rules cannot reveal a student's current grades.
        # A source must actually be a grade report/transcript, rather than a
        # curriculum containing course credit numbers.
        transcript = any(
            item.get('metadata', {}).get('document_type') in {'academic_transcript', 'grade_report', 'student_results'}
            or re.match(r'(?:bang diem|academic transcript|grade report|student results)\b', body)
            for item, body in zip(records.values(), bodies))
        if not transcript:
            return 'personal_grade_record_not_in_selected_sources'
    codes = detected_course_codes(raw)
    for code in codes:
        pattern = re.compile(r'(?<!\w)' + r'\s*'.join(map(re.escape, code)) + r'(?!\w)', re.I)
        if not any(pattern.search(source_body(item)) for item in records.values()):
            return 'course_code_not_in_selected_sources'
    exam_schedule = re.search(
        r'\b(?:exam(?:ination)?\s+(?:date|time|schedule)|'
        r'(?:ngay(?:\s+va\s+gio)?|gio|lich)\s+(?:thi|kiem tra)|bao gio thi)\b', question)
    if exam_schedule:
        # Credits, assessment weights and a document's issue date do not
        # establish an exam appointment. Require a calendar/clock value in
        # a source passage about an exam. This only admits retrieval; normal
        # evidence/answer checks must still verify the requested course/time.
        months = r'(?:january|february|march|april|may|june|july|august|september|october|november|december)'
        day, month = r'(?:0?[1-9]|[12]\d|3[01])', r'(?:0?[1-9]|1[0-2])'
        calendar = (rf'\b(?:{day}[/-]{month}(?:[/-]\d{{2,4}})?|'
                    rf'\d{{4}}-{month}-{day}|(?:[01]?\d|2[0-3])[:h][0-5]\d|'
                    r'(?:ngay|day)\s+\d{1,2}|thang\s+\d{1,2}|'
                    r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|'
                    rf'{months}\s+{day}(?:st|nd|rd|th)?|{day}\s+{months}|(?:in|during)\s+{months})\b')
        # Accent folding maps "máy" to English "May", and "thị giác" /
        # "thí điểm" to a token that resembles an exam. Those source phrases
        # cannot supply calendar support for an appointment.
        exam_marker = r'\b(?:exams?|examinations?|thi(?!\s+(?:diem|giac|truong|cong|dua)\b)|kiem tra)\b'
        supported = any(
            re.search(calendar, passage[max(0, match.start()-160):match.end()+160])
            for body in bodies for passage in re.split(r'[!?;]|\.(?!\d)', body)
            for match in re.finditer(exam_marker, passage))
        if not supported:
            return 'exam_schedule_not_in_selected_sources'
    subjects = (
        (r'\b(?:scholarships?|hoc bong|hb|kkht|ho tro hoc tap)\b',
         r'\b(?:scholarships?|hoc bong|ho tro hoc tap)\b'),
        (r'\b(?:academic warning|canh bao hoc vu|cbhv)\b',
         r'\b(?:academic warning|canh bao hoc vu)\b'),
        (r'\b(?:gpa|diem (?:trung binh|tich luy)|grade point average)\b',
         r'\b(?:gpa|diem (?:trung binh|tich luy)|grade point average)\b'),
        (r'\b(?:hoc cai thien|grade replacement|replace.*grade)\b',
         r'\b(?:hoc cai thien|grade replacement|replace.*grade)\b'),
    )
    for requested, supported in subjects:
        mentions = [match for match in re.finditer(requested, question)
                    if not re.search(r'(?:khong phai|not|rather than)\s*$', question[:match.start()])]
        if mentions and not any(re.search(supported, body) for body in bodies):
            return 'academic_subject_not_in_selected_sources'
    grade = r'\b(?:gpa|diem (?:trung binh|tich luy)|grade point average)\b'
    graduation = r'\b(?:tot nghiep|graduat(?:ion|e|ing))\b'
    registration = r'\b(?:dang k[yi]|register|registration|enrol(?:l)?(?:ment)?)\b'
    credit_field = r'\b(?:credits?|tin(?: chi)?|tc)\b'
    # An admission/award GPA and a curriculum credit total cannot support
    # rules about graduation grades or grade-dependent course registration.
    # Require the requested relationship in a local source passage, rather
    # than separate keyword hits in unrelated chunks of the selected corpus.
    relationships = (
        ((grade, graduation), 'graduation_grade_rule_not_in_selected_sources'),
        ((grade, registration, credit_field), 'grade_registration_rule_not_in_selected_sources'),
    )
    for fields, reason in relationships:
        if all(re.search(field, question) for field in fields):
            if not any(
                all(re.search(field, passage[max(0, match.start()-160):match.end()+160])
                    for field in fields)
                for body in bodies
                for passage in re.split(r'[!?;]|\.(?!\d)', body)
                for match in re.finditer(fields[0], passage)
            ):
                return reason
    semester = re.search(r'\b(?:semester|hoc ky|ky|ki)\b', question)
    bound = re.search(r'\b(?:minimum|maximum|at least|at most|toi thieu|toi da|it nhat|nhieu nhat)\b', question)
    credits = re.search(r'\b(?:credits?|tin(?: chi)?|tc)\b', question)
    if semester and bound and credits:
        # A curriculum's "Credits per semester" totals do not establish a
        # registration floor or ceiling. Require explicit constraint wording
        # near both the semester and credit fields in a source paragraph.
        supported = False
        for body in bodies:
            for match in re.finditer(r'\b(?:minimum|maximum|at least|at most|toi thieu|toi da|it nhat|nhieu nhat)\b', body):
                window = body[max(0, match.start()-160):match.end()+160]
                if (re.search(r'\b(?:semester|hoc ky|ky|ki)\b', window)
                        and re.search(r'\b(?:credits?|tin chi)\b', window)):
                    supported = True
                    break
        if not supported:
            return 'semester_credit_constraint_not_in_selected_sources'
    return None
