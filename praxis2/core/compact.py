"""Compact 四策略 + ★API 不变量(总纲 §7.4.5)。
★最关键:切断点绝不切在 tool_use 与其 tool_result 之间,否则 API 报
orphaned tool_result、会话卡死。autoCompact/microCompact 第一版必做;
apiMicrocompact/sessionMemoryCompact 标接口位(v2,§7.4.5 原文即 v2 优化)。"""

import json
from typing import Any


def _ids(msg: dict, kind: str, id_key: str) -> set[str]:
    c = msg.get("content")
    if not isinstance(c, list):
        return set()
    return {b[id_key] for b in c if isinstance(b, dict)
            and b.get("type") == kind and id_key in b}


def adjust_index_to_preserve_api_invariants(msgs: list[dict], cut: int) -> int:
    """§7.4.5★:把 cut 向前移到保留段(msgs[cut:])无孤儿 tool_result 的最小下标。
    向前扫保留段所有 tool_result id,把对应 tool_use 所在轮一并纳入保留。

    注:本函数仅单向防 orphaned tool_result(tool_result→tool_use 方向)。反向
    orphaned tool_use(其 tool_result 在被压段)不由本函数也不由 boundary 兜底,
    而是上游 M1 持久化不变量(总纲 §7.1.3:query() tool_use 轮与对应 tool_result
    成对相邻落盘)保证前向切点下相邻对同保留/同压,结构上不产生 orphaned tool_use。
    全链路双向 API 安全 = 本函数 + M1 相邻对落盘(详见总纲 §7.4.5★ 诚实边界)。"""
    if cut <= 0 or cut >= len(msgs):
        return cut
    while cut > 0:
        kept = msgs[cut:]
        tu: set[str] = set()
        for m in kept:
            tu |= _ids(m, "tool_use", "id")
        orphan = False
        for m in kept:
            if not _ids(m, "tool_result", "tool_use_id") <= tu:
                orphan = True
                break
        if not orphan:
            return cut
        cut -= 1  # 含更早的 tool_use 轮,继续回退直到无孤儿
    return cut


_CB_THRESHOLD = 3  # 连续失败熔断阈值(§7.4.5 熔断器)


def reinject_pinned(state: Any, summary: str, *, cut: int) -> None:
    """§7.4.5/§12.3 post-compact 重注:pinned 原始任务 + boundary 摘要 +
    msgs[cut:]。cut 已由 adjust_index_to_preserve_api_invariants 防 orphaned
    tool_result;orphaned tool_use 方向由上游 M1 相邻对落盘(§7.1.3)结构性
    杜绝,非本函数 boundary 兜底。RMCP 相位在 state.tool_use_context 不动、
    天然不丢。original_task_idx 已在保留段(>=cut)则不重复 pin。"""
    msgs = state.messages
    pinned = []
    if (
        state.original_task_idx is not None
        and 0 <= state.original_task_idx < cut
    ):
        pinned = [msgs[state.original_task_idx]]
    boundary = {"role": "user",
                "content": [{"type": "text", "text": f"【前段摘要】{summary}"}]}
    state.messages = pinned + [boundary] + msgs[cut:]


class AutoCompactor:
    """§7.4.5 autoCompact:调 API 把前段总结成一条 boundary message。
    async(Compactor 缝已异步化,总纲 §7.4.5 校准)。带熔断 + PTL 防御。
    切点经 adjust_index_to_preserve_api_invariants 防 orphaned tool_result;
    orphaned tool_use 方向由上游 M1 相邻对落盘(§7.1.3)结构性杜绝,非
    boundary 兜底(双向安全见总纲 §7.4.5★ 诚实边界)。"""

    def __init__(self, client: Any, settings: Any) -> None:
        self._client = client
        self._s = settings

    async def _summarize(self, msgs: list[dict]) -> str:
        parts: list[str] = []
        async for ev in self._client.stream_messages(
            model=self._s.model,
            messages=[{"role": "user", "content":
                       f"用 3 句话总结以下对话的关键状态:\n"
                       f"{json.dumps(msgs, ensure_ascii=False)}"}],
            max_tokens=self._s.max_tokens,
            system="你是上下文压缩器,只输出关键状态摘要。",
            tools=None,
        ):
            if ev["type"] == "text":
                parts.append(ev["text"])
        return "".join(parts).strip()

    async def _summarize_ptl_safe(self, hist: list[dict]) -> str:
        """§7.4.5 PTL 防御:首次总结失败(请求本身太长等)→ 截断历史取后半
        重试一次。两次都失败则向上抛(由 compact 计熔断)。"""
        try:
            s = await self._summarize(hist)
            if not s:
                raise RuntimeError("空摘要")
            return s
        except Exception:  # noqa: BLE001 - PTL 防御:截断后半重试一次(§7.4.5)
            s = await self._summarize(hist[len(hist) // 2:])
            if not s:
                raise RuntimeError("空摘要") from None
            return s

    async def compact(self, state: Any) -> None:
        track = state.auto_compact_tracking
        if track.get("consecutive_failures", 0) >= _CB_THRESHOLD:
            return  # 熔断:放弃压缩,原样返回(§7.4.5 熔断器)
        keep = getattr(self._s, "compact_keep_recent", 2)
        n = len(state.messages)
        # 初始切点 = 保留最近 keep 条;经 §7.4.5★ 不变量回退,绝不切断 tool 对
        cut = adjust_index_to_preserve_api_invariants(
            state.messages, max(0, n - keep)
        )
        if cut <= 0:
            return  # 无可压缩段(全保留),不调 API
        try:
            summary = await self._summarize_ptl_safe(state.messages[:cut])
        except Exception:  # noqa: BLE001 - PTL 重试仍失败 → 计熔断,不中断主循环
            track["consecutive_failures"] = track.get("consecutive_failures", 0) + 1
            return
        track["consecutive_failures"] = 0
        reinject_pinned(state, summary, cut=cut)
        state.transition = "auto_compact_done"


class MicroCompactor:
    """§7.4.5 microCompact 基础版:不调 API,本地清过期 tool_result 内容,
    保结构(块/ tool_use_id 保留 → 不破 API invariant),留占位符。
    apiMicrocompact(Anthropic 原生 context management clear 老 thinking/tool)
    与 sessionMemoryCompact(用 Session Memory 省 token,无则回退 autoCompact)
    为 v2 优化(总纲 §7.4.5 原文),M4 仅标接口位见下方注释,不实现。"""

    def __init__(self, *, max_age_turns: int) -> None:
        self._max_age = max_age_turns

    def compact_local(self, state: Any) -> None:
        msgs = state.messages
        # 一轮约 assistant+user 两条;cutoff<=0 时全历史在最近范围,循环 no-op
        cutoff = len(msgs) - self._max_age * 2
        for i, m in enumerate(msgs):
            if i >= cutoff or m.get("role") != "user":
                continue
            c = m.get("content")
            if not isinstance(c, list):
                continue
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    b["content"] = "[old result cleared]"  # 保结构清内容
        state.transition = "micro_compact_done"

    # --- v2 接口位(总纲 §7.4.5,M4 不实现)---
    # def api_microcompact(self, state): ...      # Anthropic 原生 context mgmt
    # def session_memory_compact(self, state): ...  # 无 session memory 时回退 autoCompact
