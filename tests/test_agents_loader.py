import pytest

from praxis2.agents.loader import AgentMode, AgentSelection, resolve_agent


def test_discipline_mode_selects_that_slug_plus_common():
    # B.3:历史 TitleCase 入口 "Cryo" 经 resolve_agent 内部 .lower() 标准化为
    # "cryo",与真盘 namespace brain:cryo 对齐(reviewer M5 C1+C2)
    sel = resolve_agent("Cryo", user_query="冷冻电镜重构")
    assert isinstance(sel, AgentSelection)
    assert sel.mode is AgentMode.DISCIPLINE
    assert sel.brain_slugs == ["_common", "cryo"]
    assert sel.is_discipline is True   # §7.5.4 → disallowed AgentTool
    assert sel.readonly is False


def test_general_mode_selects_general_plus_common():
    sel = resolve_agent("general", user_query="跨学科问题")
    assert sel.mode is AgentMode.GENERAL
    assert sel.brain_slugs == ["_common", "general"]
    assert sel.is_discipline is False


def test_bare_mode_keeps_common_only_no_domain_brain_s13():
    sel = resolve_agent("bare", user_query="随便问")
    assert sel.mode is AgentMode.BARE
    assert sel.brain_slugs == ["_common"]  # S13:bare 仍保留 _common


def test_one_above_all_routes_by_intent_and_records_reason():
    rec: list[dict] = []
    sel = resolve_agent(
        "one-above-all",
        user_query="CRISPR 基因编辑 sgRNA 设计脱靶",
        transcript_sink=rec.append,
    )
    assert sel.mode is AgentMode.ONE_ABOVE_ALL
    assert "crispr" in sel.brain_slugs  # B.3:lowercase 单源
    assert sel.max_turns is not None and sel.max_turns <= 5  # §7.5.4
    # §12:路由依据写 transcript(可复盘为何这么选)
    assert rec and rec[0]["type"] == "agent_route"
    assert rec[0]["chosen"] == "crispr" and "score" in rec[0]


def test_one_above_all_falls_back_to_general_when_unsure():
    rec: list[dict] = []
    sel = resolve_agent(
        "one-above-all", user_query="完全无关的日常闲聊",
        transcript_sink=rec.append,
    )
    assert "general" in sel.brain_slugs
    assert rec[0]["chosen"] == "general"
    assert rec[0]["fallback"] is True


def test_yourself_synthesizes_readonly_slice_from_disciplines():
    sel = resolve_agent(
        "yourself",
        user_query="我做酶催化与对接,关注 Enzyme 与 Dock",
    )
    assert sel.mode is AgentMode.YOURSELF
    assert "_common" in sel.brain_slugs
    # B.3:slug lowercase 单源(真盘 brain:enzyme / brain:dock)
    assert "enzyme" in sel.brain_slugs and "dock" in sel.brain_slugs
    assert sel.readonly is True  # 只读视图,不写回 brains(§7.5.0)


def test_unknown_spec_is_hard_error_fail_fast():
    with pytest.raises(ValueError, match="未知 agent"):
        resolve_agent("not-a-mode", user_query="x")


def test_one_above_all_routes_md_by_force_keyword_not_dead():
    # C1 回归:多词短语拆为单 token 后 "force"/"forcefield" 真能命中 MD
    # (旧 "force field" 经 _tokens 分词永不命中,属死关键词)
    sel = resolve_agent("one-above-all", user_query="force field 分子动力学模拟")
    assert "md" in sel.brain_slugs  # B.3:lowercase 单源
    assert sel.scores.get("md", 0) >= 1
