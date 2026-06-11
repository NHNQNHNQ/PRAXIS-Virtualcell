"""学习闭环抽取(总纲 §7.4.2)。M4 落地:抽取逻辑 + 候选 append-only 写
_candidate 区 + 幂等。真 fork「只有指定写权限的 subagent」沙箱留 M5
(agents/ 设施 M5 才建);未审候选只对本会话可见、不进大脑检索(检索 M5 接)。"""

import json
from dataclasses import dataclass

from praxis2.store.base import Namespace, Store

# 公开契约:review.py 跨模块 import 用(候选 KV key 前缀);
# 与 M3 PHASE_KEY 同体例——跨模块共享常量取 public 名,勿用前导下划线
CAND_PREFIX = "_candidate/"


@dataclass
class ExtractCandidate:
    id: str
    text: str
    trigger: str  # tool_failure | phase_failure | token_threshold | manual


def extract_candidates(
    transcript: list[dict], *, trigger: str
) -> list[ExtractCandidate]:
    """M4 第一版规则式抽取:失败点(is_error tool_result)各产一条候选。
    完整 fork-subagent 摘要 M5 接 AgentTool 时替换本规则实现。"""
    out: list[ExtractCandidate] = []
    n = 0
    for m in transcript:
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if (isinstance(b, dict) and b.get("type") == "tool_result"
                    and b.get("is_error")):
                n += 1
                out.append(ExtractCandidate(
                    id=f"{trigger}-{n}", trigger=trigger,
                    text=f"失败经验:{b.get('content', '')}",
                ))
    return out


async def persist_candidates(
    store: Store, ns: Namespace, cands: list[ExtractCandidate]
) -> None:
    """候选 append-only 写 _candidate 区;同 id 幂等(不重复入队)。
    同时注册 _cand_index 供 review.list_pending 枚举(meta_upsert 幂等)。"""
    for c in cands:
        key = CAND_PREFIX + c.id
        if await store.kv_get(ns, key) is not None:
            continue  # 幂等
        await store.kv_set(ns, key, json.dumps(
            {"id": c.id, "text": c.text, "trigger": c.trigger},
            ensure_ascii=False).encode())
        await store.meta_upsert("_cand_index", {
            "user_id": ns.user_id, "pk": c.id, "ns_scope": ns.scope})
