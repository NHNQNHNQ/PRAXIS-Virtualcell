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
                notes, flags = d.get("notes"), d.get("flags")
                # C3 结构守卫:只接受 list(非 list 丢弃置 [],绝不把字符串逐字符拆成
                # ['d','a','n',...] 污染 provenance);捕获 TypeError/AttributeError
                # (JSON 顶层非 object、值为标量)防畸形/注入产物污染 provenance。
                # 本 agent 产物只进 provenance 不碰裁决,守卫仅保结构合法、不改语义。
                # C4 元素级白名单:C3 只守了容器(notes 是不是 list),没守元素 ——
                # [{'evil':1},['nested'],None] 原样进 provenance。只接受 str,其余丢弃。
                out["notes"] = [n for n in notes if isinstance(n, str)] if isinstance(notes, list) else []
                out["flags"] = [f for f in flags if isinstance(f, str)] if isinstance(flags, list) else []
            # C4 修正 11:回填 RecursionError(深嵌套 JSON → json.loads 抛,它是 RuntimeError
            # 子类、不在前三者继承链上)。同型缺口机械枚举共 7 处,本处为回填的 5 处之一 ——
            # 穿透后经 core/runtime.py:44 `agent.handle(...)`(该处无 try/except)→ CLI 崩
            # traceback(cli.py 全文无 try/except)/ `/api/jobs` 降级 400。
            except (json.JSONDecodeError, TypeError, AttributeError, RecursionError):
                out["flags"] = ["llm_parse_failed"]
        else:
            out["flags"] = ["llm_unavailable"]
        bus.send(AgentMessage(message.message_id + ":llmcrit", self.name, "client",
            "llm_critic_notes", out, message.timestamp, message.message_id))
