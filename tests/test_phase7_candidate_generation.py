import json

import pytest

from campusai.rag.context import resolve_query
from campusai.retrieval.bm25_index import BM25Index
from campusai.retrieval.hybrid import HybridRetriever
from campusai.retrieval.routing import choose_route, detected_course_codes
from campusai.retrieval.table_links import linked_table_sources
from campusai.retrieval.tokenizer_vi import corpus_typo_expansion


def record(chunk, text, *, doc="doc", page=1, language="vi"):
    return {"chunk_id": chunk, "doc_id": doc, "page": page, "content": text,
            "content_type": "text", "metadata": {"language": language, "page_range": [page, page]}}


@pytest.mark.parametrize("query", ["Môn ABC1001 có mấy tín chỉ vậy?", "Học phần XYZ2002 học ở kỳ nào thế?",
                                   "AI nâng cao trong hướng dẫn thạc sĩ học ở kỳ nào vậy"])
def test_conversational_sentence_endings_do_not_erase_self_contained_questions(query):
    assert resolve_query(query).needs_clarification is False


@pytest.mark.parametrize("query", ["Môn này có mấy tín?", "What about it?", "cái đó thì sao?"])
def test_actual_deictic_followups_still_need_context(query):
    assert resolve_query(query).needs_clarification is True


def test_program_and_semester_shorthand_is_context_not_course_identity():
    for query in ("môn trong khung ĐTVT", "KHMT HK5", "CNTT CTDT23", "kỳ HK1"):
        assert choose_route(query) == "hybrid_rrf"
        assert detected_course_codes(query) == ()
    assert detected_course_codes("ABC1001 và ZZ90001") == ("ABC1001", "ZZ90001")


def test_typo_expansion_is_source_vocabulary_bound_and_keeps_identifiers():
    assert corpus_typo_expansion("scopuss ABC1001", {"scopus", "abc100"}) == "scopuss ABC1001 scopus"
    assert corpus_typo_expansion("scopus", {"scopus"}) == "scopus"
    assert corpus_typo_expansion("unrelated", {"scopus"}) == "unrelated"


def test_course_lookup_matches_pdf_whitespace_and_keeps_unknown_code_abstention(tmp_path):
    records = [record("known", "ABC 1001 credits 3"), record("different", "ABC10010 credits 4")]
    BM25Index(records).save(tmp_path / "doc/bm25.json")
    r = HybridRetriever(tmp_path, query_cache_size=0)
    assert [v.chunk_id for v in r.search("ABC1001", ["doc"], mode="auto")] == ["known"]
    assert r.generate_candidates("ZZ90001", ["doc"]) == []


def test_table_links_use_row_codes_actual_source_page_and_scope():
    table = {"headers": ["Code", "Course", "Prerequisite"],
             "rows": [["ABC1001", "Matlab applications", "XYZ2002"]]}
    records = {"table": record("table", json.dumps(table)),
               "prerequisite": record("prerequisite", "XYZ2002"),
               "wrongpage": record("wrongpage", "XYZ2002", page=2),
               "wrongdoc": record("wrongdoc", "XYZ2002", doc="other"),
               "outside": record("outside", "ZZ90001")}
    linked = linked_table_sources("Matlab prerequisites", records, 40)
    assert set(linked) == {"table", "prerequisite"}
    assert linked_table_sources("Matlab prerequisites", records, 1) == ["table"]
    assert linked_table_sources("unrelated school policy", records, 40) == []


