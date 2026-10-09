import asyncio

from praxis2.core.seams import AllowAllPermission, PermissionDecision, PermissionResult
from praxis2.core.state import State
from praxis2.server.permission_bridge import (
    BridgePermissionAdapter,
    PendingPermissionRegistry,
)


class _AskPolicy:
    def check(self, *, tool, payload, state):
        return PermissionResult(PermissionDecision.ASK, reason="\u6d4b\u8bd5 ASK")


class _DenyPolicy:
    def check(self, *, tool, payload, state):
        return PermissionResult(PermissionDecision.DENY, reason="\u6d4b\u8bd5 DENY")


async def test_adapter_acheck_non_ask_does_not_invoke_bridge():

    reg = PendingPermissionRegistry()
    events: list[dict] = []

    async def emit(ev: dict) -> None:
        events.append(ev)

    adapter = BridgePermissionAdapter(_DenyPolicy(), registry=reg, emit_sse=emit, user_id="u1", timeout_s=2.0)
    dec = await adapter.acheck(tool=None, payload={}, state=State())

    assert dec.decision is PermissionDecision.DENY
    assert events == [], f"Non-ASK decisions must not emit approval events; observed {events}"

    assert reg._pending == {}, f"Non-ASK decisions must not create pending approvals; observed {reg._pending}"


async def test_adapter_acheck_ask_resolves_via_bridge_allow():

    reg = PendingPermissionRegistry()
    events: list[dict] = []

    async def emit(ev: dict) -> None:
        events.append(ev)

    adapter = BridgePermissionAdapter(_AskPolicy(), registry=reg, emit_sse=emit, user_id="u1", timeout_s=2.0)

    async def user_resolves_after_emit() -> None:

        await asyncio.sleep(0.05)
        rid = events[0]["request_id"]
        await reg.resolve(rid, "allow", caller_user_id="u1")

    resolver_task = asyncio.create_task(user_resolves_after_emit())
    dec = await adapter.acheck(tool=None, payload={}, state=State())
    await resolver_task

    assert dec.decision is PermissionDecision.ALLOW
    assert events[0]["type"] == "control_request"


async def test_adapter_acheck_ask_timeout_denies():

    reg = PendingPermissionRegistry()

    async def emit(ev: dict) -> None:
        pass

    adapter = BridgePermissionAdapter(_AskPolicy(), registry=reg, emit_sse=emit, user_id="u1", timeout_s=0.1)
    dec = await adapter.acheck(tool=None, payload={}, state=State())
    assert dec.decision is PermissionDecision.DENY


def test_adapter_sync_check_demotes_ask_to_deny():

    reg = PendingPermissionRegistry()

    async def emit(ev: dict) -> None:
        pass

    adapter = BridgePermissionAdapter(_AskPolicy(), registry=reg, emit_sse=emit, user_id="u1")
    dec = adapter.check(tool=None, payload={}, state=State())
    assert dec.decision is PermissionDecision.DENY


def test_default_acheck_returns_check_result_for_allow_all():

    p = AllowAllPermission()

    res = p.check(tool=None, payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW

    ares = asyncio.run(p.acheck(tool=None, payload={}, state=State()))
    assert ares.decision is PermissionDecision.ALLOW


async def test_adapter_timeout_configurable_via_settings():

    reg = PendingPermissionRegistry()

    async def emit(ev: dict) -> None:
        pass

    adapter = BridgePermissionAdapter(
        _AskPolicy(),
        registry=reg,
        emit_sse=emit,
        user_id="u1",
        timeout_s=0.01,
    )

    dec = await asyncio.wait_for(adapter.acheck(tool=None, payload={}, state=State()), timeout=5.0)
    assert dec.decision is PermissionDecision.DENY


def test_rule_policy_acheck_inherits_default():

    from praxis2.tools.permission import Rule, RuleAction, RulePermissionPolicy

    pol = RulePermissionPolicy([Rule(action=RuleAction.DENY, tool_prefix="bash")])

    class _T:
        name = "bash"

    res = asyncio.run(pol.acheck(tool=_T(), payload={}, state=State()))
    assert res.decision is PermissionDecision.DENY
