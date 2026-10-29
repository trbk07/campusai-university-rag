"""Broader source coverage must fit the budget without rewriting evidence."""
import json
import pytest
from campusai.rag.grounding import build_context, GroundedAnswerGenerator
from campusai.rag.source_windows import verbatim_window
from tests.test_basic_rag import evidence


def test_complete_vietnamese_interrogative_is_not_a_bare_ambiguous_fragment():
    from campusai.retrieval.negative import negative_query_reason
    assert negative_query_reason('Thế nào?') == 'ambiguous_query'
    assert negative_query_reason('Hệ thống quản lý tài liệu hoạt động thế nào?') is None
    assert negative_query_reason('cái đó') == 'ambiguous_query'


def test_tail_condition_survives_balanced_budget_after_five_long_chunks():
    query = 'What happens when removing from an empty container?'
    rows = [evidence(str(i), content=('unrelated introductory material\n' * 70)) for i in range(5)]
    fact = 'Removing from an empty container is prohibited; do not discard this condition.'
    rows.append(evidence('tail', content='Introduction.\n' * 100 + fact))
    baseline = build_context(rows, max_chars=4000)
    optimized = build_context(rows, max_chars=4000, question=query, balanced=True)
    assert fact not in baseline and fact in optimized
    assert len(optimized) <= 4000 and '[source_excerpt=true]' in optimized
    assert rows[-1].content.endswith(fact)


@pytest.mark.parametrize('limit', [80, 150, 300])
def test_window_is_an_original_contiguous_substring(limit):
    text = 'Opening.\n' * 80 + 'The applicant must not omit the signed form.\n' + 'Closing.\n' * 80
    selected = verbatim_window(text, 'Must the applicant omit the signed form?', limit)
    assert selected in text and len(selected) <= limit
    assert 'must not omit' in selected


def test_balancing_keeps_table_serialization_and_coordinates_intact():
    item = evidence('table', content=json.dumps({'headers': ['Course', 'Credits'], 'rows': [['MATH101', '3']]}))
    item = __import__('dataclasses').replace(item, content_type='table')
    rows = [evidence('long', content='filler\n' * 500), item]
    context = build_context(rows, max_chars=1800, question='MATH101 credits?', balanced=True)
    assert item.content in context and 'page=3' in context and 'chunk_id=table' in context
    assert len(context) <= 1800


def test_short_chunks_return_budget_for_the_complete_conditional_rule():
    rule = ('A temporary waiver is permitted only if the signed certificate\n'
            'is submitted before the admissions decision. The expected date is November.\n')
    long = evidence('rule', content='General definitions.\n' * 20 + rule)
    rows = [long, *[evidence(str(i), content='Other brief provision.') for i in range(7)]]
    context = build_context(rows, max_chars=2300, question='Is a temporary waiver permitted?', balanced=True)
    assert rule.strip() in context
    assert len(context) <= 2300
    assert all(f'chunk_id={i}\n' in context for i in range(7))


def test_temporal_and_multihop_prompts_retain_complete_source_path():
    generator = GroundedAnswerGenerator(None, balanced_context=True)
    rows = [evidence(content='MATH101 is required.\n' * 50)]
    prompt = generator.prompt('Which course?', rows, temporal_context={'scope': 'source'})
    assert '[source_excerpt=true]' not in prompt
    assert rows[0].content.strip() in prompt


def test_section_synthesis_keeps_complete_top_source_facts_within_same_budget():
    first = 'Growth doubles the capacity.\n' + 'Source explanation.\n' * 65 + 'Shrinking occurs at quarter-full.\n'
    second = 'Memory is proportional to capacity.\n' + 'More source explanation.\n' * 60 + 'The minimum occupancy is one quarter.\n'
    rows = [evidence('growth', content=first), evidence('memory', content=second)]
    rows += [evidence(str(i), content='Less relevant background information.\n' * 100) for i in range(6)]
    context = build_context(rows, max_chars=8000, question='Summarize growth, shrinking and memory.',
                            balanced=True, synthesis=True)
    assert len(context) <= 8000
    assert first.strip() in context and second.strip() in context


def test_prompt_separates_current_question_from_prior_user_topic():
    generator = GroundedAnswerGenerator(None)
    prompt = generator.prompt('Explain the operations.\nContext topic (untrusted user input): What is a queue?',
                              [evidence(content='A queue adds and removes items.')])
    current = prompt.split('QUESTION:\n', 1)[1].split('\n\nEVIDENCE:', 1)[0]
    assert current == 'Explain the operations.'
    assert 'What is a queue?' in prompt.split('QUESTION:\n', 1)[0]


