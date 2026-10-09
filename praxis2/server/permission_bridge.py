"""Bridge asynchronous approval requests into the generic permission gate."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

from praxis2.core.seams import PermissionDecision, PermissionPolicy, PermissionResult

_ANSWER_TO_DECISION = {
    "allow": PermissionDecision.ALLOW,
    "deny": PermissionDecision.DENY,
    "ask": PermissionDecision.ASK,
}


class ResolveResult(StrEnum):
    OK = "ok"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"


@dataclass
class _PendingEntry:
    future: asyncio.Future
    user_id: str


class PendingPermissionRegistry:
    def __init__(self) -> None:
        self._pending: dict[str, _PendingEntry] = {}

    def register(self, *, user_id: str) -> str:

        rid = uuid.uuid4().hex
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = _PendingEntry(future=fut, user_id=user_id)
        return rid

    def is_pending(self, rid: str) -> bool:
        return rid in self._pending

    async def resolve(self, rid: str, answer: str, *, caller_user_id: str) -> ResolveResult:

        entry = self._pending.get(rid)
        if entry is None:
            return ResolveResult.NOT_FOUND
        if entry.user_id != caller_user_id:
            return ResolveResult.FORBIDDEN
        if not entry.future.done():
            entry.future.set_result(answer)
        return ResolveResult.OK

    def cancel(self, rid: str) -> None:

        entry = self._pending.pop(rid, None)
        if entry is not None and not entry.future.done():
            entry.future.cancel()

    async def wait(self, rid: str, *, timeout_s: float) -> str:
        entry = self._pending[rid]
        try:
            return await asyncio.wait_for(asyncio.shield(entry.future), timeout_s)
        finally:
            self._pending.pop(rid, None)


async def bridge_permission(
    reg: PendingPermissionRegistry,
    emit_sse: Callable[[dict], Awaitable[None]],
    *,
    tool_name: str,
    reason: str,
    timeout_s: float,
    user_id: str,
) -> PermissionDecision:

    rid = reg.register(user_id=user_id)
    await emit_sse(
        {
            "type": "control_request",
            "request_id": rid,
            "tool_name": tool_name,
            "reason": reason,
        }
    )
    try:
        answer = await reg.wait(rid, timeout_s=timeout_s)
    except (TimeoutError, asyncio.CancelledError):
        return PermissionDecision.DENY
    return _ANSWER_TO_DECISION.get(answer, PermissionDecision.DENY)


class BridgePermissionAdapter(PermissionPolicy):
    def __init__(
        self,
        base: PermissionPolicy,
        *,
        registry: PendingPermissionRegistry,
        emit_sse: Callable[[dict], Awaitable[None]],
        user_id: str,
        timeout_s: float = 60.0,
    ) -> None:
        self._base = base
        self._registry = registry
        self._emit = emit_sse
        self._user_id = user_id
        self._timeout = timeout_s

    def check(self, *, tool, payload, state) -> PermissionResult:

        base_dec = self._base.check(tool=tool, payload=payload, state=state)
        if base_dec.decision is PermissionDecision.ASK:
            return PermissionResult(
                PermissionDecision.DENY,
                reason="ASK requires asynchronous acheck; synchronous checks deny by default",
            )
        return base_dec

    async def acheck(self, *, tool, payload, state) -> PermissionResult:
        base_dec = self._base.check(tool=tool, payload=payload, state=state)
        if base_dec.decision is not PermissionDecision.ASK:
            return base_dec
        tool_name = getattr(tool, "name", str(tool))
        final = await bridge_permission(
            self._registry,
            self._emit,
            tool_name=tool_name,
            reason=base_dec.reason or "User approval required",
            timeout_s=self._timeout,
            user_id=self._user_id,
        )
        return PermissionResult(final, reason=base_dec.reason)
