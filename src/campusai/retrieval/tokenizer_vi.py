"""Small bilingual tokenizer with tolerant Unicode normalization."""

from __future__ import annotations

import re
import json
import unicodedata

_WORD = re.compile(r"[\w\u00c0-\u024f]+", re.UNICODE)


def repair_mojibake(text: str) -> str:
    """Repair common UTF-8 decoded as CP1252/Latin-1 corruption."""
    value = str(text)
    markers = ("\u00c3", "\u00c2", "\u00c6", "\u00c4", "\u00e1\u00bb", "\u00e2")
    if not any(marker in value for marker in markers):
        return value
    before = sum(value.count(marker) for marker in markers)
    for encoding in ("cp1252", "latin1"):
        try:
            repaired = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if sum(repaired.count(marker) for marker in markers) < before:
            return repaired
    return value


def tokenize(text: str, language: str | None = None) -> list[str]:
    """Tokenize Vietnamese/English text without mandatory segmentation."""
    value = repair_mojibake(text).casefold()
    if language == "vi":
        try:
            from underthesea import word_tokenize
            value = word_tokenize(value, format="text")
        except ImportError:
            pass
    return _WORD.findall(value)


def normalized_tokens(text: str, language: str | None = None) -> list[str]:
    """Return original tokens plus accent-folded forms for tolerant matching."""
    tokens = tokenize(text, language)
    folded = [
        unicodedata.normalize("NFKD", token.replace('đ','d')).encode("ascii", "ignore").decode("ascii")
        for token in tokens
    ]
    return tokens + [token for token in folded if token and token not in tokens]


def normalize_retrieval_query(text: str) -> str:
    """Normalize common bilingual academic query variants.

    The original query is still retained by the caller for provenance and
    page constraints; this expanded form is used only for candidate recall.
    """
    original = repair_mojibake(str(text)).strip()
    value = re.sub(r"[_/\\-]+", " ", original)
    aliases = []
    lowered = value.casefold()
    folded = unicodedata.normalize('NFKD', lowered.replace('đ', 'd')).encode('ascii', 'ignore').decode('ascii')
    # Expand ordinary academic shorthand and bilingual field names in both
    # directions. These describe query intent; no source IDs or answers are
    # supplied by the expansion.
    academic_aliases = (
        (r'\b(?:ths|master(?:s)?|thac\s+s[yi])\b', 'thạc sĩ master'),
        (r'\b(?:pv|interview|phong van)\b', 'phỏng vấn interview'),
        (r'\b(?:tc|tin chi|credits?)\b|\b(?:may|bao nhieu|bn|\d{1,2})\s*tin\b', 'tín chỉ credits TC'),
        (r'\b(?:gpa|cpa)\b', 'điểm trung bình chung tích lũy GPA CPA'),
        (r'\b(?:bao lau|how long|duration)\b', 'thời gian duration'),
        (r'\b(?:truot|rot|failed)\b', 'không đạt học phần'),
        (r'\b(?:thi lai|thi nua|resit|re[- ]?exam)\b', 'thi lại kỳ thi phụ kỳ thi chính'),
        (r'\b(?:hp|hoc phi|tuition)\b', 'học phí tuition'),
        (r'\b(?:nn|ngoai ngu|english|language)\b', 'ngoại ngữ tiếng Anh language'),
        (r'\b(?:xtt|xet tuyen thang|direct admission)\b', 'xét tuyển thẳng direct admission'),
        (r'\b(?:online|truc tuyen)\b', 'trực tuyến online'),
        (r'\b(?:registration|dang ky)\b', 'đăng ký registration'),
        (r'\b(?:dang ki|dk)\b', 'đăng ký registration'),
        (r'\b(?:lp|le phi|phi du tuyen|fee)\b', 'lệ phí fee'),
        (r'\b(?:when|ngay nao|ngay may|bao gio)\b', 'thời gian ngày'),
        (r'\b(?:deadline|han chot|het han|dong|closure)\b', 'hạn cuối thời gian đăng ký deadline'),
        (r'\b(?:prerequisite|hoc truoc|tien quyet)\b', 'tiên quyết prerequisite'),
    )
    for pattern, expansion in academic_aliases:
        if re.search(pattern, folded):
            aliases.append(expansion)
    if (re.search(r'\b(?:tin(?: chi)?|tc|credits?)\b',folded)
            and re.search(r'\b(?:toi da|toi thieu|gioi han|limit|dang k[yi]|registration)\b',folded)):
        aliases.append('đăng ký học tập số lượng TC khối lượng học tập')
    if re.search(r'\b(?:quy doi|diem chu|letter grade)\b',folded) or re.search(r'\b[ABCDF][+]?\s+hay\s+[ABCDF][+]?(?!\w)',original):
        aliases.append('điểm chữ quy đổi điểm học phần')
    if re.search(r"thac\s+s[yi]|thạc\s+s[ĩỹ]", lowered):
        aliases.extend(("thạc sĩ", "thac si", "master"))
    if re.search(r'(?:dao\s*tao|training).*?(?:may\s*nam|bn\s*nam|bao\s*lau|duration|years?)|training duration|\bduration\b', folded):
        aliases.extend(("thời gian đào tạo", "training duration"))
    if re.search(r'\b(?:entry|dau vao)\b', folded) and re.search(r'\b(?:english|language|nn|ngoai ngu)\b', folded):
        aliases.append('năng lực ngoại ngữ bậc điều kiện đầu vào')
    if re.search(r'\b(?:web|website|url)\b', folded) and re.search(r'\b(?:registration|dang k[yi]|dk)\b', folded):
        aliases.append('cổng thông tin địa chỉ đăng ký trực tuyến')
    if re.search(r'\b(?:scopus+s?|isi|scientific publication|bai bao)\b', folded):
        aliases.append('bài báo công bố khoa học điểm thưởng')
    if re.search(r'\b(?:result date|review dates|cong bo ket qua|xet duyet)\b', folded):
        aliases.append('thời gian xét duyệt công bố kết quả xét tuyển')
    if re.search(r'\b(?:graduation|ra truong|dau ra)\b', folded) and re.search(r'\b(?:english|language|ngoai ngu|tieng anh)\b', folded):
        aliases.append('chuẩn đầu ra ngoại ngữ bậc')
    for semester in requested_semesters(original):
        aliases.append(f'học kỳ {semester} semester {semester}')
    if re.search(r'\b(?:phu trach|ben nao|don vi|truong nao|provider)\b', folded):
        aliases.append('resources đơn vị phụ trách')
    if re.search(r'\b(?:tong|khoi luong|total)\b', folded) and requested_semesters(original):
        aliases.append('credits per semester tổng tín chỉ')
    if re.search(r"tín\s*chỉ|tin\s*chi|credits?", lowered):
        aliases.extend(("tín chỉ", "tin chi", "credits"))
    if re.search(r"thực\s*tập|thuc\s*tap|internship", lowered):
        aliases.extend(("thực tập", "thuc tap", "internship"))
    if re.search(r"tiên\s*quyết|tien\s*quyet|prerequisite", lowered):
        aliases.extend(("tiên quyết", "tien quyet", "prerequisite"))
    # Preserve codes and academic years exactly; normalized_tokens adds the
    # accent-folded form without changing these markers.
    return " ".join([original, value, *aliases])


