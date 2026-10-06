from praxis2.core.state import State
from praxis2.hooks.builtin import make_tool_use_presence_stop_hook


def _state_with_final(text, *, tool_ok=False):
    st = State()
    st.messages = [{"role": "user", "content": "请帮我对接"}]
    if tool_ok:
        st.messages.append(
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": False,
                 "content": "ok"}]}
        )
    st.messages.append(
        {"role": "assistant", "content": [{"type": "text", "text": text}]}
    )
    return st


def test_claims_execution_zero_tools_vetoes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("我已对接完成,最佳亲和力 -9.2 kcal/mol。")
    dec = hook(st)
    assert dec.veto is True
    assert st.stop_hook_veto_count == 1


def test_claims_but_has_successful_tool_use_passes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("我已对接完成,得分 -9.2。", tool_ok=True)
    assert hook(st).veto is False


def test_no_claims_passes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("你可以用 AutoDock Vina 方法来做对接,大致流程是……")
    assert hook(st).veto is False


def test_conceptual_metric_mention_does_not_veto():
    """精度优先:纯概念提及 metric 词(无声称动词、无数值)不得误杀。"""
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final(
        "RMSD 是衡量对接质量的指标,一般小于 2Å 算成功;打分函数评估结合,亲和力越低越强。"
    )
    assert hook(st).veto is False


def test_veto_capped_once():
    hook = make_tool_use_presence_stop_hook(max_veto=1)
    st = _state_with_final("我已对接完成,得分 -9.2。")
    assert hook(st).veto is True   # 第一次 veto
    assert hook(st).veto is False  # 计数到顶,不再 veto(防循环)
