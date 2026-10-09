import inspect
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from praxis2.core.state import State


class HookEvent(StrEnum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_SAMPLING = "PostSampling"
    PRE_COMPACT = "PreCompact"
    STOP = "Stop"
    SESSION_START = "SessionStart"


class HookBehavior(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class HookDecision:
    behavior: HookBehavior
    message: str = ""
    updated_input: dict | None = None


HookFn = Callable[[dict, State], Any]


class HookManager:
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
        except Exception:  # noqa: BLE001
            return HookDecision(HookBehavior.ALLOW)
        if isinstance(r, HookDecision):
            return r
        return HookDecision(HookBehavior.ALLOW)

    async def fire(self, event: HookEvent, payload: dict, state: State) -> HookDecision:
        last = HookDecision(HookBehavior.ALLOW)
        cur = dict(payload)
        any_modified = False
        for fn in self._hooks[event]:
            d = await self._run_one(fn, cur, state)
            if d.behavior is HookBehavior.DENY:
                return d
            if d.behavior is HookBehavior.ASK:
                return d
            if d.updated_input is not None:
                cur = d.updated_input
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

    def _wrapped(payload: dict, state: State) -> HookDecision:
        replaced = m3_hook(tool, payload.get("blk", {}), result, state)
        if replaced is None:
            return HookDecision(HookBehavior.ALLOW)
        return HookDecision(HookBehavior.DENY, message=str(replaced.get("content", "")))

    return _wrapped


def stop_decision_adapter(
    m3_gate: Callable[[State], Any],
) -> HookFn:

    def _wrapped(payload: dict, state: State) -> HookDecision:
        dec = m3_gate(state)
        if getattr(dec, "veto", False):
            return HookDecision(HookBehavior.DENY, message=getattr(dec, "message", ""))
        return HookDecision(HookBehavior.ALLOW)

    return _wrapped
