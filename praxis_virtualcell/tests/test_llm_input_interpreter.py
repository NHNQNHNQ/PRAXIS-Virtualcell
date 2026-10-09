import os

import pytest

from praxis_virtualcell.agents_llm.llm_client import make_llm_client
from praxis_virtualcell.agents_llm.llm_input_interpreter import LLMInputInterpreterAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.config import Mode, RuntimeConfig, load_env
from praxis_virtualcell.core.message import AgentMessage


def _client():
    load_env()
    return make_llm_client(RuntimeConfig(mode=Mode.LLM_ASSISTED,
                                         deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "")))


@pytest.mark.llm
def test_parses_chinese_experiment_description():
    bus = MessageBus()
    LLMInputInterpreterAgent(_client()).handle(
        AgentMessage("m1", "client", "LLMInputInterpreter", "parse_text",
                     {"text": "在 K562 细胞里敲除 AHR 基因,预测单细胞转录组变化"}, "t1"), bus)
    out = bus.latest("request_parsed")
    assert out is not None, "应解析成功 emit request_parsed"
    req = out.payload["request"]
    assert req["species"] == "human"
    assert "AHR" in [g.upper() for g in req["perturbation_targets"]]
    assert req["task_type"] == "predict_delta_expression"


@pytest.mark.llm
def test_garbage_input_falls_back():
    bus = MessageBus()
    LLMInputInterpreterAgent(_client()).handle(
        AgentMessage("m1", "client", "LLMInputInterpreter", "parse_text",
                     {"text": "今天天气怎么样"}, "t1"), bus)
    assert bus.latest("request_parsed") is not None or bus.latest("llm_input_failed") is not None
