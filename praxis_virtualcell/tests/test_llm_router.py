import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_router import LLMRouterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_router_suggestion_subset_of_candidates():
    bus = MessageBus()
    payload = {"request": {"species": "human", "perturbation_targets": ["AHR"],
                           "task_type": "predict_delta_expression"},
               "brain_context": {}, "applicable": ["MockCPA", "MockGEARS"],
               "rejected_candidates": ["MockLinear"]}
    LLMRouterAgent(_client()).handle(
        AgentMessage("m1", "ModelApplicability", "LLMRouter", "route_suggest", payload, "t1"), bus)
    s = bus.latest("llm_route_suggestion").payload["suggestion"]
    cands = {"MockCPA", "MockGEARS", "MockLinear"}
    assert set(s["recommended_agents"]) <= cands
    assert set(s["excluded_agents"]) <= cands
