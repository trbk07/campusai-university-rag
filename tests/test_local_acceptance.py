"""Local metadata answers and isolated OCR must preserve their boundaries."""
import argparse

import pytest

from campusai.document_info import document_info_response, page_count_request
from campusai.ingestion.tesseract_process import worker_environment
from scripts.release.measure_ocr import percentile, sample
from scripts.release.verify_answers import inference_payload, response_errors, turns, natural_variants
from scripts.operations.local import timing_observer, LocalSetupError
from campusai.retrieval.tokenizer_vi import normalize_retrieval_query
from campusai.rag.policies import explicit_comparison_request, has_conflicting_numeric_evidence
from campusai.retrieval.hybrid import RetrievalResult
from campusai.rag.regulation_facts import deterministic_regulation_fact, regulation_request


@pytest.fixture
def documents():
    return [{'doc_id': 'alpha', 'name': 'alpha.pdf', 'page_count': 7},
            {'doc_id': 'beta', 'name': 'beta.pdf', 'page_count': 11}]


@pytest.mark.parametrize('question', [
    'How many pages are in the selected PDFs?',
    'How many pages do these files have?',
    'What is the total number of pages in those PDFs?',
    'Tổng số trang của tất cả tài liệu đã chọn?',
])
def test_plural_files_use_validated_page_metadata(question, documents):
    response = document_info_response(question, documents, 'en')
    assert response['answer']['abstained'] is False
    assert response['answer']['answer'].endswith('Total: 18 pages.')
    assert response['document_info']['basis'] == 'validated_pdf_ingestion'
    assert {row['doc_id'] for row in response['document_info']['documents']} == {'alpha', 'beta'}


@pytest.mark.parametrize('question', [
    'How many pages explain the admission requirements?',
    'How many pages are in the selected PDFs and what are the fees?',
    'Do not tell me the number of pages in these files.',
])
def test_page_specific_content_is_not_replaced_with_document_metadata(question, documents):
    assert page_count_request(question, documents) is None


def test_singular_unspecified_file_still_requires_clarification(documents):
    response = document_info_response('How many pages does this file have?', documents, 'en')
    assert response['answer']['abstained'] is True
    assert response['document_info']['needs_clarification'] is True


def test_ocr_child_does_not_inherit_secondary_or_custom_credentials():
    original = {'Path': '/bin', 'SystemRoot': 'C:/Windows', 'TEMP': '/tmp',
        'CUDA_VISIBLE_DEVICES': '0', 'OMP_NUM_THREADS': '64', 'PYTHONPATH': '/untrusted',
        'GEMINI_API_KEY': 'example', 'GEMINI_API_KEY_2': 'example', 'GEMINI_API_KEY_3': 'example',
        'CUSTOM_MODEL_CREDENTIAL': 'example', 'UNEXPECTED_SETTING': 'example'}
    assert worker_environment(original) == {'Path': '/bin', 'SystemRoot': 'C:/Windows', 'TEMP': '/tmp',
        'CUDA_VISIBLE_DEVICES': '0', 'OMP_THREAD_LIMIT': '1', 'OMP_NUM_THREADS': '1'}
    assert original['OMP_NUM_THREADS'] == '64'


def test_nearest_rank_reports_observed_tail_without_interpolation():
    assert percentile(list(range(1, 21))) == 19
    assert percentile([7]) == 7
    with pytest.raises(ValueError):
        percentile([])


@pytest.mark.parametrize('value', ['document.pdf', 'document.pdf::1,1', 'document.pdf::0', 'document.pdf::a'])
def test_ocr_workload_rejects_ambiguous_physical_pages(value):
    with pytest.raises(argparse.ArgumentTypeError):
        sample(value)


def test_owner_labels_and_gold_never_become_inference_input():
    row = {'id': 'arbitrary', 'group': 'fact', 'school': 'secret_label',
           'expected': 'gold_not_for_the_model', 'source': 'gold_page',
           'input': 'What does the selected document say?'}
    payload = inference_payload(turns(row)[0], ['selected-by-user'], [], 'en')
    assert payload == {'question': row['input'], 'doc_ids': ['selected-by-user'], 'history': [], 'language': 'en'}
    assert 'gold_not_for_the_model' not in str(payload)
    assert 'secret_label' not in str(payload)


