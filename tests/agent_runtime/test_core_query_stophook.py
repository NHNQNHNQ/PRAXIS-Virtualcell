from praxis2.core.query import query
from praxis2.core.seams import AllowAllPermission, MinimalCompactor, StopDecision
from praxis2.core.state import State, TerminalReason
from praxis2.hooks.builtin import make_rmcp_stop_gate
from praxis2.tools.registry import ToolRegistry
from praxis2.tools.runtools import SerialToolRunner
from ._llm_fakes import TURN_FINAL_TEXT, FakeLLMClient


def _settings():
    class S:
        model = "m"
        max_tokens = 64
        max_turns = 20
        recovery_budget = 3
        max_output_recovery = 2

    return S()


def _two_finals_client():
    return FakeLLMClient(turns=[TURN_FINAL_TEXT, TURN_FINAL_TEXT])


async def test_stop_hook_vetoes_then_forces_one_more_turn():
    # §5④#3:证据链不完整 → Stop hook 否决终答、强制再走一轮(B.4 后:每终答都校验)
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = _two_finals_client()
    st = State()
    st.messages = [{"role": "user", "content": "给结论"}]

    # 模拟"模型在中间轮补足证据链":首次 veto 后置 ctx,使第二次终答 hook 放行。
    # 这是 B.4 修复后的正确路径——前提是每终答都跑 hook,而非旧实现"首次后跳过"。
    real_gate = make_rmcp_stop_gate()

    def gate_with_recovery(state: State) -> StopDecision:
        dec = real_gate(state)
        if dec.veto:
            # veto 后 query() 会注入消息 + continue,下一轮模型给终答前置好 ctx
            state.tool_use_context["evidence_ok"] = True
            state.tool_use_context["anti_filter_ok"] = True
        return dec

    events = [
        e
        async for e in query(
            st, client=client, registry=reg, settings=_settings(),
            runner=runner, compactor=MinimalCompactor(),
            stop_hook=gate_with_recovery,
        )
    ]
    # 第一轮终答被否决:注入合成 user 消息 + 强制再走;第二轮放行(护栏)
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    injected = [m for m in st.messages if m["role"] == "user"
                and "RMCP 终态否决" in str(m["content"])]
    assert len(injected) == 1  # 恰注入一次否决反馈
    # B.4(reviewer M1 C2):放行后清原因集合(诊断字段),不再用 stop_hook_active 旗标
    assert st.pending_stop_reasons == []
    await client.aclose()


async def test_stop_hook_passes_when_evidence_ok():
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT])
    st = State()
    st.messages = [{"role": "user", "content": "给结论"}]
    st.tool_use_context["evidence_ok"] = True
    st.tool_use_context["anti_filter_ok"] = True
    events = [
        e
        async for e in query(
            st, client=client, registry=reg, settings=_settings(),
            runner=runner, compactor=MinimalCompactor(),
            stop_hook=make_rmcp_stop_gate(),
        )
    ]
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    assert not any("RMCP 终态否决" in str(m["content"]) for m in st.messages)
    await client.aclose()


async def test_stop_hook_rechecks_each_terminal_until_satisfied():
    """B.4(reviewer M1 C2):每终答都校验 stop_hook,跨多次否决不跳过。

    场景:连发 3 个 final_text;stop_hook 始终 veto。
    修复前:第一次 veto 后 stop_hook_active=True,第二、三次终答跳过校验直接放行(BUG)。
    修复后:每次终答都跑 hook,持续 veto + 强制再走,直到 maxTurns 兜底(此处 max_turns=3
    使 3 次终答后 turn_count > max_turns 终止,且 hook 被调 3 次)。"""
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    # 3 次终答
    client = FakeLLMClient(turns=[TURN_FINAL_TEXT, TURN_FINAL_TEXT, TURN_FINAL_TEXT])

    call_count = {"n": 0}

    def always_veto(state: State) -> StopDecision:
        call_count["n"] += 1
        return StopDecision(veto=True, message=f"[veto-{call_count['n']}] 测试用持续否决")

    class S:
        model = "m"
        max_tokens = 64
        # max_turns=2:终答×3 后 turn_count=3 > 2,maxTurns 兜底(终答路径累 turn_count)
        max_turns = 2
        recovery_budget = 3
        max_output_recovery = 2

    st = State()
    st.messages = [{"role": "user", "content": "给结论"}]
    events = [
        e
        async for e in query(
            st, client=client, registry=reg, settings=S(),
            runner=runner, compactor=MinimalCompactor(),
            stop_hook=always_veto,
        )
    ]
    # 每个终答都跑 hook(3 次终答 → 3 次调用),最终 maxTurns 兜底而非静默 STOP
    assert call_count["n"] == 3
    assert events[-1] == {"type": "end", "reason": TerminalReason.MAX_TURNS.value}
    # 诊断字段累积了 3 条否决原因(maxTurns 终止前未走 clear 路径)
    assert len(st.pending_stop_reasons) == 3
    assert all("veto-" in r for r in st.pending_stop_reasons)
    await client.aclose()


async def test_stop_hook_passes_after_evidence_set_mid_turns():
    """否决一次 → 模型补 evidence(测试代码代行)→ 第二次终答 hook 放行(§5④#3「通过才放行」)。

    重点:fix 后每终答都跑 hook(不再有 stop_hook_active 跳过),第二次因 ctx 满足而放行,
    pending_stop_reasons 在放行时被清空。"""
    reg = ToolRegistry()
    runner = SerialToolRunner(reg, recovery_budget=3, permission=AllowAllPermission())
    client = _two_finals_client()

    call_count = {"n": 0}
    stop_hook = make_rmcp_stop_gate()

    def gate_with_mid_inject(state: State) -> StopDecision:
        call_count["n"] += 1
        dec = stop_hook(state)
        # 第一次返回前,模拟"模型/工具补足证据链"——在 hook 返回 veto 后,
        # query() 会注入消息 + continue,下一轮终答前 evidence 已就绪
        if call_count["n"] == 1:
            state.tool_use_context["evidence_ok"] = True
            state.tool_use_context["anti_filter_ok"] = True
        return dec

    st = State()
    st.messages = [{"role": "user", "content": "给结论"}]
    events = [
        e
        async for e in query(
            st, client=client, registry=reg, settings=_settings(),
            runner=runner, compactor=MinimalCompactor(),
            stop_hook=gate_with_mid_inject,
        )
    ]
    # hook 被调 2 次(每终答一次):第 1 否决、第 2 放行
    assert call_count["n"] == 2
    assert events[-1] == {"type": "end", "reason": TerminalReason.STOP.value}
    # 放行后 reasons 被清空
    assert st.pending_stop_reasons == []
    await client.aclose()
