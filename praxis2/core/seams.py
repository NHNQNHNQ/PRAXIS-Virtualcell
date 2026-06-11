"""query() 的三类注入缝。M1 给 no-op / 最小 stub,后续里程碑替换:
- PermissionPolicy → M3 相位感知策略(§7.3.5/§7.3.7)
- PreToolUse / PostToolUse hook → M3 DOI/证据链、M5 大脑诊断注入(§4②)
- Compactor → M4 core/compact.py 四策略 + adjust_index_to_preserve_api_invariants(§7.4.5)
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum  # ruff UP042 + py311
from typing import Any, Protocol

from praxis2.core.state import State


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionResult:
    decision: PermissionDecision
    # deny/ask 时:为何拒 + 需先满足什么(§7.3.7,让模型自己去补 retrieve 而非停下问人)
    reason: str | None = None


@dataclass
class StopDecision:
    """§7.6.1 Stop hook 注入缝契约:veto=True 则 query() 注入 message
    (为何否决+满足条件)强制再走一轮(§5④#3)。放 core 防 core→hooks 反向依赖。"""

    veto: bool
    message: str = ""


class PermissionPolicy(ABC):
    """A.6 reviewer M6 C3:由 Protocol 改 ABC,以提供 `acheck` 默认实现
    (Protocol 不支持非空默认方法体)。runtime 影响:具体策略须显式继承本类;
    SerialToolRunner 调 `await self._permission.acheck(...)`,
    既有同步策略经默认 acheck 透传(0 回归)。
    """

    @abstractmethod
    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult: ...

    async def acheck(
        self, *, tool: Any, payload: dict, state: State
    ) -> PermissionResult:
        """默认 async 实现:转 sync check;需要真异步(如 SSE bridge)的策略覆写。"""
        return self.check(tool=tool, payload=payload, state=state)


class AllowAllPermission(PermissionPolicy):
    """M1 默认全放行。M3 用相位感知策略替换(retrieve 未完成则拒 execute 类)。"""

    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        return PermissionResult(PermissionDecision.ALLOW)


# Hook 签名(M1 默认空列表):
#   PreToolUse:  (block: dict, state: State) -> None        —— M3 接入
#   PostToolUse: (tool, block: dict, result: dict, state: State) -> dict | None
#               返回非 None 则替换 result(M5 在此把大脑诊断写进 diagnostics)
PreToolUseHook = Callable[[dict, State], None]
PostToolUseHook = Callable[[Any, dict, dict, State], "dict | None"]


class Compactor(Protocol):
    async def compact(self, state: State) -> None: ...  # M4 起异步(autoCompact 调 API)


def _block_ids(msg: dict, kind: str, id_key: str) -> set[str]:
    c = msg.get("content")
    if not isinstance(c, list):
        return set()
    return {
        b[id_key]
        for b in c
        if isinstance(b, dict) and b.get("type") == kind and id_key in b
    }


class MinimalCompactor:
    """M1 最小压缩:保留后半段历史,且绝不让保留段出现"孤儿 tool_result"
    (其 tool_use 在被丢弃段)。这只是让 reactive-compact 恢复路径可端到端测试的
    最小正确实现;M4 用 core/compact.py 的四策略 + 真正的
    adjust_index_to_preserve_api_invariants 替换(§7.4.5★)。"""

    async def compact(self, state: State) -> None:
        # async 仅满足 Compactor Protocol 契约;体内纯本地裁剪,无 await
        msgs = state.messages
        if len(msgs) <= 2:
            return  # 太短无意义:有意 no-op 且不动 transition(调用方 Task8 自管 transition)
        keep = msgs[len(msgs) // 2 :]
        # 向后顺延切点,直到保留段无孤儿 tool_result(对应 tool_use 也在保留段内)
        while keep:
            tu_ids: set[str] = set()
            for m in keep:
                tu_ids |= _block_ids(m, "tool_use", "id")
            orphan = False
            for m in keep:
                if not _block_ids(m, "tool_result", "tool_use_id") <= tu_ids:
                    orphan = True
                    break
            if not orphan:
                break
            keep = keep[1:]
        if not keep and msgs:
            keep = msgs[-1:]  # 保底:绝不把 messages 压成空(否则下轮 API 400)
        state.messages = keep
        state.transition = "reactive_compact"
