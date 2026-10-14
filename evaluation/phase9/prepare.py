"""Read preserved sources and freeze the gap audit before temporal changes.

Never downloads data, calls an LLM, or changes historical indexes.
"""
import hashlib
import json
import re
from bs4 import BeautifulSoup
from evaluation.common.artifact_store import ROOT, resolve_artifact
from campusai.ingestion.metadata_detector import detect_metadata

OUT = ROOT / 'evaluation/phase9'
RAW = ROOT / '.local_artifacts/experiment_runs/phase9-20261014'
INDEX = ROOT / '.tmp/phase7-curated-source-20261005-v2/index'
HTML = RAW / 'electronics-qh2025.html'
URL = 'https://fet.uet.vnu.edu.vn/2026/01/01/chuong-trinh-dao-tao-nganh-ky-thuat-dien-tu-vien-thong-ap-dung-cho-khoa-qh-2025/'
IDS = {
    'robotics-2020': 'd39c59d1f20bd87275cbe8758d179ac90cd1e2045ef07f7270830bb167540e09',
    'robotics-QH2025': '1cb9ffe7c5e7524b641b2811bcfcd181b6666f56450c8278abb6db284042236d',
    'electronics-2023': 'cb9a88c6025b61c4545a2bd9b4e89678873a583ee8fa45a1cc9b01795be7e1a6',
}


def sha(path):
    return hashlib.sha256(resolve_artifact(path).read_bytes()).hexdigest()


