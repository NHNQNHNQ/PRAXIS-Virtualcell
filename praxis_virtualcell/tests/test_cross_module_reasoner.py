"""Tests for cross module reasoner."""
import json

from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration.cross_module_reasoner import LLMCrossModuleReasoner


class FakeLLMClient:
    def __init__(self, content):
        self.enabled = True
        self._content = content

    def complete(self, messages, *, json_mode=False, max_tokens=1024):
        return {"disabled": False, "content": self._content, "error": None}


_PLAN = {"species": "human", "primary": "genetic_hub", "secondary": ["stress_processor"],
         "overall_verdict": "accept",
         "entries": [{"module": "genetic_hub", "role": "primary", "verdict": "accept"},
                     {"module": "stress_processor", "role": "secondary", "verdict": "accept"}],
         "notes": []}


def _run(content):
    bus = MessageBus()
    LLMCrossModuleReasoner(FakeLLMClient(content)).handle(AgentMessage(
        message_id="c1", sender="Report", receiver="LLMCrossModuleReasoner",
        message_type="cross_module_review", payload={"module_plan": _PLAN}, timestamp="t1"), bus)
    return bus.latest("llm_cross_module_notes")


def test_emits_notes_and_flags_only():
    msg = _run(json.dumps({"notes": ["genetic_hub and stress form a reasonable combination"], "flags": []}))
    assert msg.message_type == "llm_cross_module_notes"
    assert set(msg.payload) == {"notes", "flags"}
    assert msg.payload["notes"] == ["genetic_hub and stress form a reasonable combination"]


def test_does_not_mutate_module_plan():
    """Verify does not mutate module plan."""
    before = json.dumps(_PLAN, sort_keys=True)
    _run(json.dumps({"notes": ["x"], "flags": ["y"]}))
    assert json.dumps(_PLAN, sort_keys=True) == before


def test_empty_content_flags_unavailable():
    msg = _run(None)
    assert "llm_unavailable" in msg.payload["flags"]


def test_bad_json_flags_parse_failed():
    msg = _run("not json{")
    assert "llm_parse_failed" in msg.payload["flags"]
