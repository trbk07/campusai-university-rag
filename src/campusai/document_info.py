"""Structural PDF facts use trusted ingestion metadata, never retrieved prose."""
import re
import unicodedata


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd')


def page_count_request(question, documents):
    if not isinstance(question, str):
        return None
    text = folded(question)
    filenames = []
    for doc in sorted(documents, key=lambda d: len(d['name']), reverse=True):
        name = folded(doc['name'])
        if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text):
            filenames.append(name)
            text = text.replace(name, ' document ')
    filenames += re.findall(r'(?<!\w)[\w.-]+\.pdf\b', text)
    for name in filenames:
        text = text.replace(name, ' document ')
    text = ' '.join(re.sub(r'[^\w\s]', ' ', text).split())
    if re.search(r'\b(?:(?:dung|khong)\s+(?:dem|can|cho biet)|do not|don t)\b', text):
        return None
    quantity = r'\b(?:(?:bao nhieu|nhieu|may|bn) trang|(?:tong )?so trang|how many pages|page count|number of pages|how long (?:(?:is|are|this|that|the|document|pdf|file|it) )*in pages)\b'
    if not re.search(quantity, text):
        return None
    remaining = re.sub(quantity, ' ', text).split()
    allowed = set(('tai lieu file pdf tep nay do no cua co gom dai trong la tong tat ca cac vay nhi ban cho minh t toi em va and bao nhieu may bn cong nhe oi dem the ko khong cu '
                   'biet hoi voi xin giup a please how many pages page count number what is the in this that document '
                   'documents have has does do it are there total all selected uploaded tell me can could you of length long').split())
    if any(word not in allowed for word in remaining):
        return None  # Not page-specific content, an injection, or a compound request.
    named = [d for d in documents if folded(d['name']) in filenames]
    unknown_name = bool(filenames and len({folded(d['name']) for d in named}) != len(set(filenames)))
    all_documents = len(set(filenames)) > 1 or bool(re.search(r'\b(?:tat ca|cac tai lieu|tong|total|all|documents)\b', text))
    selected = named if filenames else documents
    return selected, unknown_name or not selected or (len(selected) > 1 and not all_documents)


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