def write_once(path, value):
    if path.exists():
        assert json.loads(path.read_text(encoding='utf-8')) == value, str(path)
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare():
    frozen = OUT / 'protocol.json'
    if frozen.exists():
        protocol = json.loads(frozen.read_text(encoding='utf-8'))
        assert sha(OUT / 'benchmark.jsonl') == protocol['benchmark_sha256']
        assert sha(OUT / 'source-audit.json') == protocol['audit_sha256']
        assert sha(RAW / 'source-records.json') == protocol['source_records_sha256']
        for path, digest in protocol['source_bindings'].items():
            assert sha(ROOT / path) == digest, path
        assert (OUT / 'source-rubric.json').is_file()
        print(json.dumps(dict(status='FROZEN_INPUTS_VERIFIED', baseline='Historical failure retained; current detector is not used to rewrite it.')))
        return
    sources, bindings = [], {}
    for label, doc_id in IDS.items():
        path = INDEX / doc_id / 'bm25.json'
        items = json.loads(path.read_text(encoding='utf-8'))['items']
        bindings[path.relative_to(ROOT).as_posix()] = sha(path)
        sources.append(dict(label=label, doc_id=doc_id, original_items=items,
                            source_kind='preserved_pdf_or_original_html_pdf_snapshot'))
    html = resolve_artifact(HTML).read_bytes()
    assert hashlib.sha256(html).hexdigest() == 'df2c17bf39827eec0040da09d6582c28c0f73f7b89ef136082a3735dbaf5d490'
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.select_one('h1').get_text(' ', strip=True)
    article = soup.select_one('.td-post-content')
    assert article and 'QH-2025' in title
    doc_id = hashlib.sha256(html).hexdigest()
    blocks = [title]
    for node in article.find_all(['p', 'h2', 'h3', 'h4', 'li', 'tr']):
        if node.find_parent(['li', 'tr']):
            continue
        if node.name == 'tr':
            text = json.dumps([cell.get_text(' ', strip=True) for cell in node.find_all(['th', 'td'], recursive=False)], ensure_ascii=False)
        else:
            text = node.get_text(' ', strip=True)
        if text.strip():
            blocks.append(text)
    assert any('135' in b for b in blocks)
    # A logical snapshot page is declared; never label it a physical PDF page.
    items = [dict(chunk_id=f'{doc_id}_html_b{i}', doc_id=doc_id, page=1,
        content=block, content_type='table' if block.startswith('[') else 'text',
        metadata=dict(source_url=URL, source_hash=doc_id,
            source_name='UET electronics QH-2025 — preserved HTML snapshot',
            page_range=[1, 1], page_kind='html_snapshot_logical_page',
            institution='VNU-UET', program='Electronics and Communications Engineering Technology'))
        for i, block in enumerate(blocks)]
    sources.append(dict(label='electronics-QH2025', doc_id=doc_id,
                        source_kind='official_html_preserved_bytes', original_items=items))
    bindings[HTML.relative_to(ROOT).as_posix()] = sha(HTML)
    by_label = {s['label']: s for s in sources}
    source_checks = {
        'robotics-2020': ['1120/QĐ-ĐT', '11 tháng 12 năm 2020', 'Robotics Engineering'],
        'robotics-QH2025': ['QH', '2025', 'Robotics'],
        'electronics-2023': ['năm 2023', '7510302', 'từ khóa tuyển'],
        'electronics-QH2025': ['QH-2025', '7510302', '135'],
    }
    for label, needles in source_checks.items():
        body = '\n'.join(i['content'] for i in by_label[label]['original_items'])
        assert all(needle in body for needle in needles), label
    baseline_input = 'ban hành ngày 01/08/2025\nIssue date: 01/08/2025'
    baseline = detect_metadata(baseline_input)
    assert baseline['effective_date'] == '2025-08-01', 'baseline changed before freeze'
    audit = dict(schema_version=1, status='SOURCE_INVENTORY_AND_GAP_AUDIT_COMPLETE',
        reviewer='Codex — Automated AI Review', families={'robotics': 'dev', 'electronics': 'acceptance'},
        source_labels=list(by_label), provider_posts=0,
        gaps=[
            dict(id='issue_vs_effective', reproduced=True, input=baseline_input,
                 expected_effective_date=None, actual_effective_date=baseline['effective_date']),
            dict(id='metadata_date_provenance', detail='ISO date evidence may fall back to unrelated first line; bind exact date clause.'),
            dict(id='mentioned_vs_applicable_year', detail='Mentioned-year postings do not establish applicability.'),
            dict(id='missing_resolver', detail='No pre-ranking version resolver or reference-day cache binding.'),
            dict(id='family_coverage', detail='Existing 20 temporal cases are one amendment-table regression, not 20 independent families.'),
        ], source_limitations=[
            'Electronics 2023 cover has blank day/month: preserve year precision.',
            'Electronics 2023 applies from intake 2022: version year is not applicability year.',
            'QH-2025 is a cohort statement, not a legal effective date.',
            'Latest/current/as-of with unknown dates or precedence must remain insufficient/conflict.',
            'No acceptance answers generated or evaluated; source review is delegated AI, not human signoff.',
        ], bindings=bindings)
    write_once(OUT / 'source-audit.json', audit)
    write_once(RAW / 'source-records.json', dict(schema_version=1, sources=sources, bindings=bindings))
    cases = []
    for family, split, old_label, new_label in [
        ('robotics', 'dev', 'robotics-2020', 'robotics-QH2025'),
        ('electronics', 'acceptance', 'electronics-2023', 'electronics-QH2025'),
    ]:
        old_id, new_id = by_label[old_label]['doc_id'], by_label[new_label]['doc_id']
        old_year = 2020 if family == 'robotics' else 2023
        subject = 'Kỹ thuật Robot' if family == 'robotics' else 'Công nghệ kỹ thuật điện tử – viễn thông'
        questions = [
            ('explicit', f'Theo bản chương trình {subject} năm {old_year}, danh hiệu tốt nghiệp là gì?', 'resolved', [old_id]),
            ('explicit', f'Theo bản chương trình {subject} QH-2025, thời gian đào tạo là bao lâu?', 'resolved', [new_id]),
            ('as_of', f'Tại ngày 01/01/2024, bản chương trình {subject} nào có hiệu lực?', 'insufficient_evidence', []),
            ('as_of', f'Tại ngày 01/01/2026, chương trình {subject} đã có hiệu lực chưa?', 'insufficient_evidence', []),
            ('latest', f'Bản mới nhất của chương trình {subject} trong các tài liệu đã chọn là bản nào?', 'insufficient_evidence', []),
            ('latest', f'Chương trình {subject} hiện hành có danh hiệu tốt nghiệp gì?', 'insufficient_evidence', []),
            ('compare', f'So sánh danh hiệu tốt nghiệp của {subject} giữa bản {old_year} và bản QH-2025.', 'resolved', [old_id, new_id]),
            ('compare', f'So sánh thời gian đào tạo của {subject} giữa bản {old_year} và bản QH-2025.', 'resolved', [old_id, new_id]),
            ('unknown', f'Theo bản chương trình {subject} năm 2099, thời gian đào tạo là bao lâu?', 'insufficient_evidence', []),
            ('unknown', f'Theo bản chương trình {subject} QH-2024, danh hiệu tốt nghiệp là gì?', 'insufficient_evidence', []),
            ('scope', f'Theo bản chương trình {subject} QH-2025, thời gian đào tạo là bao lâu?', 'insufficient_evidence', []),
            ('scope', f'So sánh danh hiệu tốt nghiệp của {subject} giữa bản {old_year} và bản QH-2025.', 'insufficient_evidence', []),
        ]
        for i, (group, question, status, eligible) in enumerate(questions, 1):
            cases.append(dict(qid=f'p9-{family}-{i:02d}', family=family, split=split,
                category=group, question=question, doc_ids=[old_id] if group == 'scope' else [old_id, new_id],
                reference_date='2026-10-14', expected_status=status, expected_eligible_doc_ids=eligible,
                answerable=status == 'resolved', expected_behavior='answer_grounded' if eligible else 'abstain_before_model',
                source_labels=[old_label, new_label], review='Codex — Automated AI Review',
                exposure='source-reviewed, not fresh independent validation'))
    benchmark = OUT / 'benchmark.jsonl'
    payload = '\n'.join(json.dumps(c, ensure_ascii=False) for c in cases) + '\n'
    if benchmark.exists():
        assert benchmark.read_text(encoding='utf-8') == payload
    else:
        benchmark.write_text(payload, encoding='utf-8')
    protocol = dict(schema_version=1, status='FROZEN_BEFORE_TEMPORAL_IMPLEMENTATION',
        scope='Small real-source quality regression; no API qualification or fresh-validation claim.',
        benchmark_sha256=sha(benchmark), source_records_sha256=sha(RAW / 'source-records.json'),
        audit_sha256=sha(OUT / 'source-audit.json'), count=24, dev=12, acceptance=12,
        families_disjoint=True, additional_regression='20 existing Phase 8 temporal cases, reported separately',
        requirements=dict(resolution_accuracy=1.0, semantic_answer_accuracy=1.0,
            safe_negatives=1.0, false_abstentions=0, scope_leaks=0, unsupported_claims=0,
            public_schema_validity=1.0, source_coordinate_validity=1.0, minimum_coverage_percent=85),
        limitations=[
            'Both genuine families lack a sufficiently proven effective timeline/precedence. Real latest/as-of cases must abstain; positive date/precedence mechanics are separately synthetic contract tests.',
            'A lexical version label permits explicit selection but never proves global current/latest legal validity.',
            'Two families and 12 acceptance cases are bounded regression, not broad statistical guarantees.',
            'Electronics HTML uses explicitly labelled snapshot pagination, not original physical PDF pages.',
        ], source_bindings=bindings, provider_posts=0)
    write_once(OUT / 'protocol.json', protocol)
    rubric = []
    for case in cases:
        expected = []
        if case['answerable']:
            field = 'duration' if 'thời gian đào tạo' in case['question'].casefold() else 'degree'
            labels = [label for label in case['source_labels']
                      if by_label[label]['doc_id'] in case['expected_eligible_doc_ids']]
            for label in labels:
                pattern = (r'Thời[\s\xa0]+gian[\s\xa0]+đào[\s\xa0]+tạo[^\n]*'
                           if field == 'duration' else r'Danh[\s\xa0]+hiệu[\s\xa0]+tốt[\s\xa0]+nghiệp[^\n]*')
                found = None
                for item in by_label[label]['original_items']:
                    match = re.search(pattern, item['content'], re.I)
                    if match:
                        found = dict(label=label, field=field, doc_id=by_label[label]['doc_id'],
                            chunk_id=item['chunk_id'], page=item['page'], quote=match[0])
                        break
                assert found, (label, field)
                expected.append(found)
        rubric.append(dict(qid=case['qid'], expected_status=case['expected_status'],
            eligible_doc_ids=case['expected_eligible_doc_ids'], claims=expected,
            negative_basis=None if expected else 'Missing effective date/precedence, unavailable requested version, or requested counterpart outside selected scope.'))
    write_once(OUT / 'source-rubric.json', dict(schema_version=1,
        status='SOURCE_REVIEWED_BEFORE_TEMPORAL_IMPLEMENTATION', benchmark_sha256=sha(benchmark),
        source_records_sha256=sha(RAW / 'source-records.json'),
        reviewer='Codex — Automated AI Review', officially_human_approved=False,
        cases=rubric, limitation='The 2023 electronics source contains blank signature date/number; no signed/current effectiveness is asserted.'))
    print(json.dumps(dict(status=audit['status'], families=2, sources=4, baseline_reproduced=True)))


if __name__ == '__main__':
    prepare()
