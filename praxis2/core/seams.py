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

    reason: str | None = None


@dataclass
class StopDecision:
    veto: bool
    message: str = ""


class PermissionPolicy(ABC):
    @abstractmethod
    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult: ...

    async def acheck(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:

        return self.check(tool=tool, payload=payload, state=state)


class AllowAllPermission(PermissionPolicy):
    def check(self, *, tool: Any, payload: dict, state: State) -> PermissionResult:
        return PermissionResult(PermissionDecision.ALLOW)


#   PostToolUse: (tool, block: dict, result: dict, state: State) -> dict | None

PreToolUseHook = Callable[[dict, State], None]
PostToolUseHook = Callable[[Any, dict, dict, State], "dict | None"]


class Compactor(Protocol):
    async def compact(self, state: State) -> None: ...


def _block_ids(msg: dict, kind: str, id_key: str) -> set[str]:
    c = msg.get("content")
    if not isinstance(c, list):
        return set()
    return {b[id_key] for b in c if isinstance(b, dict) and b.get("type") == kind and id_key in b}


class MinimalCompactor:
    async def compact(self, state: State) -> None:

        msgs = state.messages
        if len(msgs) <= 2:
            return
        keep = msgs[len(msgs) // 2 :]

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
            keep = msgs[-1:]
        state.messages = keep
        state.transition = "reactive_compact"
