"""TEST-AGENT-FRAMEWORK.md §5 修复 + mode-aware 注册。

锁死契约:
- build_chat_registry() 默认含 AgentTool
- selection.is_discipline=True → 不含 AgentTool(§7.5.4 防递归)
- selection.is_discipline=False(general/bare/yourself/fallback OAA)→ 含 AgentTool
- selection=None → 安全默认 = 含 AgentTool
- 返回值是 ToolRegistry,query() 可直接喂
"""

from praxis2.agents.agent_tool import AgentTool
from praxis2.agents.loader import resolve_agent
from praxis2.server.chat_registry import build_chat_registry
from praxis2.tools.registry import ToolRegistry


def _names(reg: ToolRegistry) -> set[str]:
    return {t["name"] for t in reg.anthropic_tools()}


# ── 默认行为(None / 未传 selection) ──────────────────────────────


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
    """query() 把 anthropic_tools() 喂 Anthropic API(query.py:94/105);
    非空才会让 model 在 tools 参数里收到工具描述。"""
    assert build_chat_registry().anthropic_tools()


# ── mode-aware 行为 ──────────────────────────────────────────────


def test_discipline_mode_excludes_agent_tool() -> None:
    """§7.5.4:学科 agent 禁用 AgentTool 防递归深度爆炸。"""
    sel = resolve_agent("cell", user_query="细胞实验")
    assert sel.is_discipline is True
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" not in _names(reg)


def test_general_mode_includes_agent_tool() -> None:
    sel = resolve_agent("general", user_query="跨学科问题")
    assert sel.is_discipline is False
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_bare_mode_includes_agent_tool() -> None:
    sel = resolve_agent("bare", user_query="随便问")
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_yourself_mode_includes_agent_tool() -> None:
    sel = resolve_agent("yourself", user_query="自反性问题")
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_one_above_all_route_to_discipline_excludes_agent_tool() -> None:
    """OAA 命中学科(is_discipline=True)按学科 agent 处理,禁用 AgentTool。"""
    sel = resolve_agent("one-above-all", user_query="CRISPR sgRNA 设计脱靶")
    assert sel.is_discipline is True
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" not in _names(reg)


def test_one_above_all_fallback_includes_agent_tool() -> None:
    """OAA 无关键词 → fallback general,is_discipline=False,带 AgentTool。"""
    sel = resolve_agent("one-above-all", user_query="完全无关的日常闲聊")
    assert sel.is_discipline is False
    reg = build_chat_registry(selection=sel)
    assert "AgentTool" in _names(reg)


def test_explicit_none_selection_includes_agent_tool() -> None:
    """显式 selection=None(安全默认,用于未接入 resolve_agent 的旧调用点)。"""
    reg = build_chat_registry(selection=None)
    assert "AgentTool" in _names(reg)
