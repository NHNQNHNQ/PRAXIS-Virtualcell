"""出路由建议(只建议,不裁决)。只能从候选里选;emit llm_route_suggestion。"""
from __future__ import annotations

import json

from praxis_virtualcell.agents_llm.llm_client import LLMClient
from praxis_virtualcell.core.agent import BaseAgent
from praxis_virtualcell.core.bus import MessageBus
from praxis_virtualcell.core.message import AgentMessage

_SYS = (
    "你给虚拟细胞预测的模型路由建议。只输出 JSON:"
    '{"recommended_agents":[],"excluded_agents":[],"reasoning_summary":"","risk_flags":[]}。'
    "agent 名必须来自给定 candidates,不要发明新名字。只输出 JSON。"
)


class LLMRouterAgent(BaseAgent):
    name = "LLMRouter"

    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def handle(self, message: AgentMessage, bus: MessageBus) -> None:
        p = message.payload
        candidates = list(p.get("applicable", [])) + list(p.get("rejected_candidates", []))
        user = json.dumps({"request": p.get("request"), "candidates": candidates,
                           "rule_applicable": p.get("applicable")}, ensure_ascii=False)
        res = self.client.complete(
            [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
            json_mode=True)
        sug = {"recommended_agents": [], "excluded_agents": [],
               "reasoning_summary": "", "risk_flags": []}
        if res.get("content"):
            try:
                d = json.loads(res["content"])
                sug["recommended_agents"] = [a for a in (d.get("recommended_agents") or []) if a in candidates]
                sug["excluded_agents"] = [a for a in (d.get("excluded_agents") or []) if a in candidates]
                sug["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]
                sug["risk_flags"] = list(d.get("risk_flags") or [])
            except json.JSONDecodeError:
                sug["risk_flags"] = ["llm_parse_failed"]
        else:
            sug["risk_flags"] = ["llm_unavailable"]
        conflict = bool(set(sug["excluded_agents"]) & set(p.get("applicable", [])))
        bus.send(AgentMessage(message.message_id + ":llmroute", self.name, "client",
            "llm_route_suggestion", {"suggestion": sug, "conflict_with_rule": conflict},
            message.timestamp, message.message_id))
