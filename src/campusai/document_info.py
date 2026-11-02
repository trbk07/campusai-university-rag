"""PDF references and structural facts use the authorized document metadata."""
import re
import unicodedata
from dataclasses import dataclass


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd')


@dataclass(frozen=True)
class PDFNameMatch:
    documents: tuple
    mentioned: bool
    unknown: bool
    ambiguous: bool
    text: str


def match_pdf_names(question, documents):
    text = folded(question)
    exact_question = unicodedata.normalize('NFC', question).casefold()
    filenames = []
    for doc in sorted(documents, key=lambda d: len(d['name']), reverse=True):
        name = folded(doc['name'])
        if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text):
            filenames.append(name)
            text = text.replace(name, ' document ')
    filenames += re.findall(r'(?<!\w)[\w.-]+\.pdf\b', text)
    for name in filenames:
        text = text.replace(name, ' document ')
    named, ambiguous_name = [], False
    for name in dict.fromkeys(filenames):
        candidates = [doc for doc in documents if folded(doc['name']) == name]
        exact = [doc for doc in candidates if re.search(r'(?<!\w)' + re.escape(
            unicodedata.normalize('NFC', doc['name']).casefold()) + r'(?!\w)', exact_question)]
        chosen = exact or candidates
        keys = [unicodedata.normalize('NFC', doc['name']).casefold() for doc in chosen]
        ambiguous_name |= (len(keys) != len(set(keys)) or not exact and len(chosen) > 1)
        named.extend(chosen)
    unknown_name = bool(filenames and len({folded(d['name']) for d in named}) != len(set(filenames)))
    return PDFNameMatch(tuple(named), bool(filenames), unknown_name, ambiguous_name, text)


def page_count_request(question, documents):
    if not isinstance(question, str):
        return None
    names = match_pdf_names(question, documents)
    text = ' '.join(re.sub(r'[^\w\s]', ' ', names.text).split())
    if re.search(r'\b(?:(?:dung|khong)\s+(?:dem|can|cho biet)|do not|don t)\b', text):
        return None
    quantity = r'\b(?:(?:bao nhieu|nhieu|may|bn) trang|(?:tong )?so trang|how many pages|page count|number of pages|how long (?:(?:is|are|this|that|the|document|pdf|file|it) )*in pages)\b'
    if not re.search(quantity, text):
        return None
    remaining = re.sub(quantity, ' ', text).split()
    allowed = set(('tai lieu file pdf tep nay do no cua co gom dai trong la tong tat ca cac moi tung vay nhi ban cho minh t toi em va and bao nhieu may bn cong nhe oi dem the ko khong cu da chon '
                   'biet hoi voi xin giup a please how many pages page count number what is the in this that document '
                   'documents pdfs files these those have has does do it are there total all each per selected uploaded tell me can could you of length long').split())
    if any(word not in allowed for word in remaining):
        return None
    explicit_names = {unicodedata.normalize('NFC', doc['name']).casefold() for doc in names.documents}
    all_documents = len(explicit_names) > 1 or bool(re.search(
        r'\b(?:tat ca|cac tai lieu|moi|tung|tong|total|all|each|per|documents|pdfs|files)\b', text))
    selected = list(names.documents) if names.mentioned else documents
    return selected, names.ambiguous or names.unknown or not selected or (len(selected) > 1 and not all_documents)


def document_info_response(question, documents, language='vi'):
    request = page_count_request(question, documents)
    if request is None:
        return None
    selected, unclear = request
    valid = [d for d in selected if type(d.get('page_count')) is int and d['page_count'] > 0]
    unavailable = not unclear and len(valid) != len(selected)
    rows = [] if unclear or unavailable else [
        {'doc_id': d['doc_id'], 'name': d['name'], 'page_count': d['page_count']} for d in valid]
    english = language == 'en'
    if unclear:
        answer = ('Which selected PDF do you mean? Please name it or ask for all selected documents.' if english
                  else 'Bạn muốn hỏi PDF nào? Hãy nêu tên file hoặc hỏi tổng số trang của tất cả tài liệu đã chọn.')
        candidates = selected or documents
        if candidates:
            answer += ('\nAvailable selected PDFs:\n' if english else '\nCác PDF trong phạm vi đã chọn:\n')
            answer += '\n'.join('- ' + doc['name'] for doc in candidates[:6])
        else:
            answer = ('No PDF is selected. Upload or select a PDF first.' if english
                      else 'Chưa có PDF trong phạm vi hỏi. Hãy tải hoặc chọn tài liệu trước.')
    elif unavailable:
        answer = ('The page count is unavailable for this PDF. Please upload it again.' if english
                  else 'Chưa đọc được số trang của PDF này. Bạn hãy tải lại file để kiểm tra.')
    else:
        answer = '\n'.join(f"{d['name']}: {d['page_count']} {'pages' if english else 'trang'}." for d in rows)
        if len(rows) > 1:
            answer += f"\n{'Total' if english else 'Tổng cộng'}: {sum(d['page_count'] for d in rows)} {'pages' if english else 'trang'}."
    return {'ok': True, 'cache_hit': False,
        'answer': {'answer': answer, 'confidence': 'low' if unclear or unavailable else 'high',
            'abstained': bool(unclear or unavailable), 'citations': [], 'claims': [],
            'schema_version': 'document-info-v1'},
        'document_info': {'kind': 'page_count', 'documents': rows,
                          'basis': 'validated_pdf_ingestion', 'needs_clarification': bool(unclear),
                          'unavailable': bool(unavailable)}}
