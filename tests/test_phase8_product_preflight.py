import hashlib
import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from campusai.llm.client import LLMResponseError
from evaluation.phase8.prepare_product_run import prepare


class _Answer:
    def to_dict(self):
        return {"answer": "preflight only", "citations": [], "abstained": True}

    def to_public_dict(self):
        return {"answer": "preflight only", "citations": [], "abstained": True}


class _Service:
    def __init__(self, llm):
        self.cache = SimpleNamespace(close=lambda: None)
        self.retriever = SimpleNamespace(query_cache_size=32, last_trace=None)
        self.answer_generator = SimpleNamespace(llm=llm)
        self.last_retrieval = []
        self.ask_count = 0

    def ask(self, question, **_options):
        self.ask_count += 1
        try:
            self.answer_generator.llm.generate_json(
                f"Answer only from evidence for: {question}", schema={"type": "object"})
        except LLMResponseError:
            pass
        return _Answer()


class _Application:
    def __init__(self, llm):
        self.query_service = _Service(llm)

    def query(self, question, **options):
        answer = self.query_service.ask(question, **options)
        return {"ok": True, "answer": answer.to_public_dict()}

    def close(self):
        return None


def test_phase8_preflight_captures_exact_prompt_and_sends_zero_requests(tmp_path, monkeypatch):
    benchmark = tmp_path / "benchmark.jsonl"
    benchmark.write_text(json.dumps({
        "qid": "q-1", "question": "How many credits?", "answerable": True,
        "split": "test", "tags": ["table"], "doc_ids": ["doc-1"], "filters": {},
    }) + "\n", encoding="utf-8")
    index = tmp_path / "index"
    index.mkdir()
    (index / "doc-1").mkdir()
    (index / "doc-1" / "dense.json").write_text(
        json.dumps({"items": [{"doc_id": "doc-1", "chunk_id": "c1"}]}), encoding="utf-8")
    (index / "manifest.json").write_text(json.dumps({"documents": ["doc-1"]}), encoding="utf-8")
    llm_config = tmp_path / "product.yaml"
    llm_config.write_text("llm: {}\n", encoding="utf-8")
    packet_path = tmp_path / "preflight.json"
    holder = {}

    def factory():
        # serve.create_llm is patched by prepare to return the offline recorder.
        from scripts.operations.serve import create_llm
        llm = create_llm()
        holder["llm"] = llm
        return _Application(llm)

    def deny_network(*_args, **_kwargs):
        raise AssertionError("preflight must never use network transport")

    monkeypatch.setattr("urllib.request.urlopen", deny_network)
    packet = prepare(benchmark_path=benchmark, index_dir=index, llm_config=llm_config,
                     packet_path=packet_path, app_factory=factory)

    assert packet["provider_requests_sent"] == 0
    assert packet["external_egress"] is False
    assert packet["provider_call_count_estimate"] == 1
    assert packet["cases"][0]["planned_provider_call"] is True
    assert packet["cases"][0]["prompt"] == "Answer only from evidence for: How many credits?"
    assert packet["cases"][0]["prompt_sha256"] == hashlib.sha256(
        packet["cases"][0]["prompt"].encode("utf-8")).hexdigest()
    assert packet["cases"][0]["schema"] == {"type": "object"}
    assert json.loads(packet_path.read_text(encoding="utf-8"))["cases"] == packet["cases"]
    assert len(holder["llm"].prompts) == 1


def test_phase8_preflight_refuses_to_overwrite_a_packet(tmp_path):
    packet = tmp_path / "already-exists.json"
    packet.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        prepare(packet_path=packet)