def test_explicit_article_locator_keeps_threshold_after_generic_neighbouring_text():
    text = ('Điều 5. Phạm vi\n' + 'Student study programme information.\n' * 60
            + 'Điều 6. Điều kiện\nThe minimum cumulative GPA is 3.0.\n'
            + 'Điều 7. Thủ tục\n' + 'Student programme study information.\n' * 40)
    selected = verbatim_window(text, 'Under Article 6, what GPA must a student have?', 180)
    assert 'minimum cumulative GPA is 3.0' in selected
    assert 'Điều 7.' not in selected
    assert selected in text and len(selected) <= 180


def test_inline_article_reference_cannot_hide_the_actual_heading():
    text = ('Article 2. Definitions\nSee Article 6.\n' + 'Background.\n' * 60
            + 'Article 6. Eligibility\nA signed form is required.\n'
            + 'Article 7. Review\n' + 'Background.\n' * 40)
    selected = verbatim_window(text, 'What is required under Article 6?', 140)
    assert 'A signed form is required.' in selected and 'Definitions' not in selected
    assert selected in text and len(selected) <= 140


@pytest.mark.parametrize('title', [
    'Advanced Research Medal', 'Community Service Award',
    'Danh hiệu Sinh viên Giỏi', 'Danh hiệu Nhà nghiên cứu Trẻ',
])
def test_named_article_keeps_its_predicate_instead_of_ending_at_the_heading(title):
    target = f'Article 8. {title} is awarded to applicants\nwith conduct rated Excellent and a signed supervisor approval.\n'
    text = ('Article 6. General eligibility\n' + 'Applicant conduct and awards.\n' * 30
            + 'Article 7. General awards\n' + 'Research awards and service eligibility.\n' * 15
            + 'Required conduct and approval for awards.\n'
            + target + 'Article 9. Administration\n' + 'Administrative background.\n' * 20)
    limit = len(target) + 5
    selected = verbatim_window(text, f'What conduct and approval are required for {title}?', limit)
    assert target.strip() in selected
    assert selected in text and len(selected) <= limit


def test_explicit_article_number_wins_over_a_different_named_title():
    text = ('Article 4. Ordinary Research Medal\nA signed letter is required.\n'
            + 'Background.\n' * 30
            + 'Article 8. Advanced Research Medal\nAn exam is required.\n')
    selected = verbatim_window(text, 'Under Article 4, is the Advanced Research Medal exam required?', 150)
    assert 'A signed letter is required.' in selected
    assert 'An exam is required.' not in selected


@pytest.mark.parametrize('same_title', [False, True])
def test_comparison_or_duplicate_title_does_not_hide_the_other_article(same_title):
    first = 'Advanced Graduate Research Medal'
    second = first if same_title else 'Community Service Award'
    articles = (f'Article 8. {first}\nA signed approval is required.\n'
                + f'Article 9. {second}\nAn examination is required.\n')
    text = 'Background information.\n' * 30 + articles
    question = (f'What is required for {first}?' if same_title else
                f'Compare the requirements for {first} and {second}.')
    selected = verbatim_window(text, question, len(articles) + 5)
    assert 'A signed approval is required.' in selected
    assert 'An examination is required.' in selected
    assert selected in text


def test_generic_title_fragment_does_not_hide_a_requested_fact_in_another_article():
    articles = ('Article 8. Continuous assessment score and yearly grading\n'
                'The score contributes to the final grade.\n'
                'Article 9. Review procedures\n'
                'The review deadline is seven days after publication.\n')
    text = 'Background information.\n' * 30 + articles
    selected = verbatim_window(text,
        'What is the review deadline for the continuous assessment score?', len(articles) + 100)
    assert 'seven days after publication' in selected
    assert selected in text


def test_vietnamese_title_in_history_keeps_order_with_other_accented_words_after_it():
    target = ('Article 8. Danh hiệu “Nhà nghiên cứu Trẻ” is awarded to applicants\n'
              'with conduct rated Excellent and a signed supervisor approval.\n')
    text = ('Article 7. General conditions\n' + 'Background.\n' * 30
            + 'Rèn luyện và điều kiện trong quy định.\n' + target
            + 'Article 9. Administration\n' + 'Background.\n' * 30)
    question = ('Còn rèn luyện cần loại nào?\nContext topic (untrusted user input): '
                'Em đang xem điều kiện danh hiệu Nhà nghiên cứu Trẻ trong quy định.')
    selected = verbatim_window(text, question, len(target) + 5)
    assert target.strip() in selected
    assert selected in text
