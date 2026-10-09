"""LLMModulePlanner(Phase 4,进 message bus):复刻 LLMRouter 的"只能从候选选"。

收 module_plan_request({request(raw), module_support, mismatch_queries})→ 归一 → 建候选全集
(safety_contract.build_candidate_modules)→ 调 LLM 出 module 集 → sanitize_llm_plan 过滤成
候选子集(fail-closed)→ emit module_candidates_llm 交 ModuleRouter 用 Phase 3 代码合成 ModulePlan。

铁律:LLM 只挑合法 module 集(不产 ModulePlan、不设 engine/verdict/prediction);越候选剔除;
LLM 失败回退保底含 primary。assert_llm_boundaries 三 flag 恒 False 由入口守卫,LLM 产物只进
候选过滤 + 后续 provenance notes,不碰 prediction/hard-rule。
"""
from __future__ import annotations

import json

from praxis_virtualcell.agents import module_rules
from praxis_virtualcell.agents.species_schema import normalize_request
from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage
from praxis_virtualcell.llm_orchestration import safety_contract as SC

_SYS = (
    "你给虚拟细胞的生物功能模块编排建议。只输出 JSON:"
    '{"selected_modules":[],"reasoning_summary":"","risk_flags":[]}。'
    "selected_modules 里的模块名必须来自给定 candidates,不要发明新模块名、不要选 candidates 外的。"
    "你只挑选相关模块,不决定引擎、不给数值预测、不改裁决。只输出 JSON。"
)


class LLMModulePlanner(BaseAgent):
    name = "LLMModulePlanner"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        raw = message.payload["request"]
        req = normalize_request(raw)
        module_support = message.payload.get("module_support", {})
        mismatch_queries = message.payload.get("mismatch_queries", {})
        primary = module_rules.pick_primary(req)
        candidates = SC.build_candidate_modules(req, module_support)

        user = json.dumps({"request": raw, "candidates": candidates,
                           "deterministic_primary": primary}, ensure_ascii=False)
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
            json_mode=True)
        mc = SC.sanitize_llm_plan(res.get("content"), candidates, primary=primary)
        mc["selected"] = mc.pop("selected_modules")   # 对外键名 selected
        bus.send(AgentMessage(
            message_id=message.message_id + ":mcllm",
            sender=self.name, receiver="ModuleRouterAgent",
            message_type="module_candidates_llm",
            payload={"request": raw, "module_support": module_support,
                     "mismatch_queries": mismatch_queries, "module_candidates": mc},
            timestamp=message.timestamp, parent_message_id=message.message_id))