def test_candidate_links_recognize_named_curriculum_without_course_codes():
    table = {"headers": ["No", "Discipline", "Credits", "Resources"],
             "rows": [["Semester 1", "", "", ""],
                      ["1", "Orbital propulsion engineering", "3", "University"]]}
    records = {"curriculum": record("curriculum", json.dumps(table)),
               "wrongdoc": record("wrongdoc", "Orbital propulsion engineering", doc="other"),
               "samepage": record("samepage", "Unrelated regulation")}
    query = "How many credits for Orbital propulsion engineering?"
    assert linked_table_sources(query, records, 40) == []
    assert linked_table_sources(query, records, 40, include_named_curriculum=True) == ["curriculum"]
    assert linked_table_sources("unrelated school policy", records, 40, include_named_curriculum=True) == []
    assert linked_table_sources(query, records, 0, include_named_curriculum=True) == []


def test_named_curriculum_link_rejects_ambiguous_columns_and_section_rows():
    tables = [
        {"headers": ["Discipline", "Course"], "rows": [["Orbital engineering", "Orbital engineering"]]},
        {"headers": ["Discipline", "Credits"], "rows": [["Credits per semester", "30"]]},
        {"headers": ["Discipline", "Credits"], "rows": [["Semester 1", "30"]]},
        {"headers": ["Resources", "Credits"], "rows": [["Orbital engineering", "3"]]},
        {"headers": None, "rows": [["Orbital engineering", "3"]]},
        {"headers": [None, "Credits"], "rows": [["Orbital engineering", "3"]]},
    ]
    for table in tables:
        records = {"table": record("table", json.dumps(table))}
        assert linked_table_sources("Orbital engineering credits per semester 1", records, 40,
                                    include_named_curriculum=True) == []


def test_answer_lookup_named_table_anchor_requires_the_complete_subject_phrase():
    table = {"headers": ["Discipline", "Credits"],
             "rows": [["Orbital propulsion engineering", "3"]]}
    records = {"table": record("table", json.dumps(table))}
    assert linked_table_sources("Orbital engineering credits", records, 40,
                                include_named_curriculum=True, named_exact_only=True) == []
    assert linked_table_sources("Orbital propulsion engineering credits", records, 40,
                                include_named_curriculum=True, named_exact_only=True) == ["table"]


def test_easy_named_course_uses_table_anchor_without_a_reranker(tmp_path):
    table = {"headers": ["Discipline", "Credits"],
             "rows": [["Orbital propulsion engineering", "3"]]}
    records = [record("table", json.dumps(table))]
    records.extend(record(f"clutter-{i}", "orbital propulsion engineering credits regulation") for i in range(45))
    BM25Index(records).save(tmp_path / "doc/bm25.json")
    retriever = HybridRetriever(tmp_path, query_cache_size=0)
    values = retriever.search("Credits for Orbital propulsion engineering?", ["doc"], mode="auto")
    assert values[0].chunk_id == "table"
    assert values[0].content == records[0]["content"]
    assert retriever.reranker is None


def test_raw_candidate_pool_has_a_separate_cache_identity_and_preserves_scope(tmp_path):
    records = [record("allowed", "course prerequisite credit"), record("filtered", "course prerequisite credit", language="en")]
    BM25Index(records).save(tmp_path / "doc/bm25.json")
    r = HybridRetriever(tmp_path)
    from campusai.retrieval.calibration import RetrievalPolicy
    from campusai.retrieval.confidence import LEGACY_CONFIDENCE_MODEL
    # Deliberately impossible answer threshold; raw candidates remain inspectable.
    r.policies["hybrid_rrf"] = RetrievalPolicy(mode="hybrid_rrf", threshold=1,
        confidence_model=LEGACY_CONFIDENCE_MODEL, index_sha256=None, source="test")
    assert r.search("course prerequisite", ["doc"], mode="auto", filters={"language": "vi"}) == []
    values = r.generate_candidates("course prerequisite", ["doc"], filters={"language": "vi"})
    assert [v.chunk_id for v in values] == ["allowed"]
    assert r.search("course prerequisite", ["doc"], mode="auto", filters={"language": "vi"}) == []
    assert r.generate_candidates("course prerequisite", []) == []
    with pytest.raises(ValueError):
        r.generate_candidates("course prerequisite", ["doc"], mode="dense")