def test_multiturn_benchmark_preserves_actual_question_order():
    assert turns({'group': 'multi-turn', 'input': 'Lượt 1: Explain this. | Lượt 2: Why?'}) == ['Explain this.', 'Why?']


def test_natural_variants_preserve_question_and_do_not_add_gold_or_school():
    row = {'id': 'case', 'group': 'fact', 'input': 'How is this defined?', 'school': 'hidden', 'expected': 'gold'}
    variant = natural_variants([row], 1, 'en')[0]
    payload = inference_payload(variant['input'], ['selected'], [], 'en')
    assert variant['input'].endswith(row['input'])
    assert 'hidden' not in str(payload) and 'gold' not in str(payload)
    assert row['input'] == 'How is this defined?'
    with pytest.raises(ValueError):
        natural_variants([{'id': 'multi', 'group': 'multi-turn', 'input': 'Turn 1: Hi'}], 1)


def test_provider_counters_separate_real_inference_from_token_count(monkeypatch):
    from urllib.request import Request
    from campusai.llm import client as provider
    from campusai.request_timings import capture_request
    monkeypatch.setattr(provider, '_request_json', lambda *a, **k: {'modelVersion': 'gemini-unit-v1'})
    client = provider.GeminiClient('example', model='gemini-unit', max_retries=0)
    try:
        with capture_request() as trace:
            client._send(Request(client.endpoint, data=b'{}'))
            client._send(Request(client.endpoint.replace(':generateContent', ':countTokens'), data=b'{}'))
        assert trace['stage_calls']['provider_inference_success'] == 1
        assert trace['stage_calls']['provider_token_count_success'] == 1
        assert trace['stage_calls']['provider_model.gemini-unit-v1'] == 1
    finally:
        client.close()


def test_acceptance_rejects_missing_or_malformed_answer_contract():
    assert response_errors({'ok': True, 'answer': None}, {})
    assert response_errors([], {}) == ['request_failed']


def test_opt_in_timing_log_excludes_question_answer_and_source_data(tmp_path):
    import json
    path = tmp_path / 'timings.jsonl'
    observe = timing_observer(path)
    observe({'request_id': 'trace', 'server_total_ms': 12, 'stages_ms': {'llm': 8},
             'stage_calls': {'llm': 1}, 'cache_hit': False, 'question': 'private',
             'answer': 'private', 'retrieval_trace': {'content': 'private'}})
    row = json.loads(path.read_text(encoding='utf-8'))
    assert set(row) == {'request_id', 'server_total_ms', 'stages_ms', 'stage_calls', 'cache_hit'}
    assert 'private' not in path.read_text(encoding='utf-8')
    with pytest.raises(LocalSetupError):
        timing_observer(path)


def test_previous_course_does_not_expand_to_passed_prerequisite():
    query = normalize_retrieval_query('Môn học trước của chương trình có cần đạt không?')
    assert 'tiên quyết' not in query and 'prerequisite' not in query
    assert 'học phần học trước' in query
    assert 'prerequisite' in normalize_retrieval_query('Điều kiện tiên quyết là gì?')


def test_contact_and_cohort_expansion_contains_no_source_facts():
    assert 'địa chỉ' in normalize_retrieval_query('Trụ sở tổ chức nằm ở đâu?')
    assert 'khóa tuyển sinh' in normalize_retrieval_query('Quy định áp dụng từ khóa nào?')


@pytest.mark.parametrize('question', [
    'Các nguồn có giống nhau không?', 'Hai cách tính có khác nhau không?',
    'Are those values the same?', 'Are the values different?',
])
def test_natural_comparisons_are_explicit(question):
    assert explicit_comparison_request(question)


def test_comparison_still_rejects_disagreement_inside_one_source():
    def result(ident, doc, amount):
        return RetrievalResult(ident, doc, 1, f'The fee is {amount} dollars.', 'text', 1., 'test', {})
    left, right = result('a', 'one', 12), result('b', 'two', 18)
    question = 'Are the fee amounts of 12 and 18 the same?'
    assert not has_conflicting_numeric_evidence([left, right], question)
    assert has_conflicting_numeric_evidence([left, result('c', 'one', 18)], question)
    assert not explicit_comparison_request('Do not compare the fees.')


