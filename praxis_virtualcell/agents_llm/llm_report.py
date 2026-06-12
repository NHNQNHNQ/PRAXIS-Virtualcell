"""结构化报告 → 中文 NL 叙述。忠实保留 abstain/参与/拒绝/reliability/provenance,不编造。"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你把结构化的虚拟细胞预测报告改写成简洁中文科研叙述。必须忠实保留:是否 abstain、"
    "用了/拒了哪些模型、reliability、provenance 要点;不得编造报告里没有的预测数值或结论。"
    "只输出叙述文本,不要输出 JSON。"
)


class LLMReportAgent(BaseAgent):
    name = "LLMReport"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload["report"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(report, ensure_ascii=False)}],
            max_tokens=800)
        narrative = res.get("content") or ""
        bus.send(AgentMessage(message.message_id + ":llmrep", self.name, "client",
            "llm_narrative", {"narrative": narrative}, message.timestamp, message.message_id))
