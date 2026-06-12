"""optional LLM agents 占位:offline/无 key 时 should_run()=False,被 runtime 跳过。
W3 才真实现 LLMInputInterpreter/LLMRouter/LLMCritic/LLMReport。"""
from __future__ import annotations

from praxis_virtualcell.agents_llm.llm_client import LLMClient


class _OptionalLLMAgent:
    name = "OptionalLLMAgent"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def should_run(self) -> bool:
        return self.client.enabled


class LLMInputInterpreterAgent(_OptionalLLMAgent):
    name = "LLMInputInterpreter"


class LLMRouterAgent(_OptionalLLMAgent):
    name = "LLMRouter"


class LLMCriticAgent(_OptionalLLMAgent):
    name = "LLMCritic"


class LLMReportAgent(_OptionalLLMAgent):
    name = "LLMReport"
