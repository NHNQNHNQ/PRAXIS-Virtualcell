"""完整 HookManager:多态返回协议 + 多 hook 遇 deny 短路 + 6 事件分发
(总纲 §7.6.1)。M3 builtin.py 的 PostToolUse dict|None / Stop StopDecision
经 adapter 并入本协议(§5④ 三不变量零回归,类比 M5 把 M4 前置接口接成真实落点)。

hook 可同步或 async;hook 内部异常被隔离按 ALLOW 跳过(宁松勿崩——
科学严谨由 deny hook 主动表达,异常不应静默变 deny 卡死主循环,§7.6.1
hook 链要有异常处理)。多个 hook 按注册(定义)顺序执行,遇 deny 立即返回。"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from praxis2.core.state import State


class HookEvent(StrEnum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_SAMPLING = "PostSampling"  # 模型出完整 assistant、提取 tool_use 前
    PRE_COMPACT = "PreCompact"
    STOP = "Stop"
    SESSION_START = "SessionStart"  # §7.4.4 resume 重跑


class HookBehavior(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"  # 触发用户交互(远程走 §7.6.2)


@dataclass
class HookDecision:
    """§7.6.1 多态返回对象(非 bool)。
    deny → 不执行 + 生成 rejection,模型可重试(message 写为何否决+满足条件);
    allow + updated_input → 用修改后输入执行(RMCP 合规修正点);
    ask → 触发用户交互(message 为请求文本,远程桥接 §7.6.2)。"""

    behavior: HookBehavior
    message: str = ""
    updated_input: dict | None = None


# hook 签名:(payload: dict, state: State) -> HookDecision | (await ...)
HookFn = Callable[[dict, State], Any]


class HookManager:
    """按事件分发;每事件 hook 列表按注册顺序执行,遇 deny 短路。
    无 hook → 默认 ALLOW。"""

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[HookFn]] = {e: [] for e in HookEvent}

    def register(self, event: HookEvent, fn: HookFn) -> None:
        self._hooks[event].append(fn)

    @staticmethod
    async def _run_one(fn: HookFn, payload: dict, state: State) -> HookDecision:
        try:
            r = fn(payload, state)
            if inspect.isawaitable(r):
                r = await r
        except Exception:  # noqa: BLE001 - hook 异常隔离,不崩主循环(§7.6.1)
            return HookDecision(HookBehavior.ALLOW)
        if isinstance(r, HookDecision):
            return r
        return HookDecision(HookBehavior.ALLOW)  # 兜底:非法返回视为放行

    async def fire(
        self, event: HookEvent, payload: dict, state: State
    ) -> HookDecision:
        last = HookDecision(HookBehavior.ALLOW)
        cur = dict(payload)
        any_modified = False
        for fn in self._hooks[event]:
            d = await self._run_one(fn, cur, state)
            if d.behavior is HookBehavior.DENY:
                return d  # 遇 deny 立即返回不再跑后续(§7.6.1)
            if d.behavior is HookBehavior.ASK:
                return d  # ask 同样短路(交远程桥接)
            if d.updated_input is not None:
                cur = d.updated_input  # allow+updated_input 串到下一 hook
                any_modified = True
        if any_modified:
            last = HookDecision(HookBehavior.ALLOW, updated_input=cur)
        return last


def post_tool_use_adapter(
    m3_hook: Callable[[Any, dict, dict, State], "dict | None"],
    *,
    tool: Any,
    result: dict,
) -> HookFn:
    """把 M3 builtin PostToolUse(返回 dict|None)并入新协议(§5④#2 零回归):
    None → ALLOW(放行原 result);dict(替换为 is_error result)→ DENY
    (message 取替换 result 的 content,即 hook 写给模型的*为何否决*+*满足条件*)。
    payload 须含 'blk'(tool_use 块);tool/result 经闭包绑定(M3 hook 四参签名)。"""

    def _wrapped(payload: dict, state: State) -> HookDecision:
        replaced = m3_hook(tool, payload.get("blk", {}), result, state)
        if replaced is None:
            return HookDecision(HookBehavior.ALLOW)
        return HookDecision(
            HookBehavior.DENY, message=str(replaced.get("content", ""))
        )

    return _wrapped


def stop_decision_adapter(
    m3_gate: Callable[[State], Any],
) -> HookFn:
    """把 M3 Stop hook(返回 StopDecision(veto,message))并入新协议(§5④#3
    零回归):veto=True → DENY(message 透传:为何否决+满足条件);
    veto=False → ALLOW。Stop 事件 payload 不使用(gate 只读 state)。"""

    def _wrapped(payload: dict, state: State) -> HookDecision:
        dec = m3_gate(state)
        if getattr(dec, "veto", False):
            return HookDecision(
                HookBehavior.DENY, message=getattr(dec, "message", "")
            )
        return HookDecision(HookBehavior.ALLOW)

    return _wrapped
