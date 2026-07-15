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
                rec, exc = d.get("recommended_agents"), d.get("excluded_agents")
                rf = d.get("risk_flags")
                # C3 全入口结构守卫:只接受 list(非 list 丢弃置 [],绝不把字符串逐字符拆 ——
                # "AB" 会被拆成 ['A','B'],候选名恰好命中单字符时静默注入垃圾 agent 名);
                # 捕获 TypeError/AttributeError(JSON 顶层非 object、值为标量)防畸形/注入产物崩溃。
                # 做法与 llm_orchestration/safety_contract.py 一致 —— 该文件复刻本 agent 的过滤逻辑时
                # 已修此 fail-closed 漏洞但未回填原件,本 task 回填。
                sug["recommended_agents"] = [a for a in (rec if isinstance(rec, list) else [])
                                             if a in candidates]
                sug["excluded_agents"] = [a for a in (exc if isinstance(exc, list) else [])
                                          if a in candidates]
                sug["reasoning_summary"] = str(d.get("reasoning_summary", ""))[:500]
                # C4 元素级白名单(recommended/excluded_agents 无需改 —— `if a in candidates`
                # 是值白名单,candidates 是 list → `in` 用 == 不需 hash,天然安全)。
                sug["risk_flags"] = [f for f in rf if isinstance(f, str)] if isinstance(rf, list) else []
            # C4 修正 11:回填 RecursionError(同 llm_critic.py:43,机械枚举 7 处之一)。
            except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
                sug["risk_flags"] = ["llm_parse_failed"]
        else:
            sug["risk_flags"] = ["llm_unavailable"]
        conflict = bool(set(sug["excluded_agents"]) & set(p.get("applicable", [])))
        bus.send(AgentMessage(message.message_id + ":llmroute", self.name, "client",
            "llm_route_suggestion", {"suggestion": sug, "conflict_with_rule": conflict},
            message.timestamp, message.message_id))
