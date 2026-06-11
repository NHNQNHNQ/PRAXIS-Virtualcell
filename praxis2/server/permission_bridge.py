"""§7.6.2 远程权限桥接(SSE 场景必做)。

权限决策不能在前端做(前端不可信):后端生成 control_request → SSE
推前端弹窗 → 用户选择 → 前端 HTTP POST 回传 → 后端在 hook 中应用。
超时处理:用户 N 秒不回 → 自动 deny(安全默认,§7.6.2)。

M6 第一版内存 PendingPermissionRegistry(key=request_id)+ asyncio
Future + wait_for 超时。跨 worker Redis 版接口位标 integration
(总纲校准④);合成消息/tool_stub fallback v2(第一版工具均本地注册)。

**Phase A.5(reviewer M6 C4)**:rid → (future, user_id) 强绑定。
register(*, user_id) 必传 owner;resolve(*, caller_user_id) 跨 tenant 返 "forbidden",
未知/过期 rid 返 "not_found",owner 自己 resolve 返 "ok"。handler 据此发 401/403/404/200。
"""

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
    """resolve() 返回值的枚举(防 handler 拼写错走 200)。

    StrEnum 自动与 str 等价(`ResolveResult.OK == "ok"` is True),所以
    旧测试中的字面量比较仍能过;handler 端应改用枚举成员比较。
    """

    OK = "ok"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"


@dataclass
class _PendingEntry:
    """rid → future + owner user_id(A.5 tenant 绑定)。"""

    future: asyncio.Future
    user_id: str


class PendingPermissionRegistry:
    """待处理权限注册表(内存,key=request_id)。register 产 Future + 绑 owner user_id,
    resolve 由 HTTP 回传喂答案(需 caller_user_id 校验 owner),cancel 清理。
    跨 worker 时经 Redis(§11.4 pub/sub 同源),接口位标 integration。

    A.5(reviewer M6 C4):未绑 user_id 导致跨 tenant 可 resolve;现强绑。
    """

    def __init__(self) -> None:
        self._pending: dict[str, _PendingEntry] = {}

    def register(self, *, user_id: str) -> str:
        """必须在 async 上下文调用(get_running_loop;Py3.14+ deprecation 收紧)。

        A.5:user_id 必传(keyword-only),作为 owner 用于 resolve 时的 tenant 校验。
        """
        rid = uuid.uuid4().hex
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = _PendingEntry(future=fut, user_id=user_id)
        return rid

    def is_pending(self, rid: str) -> bool:
        return rid in self._pending

    async def resolve(
        self, rid: str, answer: str, *, caller_user_id: str
    ) -> ResolveResult:
        """HTTP 回传写答案,带 tenant 校验。

        返回 ResolveResult 枚举(给 handler 直接映射 HTTP 状态):
        - ResolveResult.NOT_FOUND:rid 不存在(未注册/已过期/已 cancel)
        - ResolveResult.FORBIDDEN:rid 存在但 owner != caller_user_id(跨 tenant 攻击)
        - ResolveResult.OK:owner 匹配,future 已 set_result(若未 done)

        StrEnum 兼容 str,旧字面量比较(== "ok" 等)仍可工作;新代码应
        使用枚举成员防 typo 静默走错路径(reviewer A.5 fixup I1)。
        """
        entry = self._pending.get(rid)
        if entry is None:
            return ResolveResult.NOT_FOUND
        if entry.user_id != caller_user_id:
            return ResolveResult.FORBIDDEN
        if not entry.future.done():
            entry.future.set_result(answer)
        return ResolveResult.OK

    def cancel(self, rid: str) -> None:
        """control_cancel_request:清理待处理权限(§7.6.3)。

        后端发起,不需要 owner 校验。
        """
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
    """ASK → 生成 control_request → SSE 推前端 → 等回传 → 决策。
    超时默认 deny(安全:用户 N 秒未响应不放行破坏性操作,§7.6.2)。

    A.5:user_id 必传,透传到 reg.register(user_id=...) 实现 tenant 绑定。
    A.6 将在 SerialToolRunner 接入时由调用方透传 session.user_id;
    当前 5 处测试调用直接传 "u_test" 等,生产侧 wire 见 Task A.6。
    """
    rid = reg.register(user_id=user_id)
    await emit_sse({
        "type": "control_request", "request_id": rid,
        "tool_name": tool_name, "reason": reason,
    })
    try:
        answer = await reg.wait(rid, timeout_s=timeout_s)
    except (TimeoutError, asyncio.CancelledError):
        return PermissionDecision.DENY  # 超时/取消 → 安全默认拒绝
    return _ANSWER_TO_DECISION.get(answer, PermissionDecision.DENY)


class BridgePermissionAdapter(PermissionPolicy):
    """A.6(reviewer M6 C3):包装 base PermissionPolicy,把 ASK 决策接出 SSE bridge。

    `acheck`:base 决策非 ASK 直接返;ASK 时 → bridge_permission 发 SSE
    control_request → 等用户回传 → 映射成 ALLOW/DENY。
    `check`:sync 路径下无法 await,故 ASK 安全降级为 DENY(防意外裸过)。

    本 adapter 由 `_chat_stream` 在每个流式请求内注入:base 是用户/管理员策略,
    registry / emit_sse / user_id 来自当前 HTTP scope。SerialToolRunner 调 acheck。

    Known caveat(B.1 前):当前 SSE 链路 buffered(收齐再吐),control_request
    不会在 ASK 期间到达前端 → bridge 必超时 DENY。本里程碑只完成 wire;
    真端到端 ASK 体验留 B.1 接流式后。
    """

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
        """sync fast-path(仅用于 ABC 契约;runner 走 acheck)。
        ASK 在 sync 路径无 bridge 可走 → 降级 DENY,确保不裸过。"""
        base_dec = self._base.check(tool=tool, payload=payload, state=state)
        if base_dec.decision is PermissionDecision.ASK:
            return PermissionResult(
                PermissionDecision.DENY,
                reason="ASK 需 async acheck;sync 路径下安全降级为 DENY",
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
            reason=base_dec.reason or "需用户授权",
            timeout_s=self._timeout,
            user_id=self._user_id,
        )
        return PermissionResult(final, reason=base_dec.reason)
