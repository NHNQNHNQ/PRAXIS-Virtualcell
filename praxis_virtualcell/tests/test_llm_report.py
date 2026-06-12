import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_report import LLMReportAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_report_narrative_nonempty_for_abstain():
    bus = MessageBus()
    report = {"request_id": "r1", "abstain": True, "reliability": "low",
              "prediction": None, "models_used": [], "models_rejected": ["MockCPA"],
              "abstain_reasons": ["all_predictors_rejected"], "provenance": {"n_messages": 12}}
    LLMReportAgent(_client()).handle(
        AgentMessage("m1", "Report", "LLMReport", "llm_render", {"report": report}, "t1"), bus)
    narrative = bus.latest("llm_narrative").payload["narrative"]
    assert isinstance(narrative, str) and len(narrative) > 0