def test_short_query_words_do_not_merge_unrelated_numeric_subjects():
    results = [RetrievalResult('rent', 'source', 1, 'The rent is 12 dollars.', 'text', 1., 'test', {}),
               RetrievalResult('tax', 'source', 1, 'The tax is 18 dollars.', 'text', 1., 'test', {})]
    assert not has_conflicting_numeric_evidence(results, 'What is the tax of 18 dollars?')


def source_rule(text, ident='rule'):
    return RetrievalResult(ident, 'fictional', 2, text, 'text', 1., 'test',
        {'source_name': 'fictional.pdf', 'page_range': [2, 2], 'heading_path': ['Rules']})


def test_registration_limit_keeps_final_year_exception_from_source():
    result = source_rule('a) Sinh viên không thuộc diện cảnh báo học tập được đăng ký tối đa 21 TC '
        'và tối thiểu 6 TC trong học kỳ chính, không áp dụng ngưỡng TC đăng ký tối thiểu với sinh viên trình độ năm cuối.')
    answer = deterministic_regulation_fact('Kỳ chính sinh viên đăng ký bao nhiêu tín chỉ?', [result], 'vi')
    assert answer and not answer.abstained
    assert '21 TC' in answer.answer and '6 TC' in answer.answer and 'năm cuối' in answer.answer
    assert answer.citations[0].quote in result.content


def test_summer_limit_handles_pdf_line_wrapping_without_other_term():
    result = source_rule('Điều kiện trên không áp dụng cho năm cuối. Sinh viên được đăng\n'
        'ký tối đa 5 TC trong học kỳ hè.')
    answer = deterministic_regulation_fact('Kỳ hè tối đa mấy tín?', [result], 'vi')
    assert answer and not answer.abstained and '5 TC' in answer.answer
    assert 'năm cuối' not in answer.answer


def test_warning_limit_retains_governing_level_and_term():
    result = source_rule('2. Hạn chế khối lượng học tập là hình thức buộc những sinh viên đang bị cảnh báo học tập '
        'từ mức 3 trở lên đăng ký số TC học phần ít hơn bình thường tại học kỳ 2 của năm học, cụ thể như sau:\n'
        'a) Sinh viên thuộc các CTĐT chuẩn được đăng ký tối đa 13 TC và tối thiểu 7 TC cho một học kỳ chính;\n'
        'b) Quy định khác.')
    question = 'Sinh viên cảnh báo mức 3 chương trình chuẩn đăng ký bao nhiêu tín kỳ chính?'
    answer = deterministic_regulation_fact(question, [result], 'vi')
    assert answer and not answer.abstained
    assert 'mức 3' in answer.answer and 'học kỳ 2' in answer.answer
    assert '13 TC' in answer.answer and '7 TC' in answer.answer
    assert deterministic_regulation_fact(question.replace('mức 3', 'mức 2'), [result], 'vi') is None


def test_cohort_lookup_uses_document_applicability_not_training_method():
    result = source_rule('Điều 2. Quy chế này có hiệu lực kể từ ngày kí và áp dụng đối với các\n'
        'khóa tuyển sinh từ năm 2032.')
    answer = deterministic_regulation_fact('Quy chế áp dụng từ khóa nào?', [result], 'vi')
    assert answer and not answer.abstained and '2032' in answer.answer
    unrelated = source_rule('Trường áp dụng phương thức đào tạo theo tín chỉ cho tất cả các khóa.')
    assert deterministic_regulation_fact('Quy chế áp dụng từ khóa nào?', [unrelated], 'vi') is None


def test_registration_conflicts_are_not_selected_by_first_match():
    text = 'a) Sinh viên không thuộc diện cảnh báo học tập được đăng ký tối đa 21 TC và tối thiểu 6 TC trong học kỳ chính.'
    answer = deterministic_regulation_fact('Kỳ chính đăng ký bao nhiêu tín chỉ?',
        [source_rule(text), source_rule(text.replace('21 TC', '22 TC'), 'other')], 'vi')
    assert answer and answer.abstained


