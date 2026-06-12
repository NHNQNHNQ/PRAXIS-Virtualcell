"""审报告(夸大/违规/漏不确定性/rejected 写成 used)→ 只出 notes+flags,不改 prediction。"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你审查虚拟细胞预测报告的诚实性。检查:是否把 rejected 模型写成 used、是否夸大、"
    "是否漏报不确定性、是否 abstain 却仍给了预测。只输出 JSON:"
    '{"notes":[],"flags":[]}。flags 用简短英文标签。只输出 JSON。'
)


class LLMCriticAgent(BaseAgent):
    name = "LLMCritic"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        report = message.payload["report"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(report, ensure_ascii=False)}],
            json_mode=True)
        out = {"notes": [], "flags": []}
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                out["notes"] = list(d.get("notes") or [])
                out["flags"] = list(d.get("flags") or [])
            except json.JSONDecodeError:
                out["flags"] = ["llm_parse_failed"]
        else:
            out["flags"] = ["llm_unavailable"]
        bus.send(AgentMessage(message.message_id + ":llmcrit", self.name, "client",
            "llm_critic_notes", out, message.timestamp, message.message_id))
