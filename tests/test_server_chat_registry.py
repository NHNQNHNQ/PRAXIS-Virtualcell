from praxis2.agents.agent_tool import AgentTool
from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.registry import ToolRegistry


def _names(reg: ToolRegistry) -> set[str]:
    return {t["name"] for t in reg.anthropic_tools()}


def test_default_returns_tool_registry() -> None:
    reg = build_chat_registry()
    assert isinstance(reg, ToolRegistry)


def test_default_includes_agent_tool() -> None:
    assert "AgentTool" in _names(build_chat_registry())


def test_default_agent_tool_is_real_instance() -> None:
    reg = build_chat_registry()
    t = reg.get("AgentTool")
    assert isinstance(t, AgentTool)


def test_default_tools_non_empty_for_anthropic_api() -> None:

    assert build_chat_registry().anthropic_tools()


def test_discipline_mode_excludes_agent_tool() -> None:

    sel = resolve_agent("virtualcell", user_query="\u57fa\u56e0perturbation\u9884\u6d4b")
    assert sel.is_discipline is True
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" not in _names(reg)


def test_general_mode_includes_agent_tool() -> None:
    sel = resolve_agent("general", user_query="\u8de8\u5b66\u79d1\u95ee\u9898")
    assert sel.is_discipline is False
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_bare_mode_includes_agent_tool() -> None:
    sel = resolve_agent("bare", user_query="\u968f\u4fbf\u95ee")
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_yourself_mode_includes_agent_tool() -> None:
    sel = resolve_agent("yourself", user_query="\u81ea\u53cd\u6027\u95ee\u9898")
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_one_above_all_route_to_discipline_excludes_agent_tool() -> None:

    sel = resolve_agent("one-above-all", user_query="Norman perturbation \u9884\u6d4b")
    assert sel.is_discipline is True
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" not in _names(reg)


def test_one_above_all_fallback_includes_agent_tool() -> None:

    sel = resolve_agent("one-above-all", user_query="\u5b8c\u5168\u65e0\u5173\u7684\u65e5\u5e38\u95f2\u804a")
    assert sel.is_discipline is False
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_explicit_none_selection_includes_agent_tool() -> None:

    reg = build_chat_registry(selection=None)
    assert "AgentTool" in _names(reg)
