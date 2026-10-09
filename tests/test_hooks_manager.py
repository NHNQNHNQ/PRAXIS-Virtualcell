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

    assert {e.value for e in HookEvent} == {
        "PreToolUse",
        "PostToolUse",
        "PostSampling",
        "PreCompact",
        "Stop",
        "SessionStart",
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
        return HookDecision(HookBehavior.DENY, message="h2 \u62d2\u7edd:\u7f3a\u524d\u7f6e")

    def h3(payload, state):
        calls.append("h3")
        return HookDecision(HookBehavior.ALLOW)

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, h1)
    m.register(HookEvent.PRE_TOOL_USE, h2)
    m.register(HookEvent.PRE_TOOL_USE, h3)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {"name": "x"}, State())
    assert d.behavior is HookBehavior.DENY
    assert d.message == "h2 \u62d2\u7edd:\u7f3a\u524d\u7f6e"
    assert calls == ["h1", "h2"]


async def test_allow_with_updated_input_carries_through():
    def fix(payload, state):
        return HookDecision(HookBehavior.ALLOW, updated_input={**payload, "fixed": True})

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, fix)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {"a": 1}, State())
    assert d.behavior is HookBehavior.ALLOW
    assert d.updated_input == {"a": 1, "fixed": True}


async def test_ask_behavior_returned_for_remote_bridge():
    def need_user(payload, state):
        return HookDecision(HookBehavior.ASK, message="\u9700\u7528\u6237\u786e\u8ba4\u7834\u574f\u6027\u64cd\u4f5c")

    m = HookManager()
    m.register(HookEvent.PRE_TOOL_USE, need_user)
    d = await m.fire(HookEvent.PRE_TOOL_USE, {}, State())
    assert d.behavior is HookBehavior.ASK
    assert "\u786e\u8ba4" in d.message


async def test_async_hook_supported():
    async def ah(payload, state):
        return HookDecision(HookBehavior.DENY, message="async deny")

    m = HookManager()
    m.register(HookEvent.STOP, ah)
    d = await m.fire(HookEvent.STOP, {}, State())
    assert d.behavior is HookBehavior.DENY


async def test_hook_exception_isolated_does_not_crash_chain():
    def boom(payload, state):
        raise RuntimeError("hook \u5185\u90e8\u70b8\u4e86")

    def ok(payload, state):
        return HookDecision(HookBehavior.ALLOW)

    m = HookManager()
    m.register(HookEvent.POST_SAMPLING, boom)
    m.register(HookEvent.POST_SAMPLING, ok)

    d = await m.fire(HookEvent.POST_SAMPLING, {}, State())
    assert d.behavior is HookBehavior.ALLOW


async def test_m3_post_tool_use_adapter_zero_regression():

    from praxis2.hooks.builtin import doi_required

    state = State()
    ok_result = {"type": "tool_result", "tool_use_id": "t1", "is_error": False, "content": "\u7ed3\u8bba doi:10.1/x"}
    bad_result = {
        "type": "tool_result",
        "tool_use_id": "t2",
        "is_error": False,
        "content": "\u7ed3\u8bba\u65e0\u6eaf\u6e90",
    }
    allow_hook = post_tool_use_adapter(doi_required, tool=None, result=ok_result)
    deny_hook = post_tool_use_adapter(doi_required, tool=None, result=bad_result)
    da = await HookManager._run_one(allow_hook, {"blk": {}}, state)
    dd = await HookManager._run_one(deny_hook, {"blk": {}}, state)
    assert da.behavior is HookBehavior.ALLOW
    assert dd.behavior is HookBehavior.DENY
    assert "DOI" in dd.message or "doi" in dd.message.lower()


async def test_m3_stop_decision_adapter_zero_regression():

    def veto_gate(state):
        return StopDecision(veto=True, message="Evidence chain is incomplete")

    def pass_gate(state):
        return StopDecision(veto=False)

    m = HookManager()
    m.register(HookEvent.STOP, stop_decision_adapter(veto_gate))
    d = await m.fire(HookEvent.STOP, {}, State())
    assert d.behavior is HookBehavior.DENY and d.message == "Evidence chain is incomplete"

    m2 = HookManager()
    m2.register(HookEvent.STOP, stop_decision_adapter(pass_gate))
    d2 = await m2.fire(HookEvent.STOP, {}, State())
    assert d2.behavior is HookBehavior.ALLOW


async def test_two_allow_hooks_updated_input_chains():

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
    assert seen == [{"x": 0, "a": 1}]


async def test_hooks_isolated_per_event():

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
    await m.fire(HookEvent.SESSION_START, {}, State())
    assert pre_calls == [] and post_calls == []
    await m.fire(HookEvent.PRE_TOOL_USE, {}, State())
    assert pre_calls == ["pre"] and post_calls == []
    await m.fire(HookEvent.POST_SAMPLING, {}, State())
    assert pre_calls == ["pre"] and post_calls == []
    await m.fire(HookEvent.POST_TOOL_USE, {}, State())
    assert pre_calls == ["pre"] and post_calls == ["post"]
