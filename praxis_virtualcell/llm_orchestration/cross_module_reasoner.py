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
                notes, flags = d.get("notes"), d.get("flags")
                # C3 结构守卫(opus 终审补漏,复刻 llm_critic.py 同一手法):只接受 list
                # (非 list 丢弃置 [],绝不把字符串逐字符拆成 ['d','a','n',...] 污染 provenance);
                # 捕获 TypeError/AttributeError(JSON 顶层非 object、值为标量)防畸形/注入产物
                # 崩掉 core/runtime.py 的同步 _dispatch_collect 调用。
                # C4 元素级白名单(同 llm_critic.py):容器守了、元素没守。
                out["notes"] = [n for n in notes if isinstance(n, str)] if isinstance(notes, list) else []
                out["flags"] = [f for f in flags if isinstance(f, str)] if isinstance(flags, list) else []
            except (json.JSONDecodeError, TypeError, AttributeError):
                out["flags"] = ["llm_parse_failed"]
        else:
            out["flags"] = ["llm_unavailable"]
        bus.send(AgentMessage(
            message_id=message.message_id + ":xmod",
            sender=self.name, receiver="client",
            message_type="llm_cross_module_notes", payload=out,
            timestamp=message.timestamp, parent_message_id=message.message_id))
