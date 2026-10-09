import asyncio

from praxis2.core.seams import PermissionDecision
from praxis2.server.permission_bridge import (
    PendingPermissionRegistry,
    bridge_permission,
)


async def test_control_request_emitted_and_user_decision_resolves():
    reg = PendingPermissionRegistry()
    emitted: list[dict] = []

    async def emit_sse(ev: dict) -> None:
        emitted.append(ev)
        # 模拟前端 HTTP POST 回传 allow(A.5:resolve 需 caller_user_id)
        await reg.resolve(ev["request_id"], "allow", caller_user_id="u_test")

    dec = await bridge_permission(
        reg, emit_sse, tool_name="conda_remove",
        reason="破坏性操作需用户确认", timeout_s=1.0,
        user_id="u_test",
    )
    assert emitted[0]["type"] == "control_request"
    assert emitted[0]["tool_name"] == "conda_remove"
    assert "request_id" in emitted[0]
    assert dec is PermissionDecision.ALLOW


async def test_timeout_defaults_to_deny_safe():
    # 用户 N 秒不回 → 自动 deny(安全默认,§7.6.2)
    reg = PendingPermissionRegistry()

    async def emit_sse(ev: dict) -> None:
        pass  # 不回传 → 必超时

    dec = await bridge_permission(
        reg, emit_sse, tool_name="x", reason="r", timeout_s=0.05,
        user_id="u_test",
    )
    assert dec is PermissionDecision.DENY


async def test_user_deny_resolves_deny():
    reg = PendingPermissionRegistry()

    async def emit_sse(ev: dict) -> None:
        await reg.resolve(ev["request_id"], "deny", caller_user_id="u_test")

    dec = await bridge_permission(
        reg, emit_sse, tool_name="x", reason="r", timeout_s=1.0,
        user_id="u_test",
    )
    assert dec is PermissionDecision.DENY


async def test_cancel_request_clears_pending():
    # control_cancel_request:清理待处理权限(§7.6.3)
    reg = PendingPermissionRegistry()
    rid = reg.register(user_id="u_test")
    assert reg.is_pending(rid) is True
    reg.cancel(rid)
    assert reg.is_pending(rid) is False
    # 已取消的再 resolve 不抛(幂等,防重复回传崩);未知 rid → not_found
    assert await reg.resolve(rid, "allow", caller_user_id="u_test") == "not_found"


async def test_unknown_request_id_resolve_is_noop():
    reg = PendingPermissionRegistry()
    # 不存在的 rid → "not_found"(不抛,handler 据此发 404)
    assert await reg.resolve("nonexistent", "allow", caller_user_id="u_test") == "not_found"


async def test_concurrent_requests_isolated_by_id():
    # 多并发权限请求按 request_id 隔离,互不串
    reg = PendingPermissionRegistry()
    results: dict[str, str] = {}

    async def flow(tag: str, answer: str) -> None:
        async def emit(ev: dict) -> None:
            await reg.resolve(ev["request_id"], answer, caller_user_id=f"u_{tag}")

        d = await bridge_permission(reg, emit, tool_name=tag,
                                    reason="r", timeout_s=1.0,
                                    user_id=f"u_{tag}")
        results[tag] = d.value

    await asyncio.gather(flow("a", "allow"), flow("b", "deny"))
    assert results == {"a": "allow", "b": "deny"}
