from praxis2.core.seams import StopDecision
from praxis2.core.state import State
from praxis2.hooks.manager import (
    HookBehavior,
    HookDecision,
    HookEvent,
    HookManager,
    post_tool_use_adapter,
    stop_decision_adapter,
)


def test_hook_event_has_six_events():
    # §7.6.1 完整事件集
    assert {e.value for e in HookEvent} == {
        "PreToolUse", "PostToolUse", "PostSampling",
        "PreCompact", "Stop", "SessionStart",
    }


async def test_allow_default_when_no_hooks():
    m = HookManager()
    d = await m.fire(HookEvent.PRE_TOOL_USE, {}, State())
    assert d.behavior is HookBehavior.ALLOW


async def test_hooks_run_in_definition_order_and_deny_short_circuits():
    calls: list[str] = []

    def h1(payload, state):
        calls.append("h1")
        return HookDecision(HookBehavior.ALLOW)

    def h2(payload, state):
        calls.append("h2")
        return HookDecision(HookBehavior.DENY, message="h2 拒绝:缺前置")

    def h3(payload, state):
        calls.append("h3")  # 不应被调用(h2 deny 短路)
        return HookDecision(HookBehavior.ALLOW)

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, h1)
    m.register(HookEvent.PRE_TOOL_USE, h2)
    m.register(HookEvent.PRE_TOOL_USE, h3)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {"name": "x"}, State())
    assert d.behavior is HookBehavior.DENY
    assert d.message == "h2 拒绝:缺前置"
    assert calls == ["h1", "h2"]  # h3 未跑(遇 deny 立即返回)


async def test_allow_with_updated_input_carries_through():
    def fix(payload, state):
        return HookDecision(
            HookBehavior.ALLOW, updated_input={**payload, "fixed": True}
        )

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, fix)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {"a": 1}, State())
    assert d.behavior is HookBehavior.ALLOW
    assert d.updated_input == {"a": 1, "fixed": True}


async def test_ask_behavior_returned_for_remote_bridge():
    def need_user(payload, state):
        return HookDecision(HookBehavior.ASK, message="需用户确认破坏性操作")

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, need_user)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {}, State())
    assert d.behavior is HookBehavior.ASK
    assert "确认" in d.message


async def test_async_hook_supported():
    async def ah(payload, state):
        return HookDecision(HookBehavior.DENY, message="async deny")

    m = HookManager()
    m.register(HookEvent.STOP, ah)
    d = await m.fire(HookEvent.STOP, {}, State())
    assert d.behavior is HookBehavior.DENY


async def test_hook_exception_isolated_does_not_crash_chain():
    def boom(payload, state):
        raise RuntimeError("hook 内部炸了")

    def ok(payload, state):
        return HookDecision(HookBehavior.ALLOW)

    m = HookManager()
    m.register(HookEvent.POST_SAMPLING, boom)
    m.register(HookEvent.POST_SAMPLING, ok)
    # 异常 hook 不得让主循环崩(§7.6.1 hook 链要有异常处理);
    # 异常按 allow 跳过(宁松勿崩,科学严谨由 deny hook 主动表达)
    d = await m.fire(HookEvent.POST_SAMPLING, {}, State())
    assert d.behavior is HookBehavior.ALLOW


async def test_m3_post_tool_use_adapter_zero_regression():
    # M3 builtin PostToolUse 返回 dict|None:None=放行,dict=替换为 is_error result。
    # adapter 并入新协议:None→ALLOW;dict→DENY(message 取替换 result 的 content)
    from praxis2.hooks.builtin import doi_required

    state = State()
    ok_result = {"type": "tool_result", "tool_use_id": "t1",
                 "is_error": False, "content": "结论 doi:10.1/x"}
    bad_result = {"type": "tool_result", "tool_use_id": "t2",
                  "is_error": False, "content": "结论无溯源"}
    allow_hook = post_tool_use_adapter(doi_required, tool=None, result=ok_result)
    deny_hook = post_tool_use_adapter(doi_required, tool=None, result=bad_result)
    da = await HookManager._run_one(allow_hook, {"blk": {}}, state)
    dd = await HookManager._run_one(deny_hook, {"blk": {}}, state)
    assert da.behavior is HookBehavior.ALLOW
    assert dd.behavior is HookBehavior.DENY
    assert "DOI" in dd.message or "doi" in dd.message.lower()


async def test_m3_stop_decision_adapter_zero_regression():
    # M3 Stop 返回 StopDecision(veto,message):veto=True→DENY,False→ALLOW
    def veto_gate(state):
        return StopDecision(veto=True, message="证据链不完整")

    def pass_gate(state):
        return StopDecision(veto=False)

    m = HookManager()
    m.register(HookEvent.STOP, stop_decision_adapter(veto_gate))
    d = await m.fire(HookEvent.STOP, {}, State())
    assert d.behavior is HookBehavior.DENY and d.message == "证据链不完整"

    m2 = HookManager()
    m2.register(HookEvent.STOP, stop_decision_adapter(pass_gate))
    d2 = await m2.fire(HookEvent.STOP, {}, State())
    assert d2.behavior is HookBehavior.ALLOW


async def test_two_allow_hooks_updated_input_chains():
    # ALLOW+updated_input 串联:第二个 hook 看到的 payload 是第一个的输出
    def add_a(payload, state):
        return HookDecision(HookBehavior.ALLOW, updated_input={**payload, "a": 1})

    seen: list[dict] = []

    def add_b(payload, state):
        seen.append(dict(payload))
        return HookDecision(HookBehavior.ALLOW, updated_input={**payload, "b": 2})

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, add_a)
    m.register(HookEvent.PRE_TOOL_USE, add_b)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {"x": 0}, State())
    assert d.behavior is HookBehavior.ALLOW
    assert d.updated_input == {"x": 0, "a": 1, "b": 2}
    assert seen == [{"x": 0, "a": 1}]  # 第二个看到第一个的输出


async def test_hooks_isolated_per_event():
    # 6 事件分发独立:注册到 A 事件的 hook 不会在 fire(B) 时被调用
    pre_calls: list[str] = []
    post_calls: list[str] = []

    def pre_h(payload, state):
        pre_calls.append("pre")
        return HookDecision(HookBehavior.ALLOW)

    def post_h(payload, state):
        post_calls.append("post")
        return HookDecision(HookBehavior.ALLOW)

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, pre_h)
    m.register(HookEvent.POST_TOOL_USE, post_h)
    await m.fire(HookEvent.SESSION_START, {}, State())  # 既未注册 → 都不跑
    assert pre_calls == [] and post_calls == []
    await m.fire(HookEvent.PRE_TOOL_USE, {}, State())
    assert pre_calls == ["pre"] and post_calls == []
    await m.fire(HookEvent.POST_SAMPLING, {}, State())  # 不同事件 → pre 不再跑
    assert pre_calls == ["pre"] and post_calls == []
    await m.fire(HookEvent.POST_TOOL_USE, {}, State())
    assert pre_calls == ["pre"] and post_calls == ["post"]
