"""LLMCrossModuleReasoner(Phase 4,进 message bus):复刻 LLMCritic 的 advisory 模式。

收 cross_module_review({module_plan})→ 调 LLM → emit llm_cross_module_notes({notes, flags})。
只做跨模块一致性/生物学合理性的自然语言复核(可解释层),绝不改任何 entry/verdict/prediction
(决策 P4,红线 2)。写进 report.provenance.llm_cross_module_notes(接管线时)。
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你复核虚拟细胞的模块编排计划(ModulePlan)的跨模块一致性与生物学合理性。"
    "检查:primary/secondary 组合是否合理、是否有模块冲突、是否遗漏明显相关模块。"
    "你只给出观察和风险标记,不修改计划、不改裁决、不给数值预测。只输出 JSON:"
    '{"notes":[],"flags":[]}。flags 用简短英文标签。只输出 JSON。'
)


class LLMCrossModuleReasoner(BaseAgent):
    name = "LLMCrossModuleReasoner"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        module_plan = message.payload["module_plan"]
        res = self.client.complete(
            [{"role": "system", "content": _SYS},
             {"role": "user", "content": json.dumps(module_plan, ensure_ascii=False)}],
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
        bus.send(AgentMessage(
            message_id=message.message_id + ":xmod",
            sender=self.name, receiver="client",
            message_type="llm_cross_module_notes", payload=out,
            timestamp=message.timestamp, parent_message_id=message.message_id))
