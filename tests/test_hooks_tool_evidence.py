from praxis2.core.state import State
from praxis2.hooks.builtin import make_tool_use_presence_stop_hook


def _state_with_final(text, *, tool_ok=False):
    st = State()
    st.messages = [{"role": "user", "content": "\u8bf7\u5e2e\u6211\u5bf9\u63a5"}]
    if tool_ok:
        st.messages.append(
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": False, "content": "ok"}],
            }
        )
    st.messages.append({"role": "assistant", "content": [{"type": "text", "text": text}]})
    return st


def test_claims_execution_zero_tools_vetoes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("\u6211\u5df2\u5bf9\u63a5\u5b8c\u6210,\u6700\u4f73\u4eb2\u548c\u529b -9.2 kcal/mol\u3002")
    dec = hook(st)
    assert dec.veto is True
    assert st.stop_hook_veto_count == 1


def test_claims_but_has_successful_tool_use_passes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("\u6211\u5df2\u5bf9\u63a5\u5b8c\u6210,\u5f97\u5206 -9.2\u3002", tool_ok=True)
    assert hook(st).veto is False


def test_no_claims_passes():
    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final("You can use AutoDock Vina for docking; here is a suggested workflow.")
    assert hook(st).veto is False


def test_conceptual_metric_mention_does_not_veto():

    hook = make_tool_use_presence_stop_hook()
    st = _state_with_final(
        "RMSD measures docking quality. A value below 2 angstroms is a co"
        "mmon criterion; a scoring function estimates binding."
    )
    assert hook(st).veto is False


def test_veto_capped_once():
    hook = make_tool_use_presence_stop_hook(max_veto=1)
    st = _state_with_final("\u6211\u5df2\u5bf9\u63a5\u5b8c\u6210,\u5f97\u5206 -9.2\u3002")
    assert hook(st).veto is True
    assert hook(st).veto is False
