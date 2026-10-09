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

        await reg.resolve(ev["request_id"], "allow", caller_user_id="u_test")

    dec = await bridge_permission(
        reg,
        emit_sse,
        tool_name="conda_remove",
        reason="\u7834\u574f\u6027\u64cd\u4f5c\u9700\u7528\u6237\u786e\u8ba4",
        timeout_s=1.0,
        user_id="u_test",
    )
    assert emitted[0]["type"] == "control_request"
    assert emitted[0]["tool_name"] == "conda_remove"
    assert "request_id" in emitted[0]
    assert dec is PermissionDecision.ALLOW


async def test_timeout_defaults_to_deny_safe():

    reg = PendingPermissionRegistry()

    async def emit_sse(ev: dict) -> None:
        pass

    dec = await bridge_permission(
        reg,
        emit_sse,
        tool_name="x",
        reason="r",
        timeout_s=0.05,
        user_id="u_test",
    )
    assert dec is PermissionDecision.DENY


async def test_user_deny_resolves_deny():
    reg = PendingPermissionRegistry()

    async def emit_sse(ev: dict) -> None:
        await reg.resolve(ev["request_id"], "deny", caller_user_id="u_test")

    dec = await bridge_permission(
        reg,
        emit_sse,
        tool_name="x",
        reason="r",
        timeout_s=1.0,
        user_id="u_test",
    )
    assert dec is PermissionDecision.DENY


async def test_cancel_request_clears_pending():

    reg = PendingPermissionRegistry()
    rid = reg.register(user_id="u_test")
    assert reg.is_pending(rid) is True
    reg.cancel(rid)
    assert reg.is_pending(rid) is False

    assert await reg.resolve(rid, "allow", caller_user_id="u_test") == "not_found"


async def test_unknown_request_id_resolve_is_noop():
    reg = PendingPermissionRegistry()

    assert await reg.resolve("nonexistent", "allow", caller_user_id="u_test") == "not_found"


async def test_concurrent_requests_isolated_by_id():

    reg = PendingPermissionRegistry()
    results: dict[str, str] = {}

    async def flow(tag: str, answer: str) -> None:
        async def emit(ev: dict) -> None:
            await reg.resolve(ev["request_id"], answer, caller_user_id=f"u_{tag}")

        d = await bridge_permission(reg, emit, tool_name=tag, reason="r", timeout_s=1.0, user_id=f"u_{tag}")
        results[tag] = d.value

    await asyncio.gather(flow("a", "allow"), flow("b", "deny"))
    assert results == {"a": "allow", "b": "deny"}
