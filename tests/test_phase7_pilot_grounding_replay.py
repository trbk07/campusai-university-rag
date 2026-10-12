import pytest
from scripts.benchmarks.replay_phase7_pilot_grounding import CapturedFinalResponse


def test_replay_accepts_only_one_exact_captured_prompt():
    replay=CapturedFinalResponse('approved prompt','{"answer":"source answer"}')
    with pytest.raises(ValueError):replay.generate_json('different prompt')
    assert replay.generate_json('approved prompt')['answer']=='source answer'
    with pytest.raises(ValueError):replay.generate_json('approved prompt')