def test_compound_or_multi_term_question_keeps_full_generation_path():
    assert regulation_request('Kỳ chính tối đa bao nhiêu tín chỉ và học phí là bao nhiêu?') is None
    assert regulation_request('Kỳ chính và kỳ hè tối đa bao nhiêu tín chỉ?') is None
    assert regulation_request('Không đăng ký đủ tín chỉ tối thiểu kỳ chính sẽ bị gì?') is None
    assert regulation_request('Thạc sĩ kỳ chính đăng ký tối đa bao nhiêu tín chỉ?') is None
    assert regulation_request('Quy chế áp dụng từ khóa nào và học phí bao nhiêu?') is None


def test_explicit_exam_organization_answers_existence_without_guessing_eligibility():
    result = source_rule('b) Cuối mỗi học kỳ, Nhà trường tổ chức một kỳ thi chính và một kỳ thi phụ.')
    answer = deterministic_regulation_fact('Trường có kỳ thi phụ không?', [result], 'vi')
    assert answer and not answer.abstained
    assert answer.answer == 'Cuối mỗi học kỳ, Nhà trường tổ chức một kỳ thi chính và một kỳ thi phụ.'
    unrelated = source_rule('Trường không tổ chức kỳ thi phụ trong năm học này.')
    assert deterministic_regulation_fact('Trường có kỳ thi phụ không?', [unrelated], 'vi') is None
    assert regulation_request('Nếu em trượt thì có kỳ thi phụ không?') is None


def font_mapping_fixture(path):
    """Visible ASCII stays intact while ToUnicode deliberately lies about glyphs."""
    import pymupdf as fitz
    lines = ['CONTROLLED FONT MAPPING FIXTURE',
        'THIS DOCUMENT USES AN INTENTIONALLY DAMAGED CHARACTER MAP.',
        'THE VISIBLE LETTERS REMAIN THE ORIGINAL REFERENCE TEXT.',
        'EVERY READER SHOULD STILL SEE THIS SENTENCE CLEARLY.',
        'THE PARSER MUST REQUEST OCR INSTEAD OF TRUSTING WRONG GLYPHS.']
    with fitz.open() as doc:
        page = doc.new_page()
        for number, line in enumerate(lines):
            page.insert_text((42, 80 + number * 28), line, fontname='helv', fontsize=13)
        pairs = []
        for value in range(32, 127):
            char = chr(value)
            target = 0xE000 if char == 'E' else value + 0xFEE0 if char.isalpha() else value
            pairs.append('<%02X> <%04X>' % (value, target))
        cmap = ('/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n'
            '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n'
            '/CMapName /ControlledMapping def\n/CMapType 2 def\n1 begincodespacerange\n<00> <FF>\n'
            'endcodespacerange\n%d beginbfchar\n%s\nendbfchar\nendcmap\n'
            'CMapName currentdict /CMap defineresource pop\nend\nend\n') % (len(pairs), '\n'.join(pairs))
        xref = doc.get_new_xref()
        doc.update_object(xref, '<<>>')
        doc.update_stream(xref, cmap.encode())
        doc.xref_set_key(page.get_fonts()[0][0], 'ToUnicode', f'{xref} 0 R')
        doc.xref_set_key(-1, 'ID', '[<00112233445566778899AABBCCDDEEFF><00112233445566778899AABBCCDDEEFF>]')
        doc.save(path, garbage=4, deflate=True, no_new_id=True)
    return '\n'.join(lines)


def test_corrupt_font_mapping_requests_ocr_and_never_publishes_bad_native_text(tmp_path):
    from campusai.ingestion.docling_parser import parse_pdf
    first, second = tmp_path / 'font-one.pdf', tmp_path / 'font-two.pdf'
    font_mapping_fixture(first)
    font_mapping_fixture(second)
    assert first.read_bytes() == second.read_bytes()
    page = parse_pdf(first)[0]
    assert page['untrusted_native_mapping'] is True
    assert page['requires_ocr'] is True
    assert page['text'] == '' and page['visible_characters'] == []
