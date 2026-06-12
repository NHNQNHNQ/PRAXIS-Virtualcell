import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_critic import LLMCriticAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_critic_returns_structured_notes():
    bus = MessageBus()
    report = {"abstain": False, "models_used": ["MockGEARS"],
              "models_rejected": ["MockGEARS"],  # 矛盾:既 used 又 rejected
              "prediction": {"delta": [0.9]}, "reliability": "high", "provenance": {}}
    LLMCriticAgent(_client()).handle(
        AgentMessage("m1", "Report", "LLMCritic", "llm_review", {"report": report}, "t1"), bus)
    out = bus.latest("llm_critic_notes").payload
    assert isinstance(out.get("notes"), list)
    assert isinstance(out.get("flags"), list)
    # LLM 不改 prediction:输入 report 对象未被修改
    assert report["prediction"] == {"delta": [0.9]}
