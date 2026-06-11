"""Phase A.6:bridge_permission 接入 SerialToolRunner;ASK 走 SSE bridge 不裸过。

reviewer M6 C3 Critical:`SerialToolRunner` 默认 AllowAllPermission,
`PendingPermissionRegistry`+`bridge_permission` 整套是死代码。

本测试覆盖:
- BridgePermissionAdapter.acheck:ASK → 经 bridge_permission 解析(allow / timeout-deny)
- BridgePermissionAdapter.check:ASK 安全降级为 DENY(不裸过)
- PermissionPolicy 基类默认 acheck:转 sync check(0 回归既有 AllowAllPermission/RulePermissionPolicy)
"""

import asyncio

from praxis2.core.seams import AllowAllPermission, PermissionDecision, PermissionResult
from praxis2.core.state import State
from praxis2.server.permission_bridge import (
    BridgePermissionAdapter,
    PendingPermissionRegistry,
)


class _AskPolicy:
    """base policy:总返 ASK,用以触发 bridge。"""

    def check(self, *, tool, payload, state):
        return PermissionResult(PermissionDecision.ASK, reason="测试 ASK")


class _DenyPolicy:
    """base policy:总返 DENY,验 adapter 不走 bridge。"""

    def check(self, *, tool, payload, state):
        return PermissionResult(PermissionDecision.DENY, reason="测试 DENY")


async def test_adapter_acheck_non_ask_does_not_invoke_bridge():
    """A.6 fixup I1:base 返 DENY(非 ASK)→ adapter 透传,不 emit SSE 也不占 registry。

    锁住"非 ASK 不走 bridge"不变量:防 adapter 误把所有决策都过 bridge,
    导致非交互式 DENY/ALLOW 也走 SSE control_request → 性能/SSE 噪声双输。
    """
    reg = PendingPermissionRegistry()
    events: list[dict] = []

    async def emit(ev: dict) -> None:
        events.append(ev)

    adapter = BridgePermissionAdapter(
        _DenyPolicy(), registry=reg, emit_sse=emit, user_id="u1", timeout_s=2.0
    )
    dec = await adapter.acheck(tool=None, payload={}, state=State())

    assert dec.decision is PermissionDecision.DENY
    assert events == [], f"非 ASK 不应 emit SSE,实际 {events}"
    # registry._pending 是私有,但测试访问合理(锁住"不注册"不变量)
    assert reg._pending == {}, f"非 ASK 不应注册 pending,实际 {reg._pending}"


async def test_adapter_acheck_ask_resolves_via_bridge_allow():
    """ASK 走 bridge,模拟用户 allow → 返 ALLOW。"""
    reg = PendingPermissionRegistry()
    events: list[dict] = []

    async def emit(ev: dict) -> None:
        events.append(ev)

    adapter = BridgePermissionAdapter(
        _AskPolicy(), registry=reg, emit_sse=emit, user_id="u1", timeout_s=2.0
    )

    async def user_resolves_after_emit() -> None:
        # 等 emit 推 control_request,然后用 owner 身份 resolve
        await asyncio.sleep(0.05)
        rid = events[0]["request_id"]
        await reg.resolve(rid, "allow", caller_user_id="u1")

    resolver_task = asyncio.create_task(user_resolves_after_emit())
    dec = await adapter.acheck(tool=None, payload={}, state=State())
    await resolver_task

    assert dec.decision is PermissionDecision.ALLOW
    assert events[0]["type"] == "control_request"


async def test_adapter_acheck_ask_timeout_denies():
    """ASK 超时无回应 → DENY(§7.6.2 安全默认)。"""
    reg = PendingPermissionRegistry()

    async def emit(ev: dict) -> None:
        pass

    adapter = BridgePermissionAdapter(
        _AskPolicy(), registry=reg, emit_sse=emit, user_id="u1", timeout_s=0.1
    )
    dec = await adapter.acheck(tool=None, payload={}, state=State())
    assert dec.decision is PermissionDecision.DENY


def test_adapter_sync_check_demotes_ask_to_deny():
    """sync check 路径下 ASK 安全降级 DENY(不裸过)。"""
    reg = PendingPermissionRegistry()

    async def emit(ev: dict) -> None:
        pass

    adapter = BridgePermissionAdapter(
        _AskPolicy(), registry=reg, emit_sse=emit, user_id="u1"
    )
    dec = adapter.check(tool=None, payload={}, state=State())
    assert dec.decision is PermissionDecision.DENY


def test_default_acheck_returns_check_result_for_allow_all():
    """既有 AllowAllPermission 应继承 PermissionPolicy 默认 acheck,sync 等价。"""
    p = AllowAllPermission()
    # 既有 sync check 仍工作
    res = p.check(tool=None, payload={}, state=State())
    assert res.decision is PermissionDecision.ALLOW
    # 新 acheck 默认调 check
    ares = asyncio.run(p.acheck(tool=None, payload={}, state=State()))
    assert ares.decision is PermissionDecision.ALLOW


async def test_adapter_timeout_configurable_via_settings():
    """A.6 fixup I2:settings.permission_ask_timeout_s 改了,adapter 真用新值(非硬编码)。

    用极短 timeout(0.01s)走 ASK 路径,无人 resolve → 必超时 DENY。
    若 adapter 还是硬编码 60.0,本测试要等 60s 才能拿到 DENY → 5s 内拿到 DENY 即证生效。
    """
    reg = PendingPermissionRegistry()

    async def emit(ev: dict) -> None:
        pass

    adapter = BridgePermissionAdapter(
        _AskPolicy(),
        registry=reg,
        emit_sse=emit,
        user_id="u1",
        timeout_s=0.01,  # 来自 settings.permission_ask_timeout_s
    )
    # 5s 看门狗:若硬编码 60s 这里会超时 → 测试失败 → 即证 adapter 仍硬编码
    dec = await asyncio.wait_for(
        adapter.acheck(tool=None, payload={}, state=State()), timeout=5.0
    )
    assert dec.decision is PermissionDecision.DENY


def test_rule_policy_acheck_inherits_default():
    """RulePermissionPolicy 同样继承默认 acheck。"""
    from praxis2.tools.permission import Rule, RuleAction, RulePermissionPolicy

    pol = RulePermissionPolicy([Rule(action=RuleAction.DENY, tool_prefix="bash")])

    class _T:
        name = "bash"

    res = asyncio.run(pol.acheck(tool=_T(), payload={}, state=State()))
    assert res.decision is PermissionDecision.DENY