def source_body(item: dict, *, decode_tables: bool = True) -> str:
    """Read source text and actual table cells, excluding generated provenance.

    JSON-escaped cell line breaks must become real whitespace for source code
    matching. Keep the original serialization available for existing receipts.
    Malformed or unrelated JSON stays literal; do not invent table contents.
    """
    body = re.sub(r'^\[(?:Document type|Academic years|Semester|Institution|Program|Section|Page):[^\n]*\]\s*',
                  '', str(item.get('content', '')))
    start = body.find('{"headers"')
    if not decode_tables or start < 0:
        return body
    try:
        table, end = json.JSONDecoder().raw_decode(body[start:])
    except (ValueError, TypeError):
        return body
    headers, rows = table.get('headers'), table.get('rows')
    if (not isinstance(headers, list) or not all(isinstance(cell, str) for cell in headers)
            or not isinstance(rows, list) or any(not isinstance(row, list)
            or not all(isinstance(cell, str) for cell in row) for row in rows)):
        return body
    decoded = '\n'.join(' | '.join(cells) for cells in [headers, *rows])
    return body[:start] + decoded + body[start+end:]


def requested_semesters(text: str) -> tuple[int, ...]:
    """Read explicit semester labels, without using document-level metadata."""
    value = unicodedata.normalize('NFKD', repair_mojibake(text).casefold().replace('đ', 'd'))
    value = value.encode('ascii', 'ignore').decode('ascii')
    number_words = {'mot': 1, 'dau': 1, 'mo dau': 1, 'first': 1, 'hai': 2,
                    'ba': 3, 'bon': 4, 'nam': 5, 'sau': 6, 'bay': 7, 'tam': 8,
                    'chin': 9, 'muoi': 10}
    words = '|'.join(sorted(number_words, key=len, reverse=True))
    pattern = rf'\b(?:hoc\s*ky|ky|hk|semester|sem)\s*(?:thu\s*)?(\d{{1,2}}|{words})\b'
    values = []
    for match in re.finditer(pattern, value):
        token = match.group(1)
        number = int(token) if token.isdigit() else number_words[token]
        if 1 <= number <= 20 and number not in values:
            values.append(number)
    return tuple(values)


def retrieval_text(item: dict) -> str:
    """Return searchable content plus stable provenance metadata."""
    metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
    values = [
        str(item.get("content", "")), str(item.get("doc_id", "")),
        str(metadata.get("source_name", "")), str(metadata.get("document_type", "")),
        str(metadata.get("program", "")), str(metadata.get("institution", "")),
        str(metadata.get("version", "")),
        " ".join(str(value) for value in item.get("heading_path", []) or metadata.get("heading_path", [])),
    ]
    return " ".join(value for value in values if value)


def corpus_typo_expansion(query: str, vocabulary: set[str]) -> str:
    """Preserve query text and add one-edit spelling variants present in source.

    Only unknown alphabetic words of at least six characters are expanded.
    Course codes, numbers and already known words cannot be rewritten.
    """
    aliases = []
    for token in tokenize(query):
        if len(token) < 6 or not token.isalpha() or token in vocabulary:
            continue
        variants = {token[:i] + token[i + 1:] for i in range(len(token))}
        variants.update(token[:i] + token[i + 1] + token[i] + token[i + 2:]
                        for i in range(len(token) - 1))
        aliases.extend(sorted(variants & vocabulary)[:2])
    return " ".join([query, *dict.fromkeys(aliases)])
