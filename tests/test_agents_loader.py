import pytest

from praxis2.agents.loader import AgentMode, AgentSelection, resolve_agent


def test_discipline_mode_selects_that_slug_plus_common():
    # 历史 TitleCase 入口经 resolve_agent 内部 .lower() 标准化为 lowercase slug,
    # 与 namespace brain:virtualcell 对齐(PRAXIS-virtualcell 单一学科)。
    sel = resolve_agent("Virtualcell", user_query="基因扰动预测")
    assert isinstance(sel, AgentSelection)
    assert sel.mode is AgentMode.DISCIPLINE
    assert sel.brain_slugs == ["_common", "virtualcell"]
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
        user_query="Norman perturbation 基因扰动 转录组",
        transcript_sink=rec.append,
    )
    assert sel.mode is AgentMode.ONE_ABOVE_ALL
    assert "virtualcell" in sel.brain_slugs  # lowercase 单源
    assert sel.max_turns is not None and sel.max_turns <= 5  # §7.5.4
    # §12:路由依据写 transcript(可复盘为何这么选)
    assert rec and rec[0]["type"] == "agent_route"
    assert rec[0]["chosen"] == "virtualcell" and "score" in rec[0]


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
        user_query="我关注基因扰动预测 norman perturbation",
    )
    assert sel.mode is AgentMode.YOURSELF
    assert "_common" in sel.brain_slugs
    # slug lowercase 单源(namespace brain:virtualcell)
    assert "virtualcell" in sel.brain_slugs
    assert sel.readonly is True  # 只读视图,不写回 brains(§7.5.0)


def test_unknown_spec_is_hard_error_fail_fast():
    with pytest.raises(ValueError, match="未知 agent"):
        resolve_agent("not-a-mode", user_query="x")


def test_one_above_all_routes_virtualcell_by_keyword():
    # PRAXIS-virtualcell:OAA 按 virtualcell 关键词(norman/perturbation/扰动)命中单一学科。
    sel = resolve_agent("one-above-all", user_query="norman perturbation 扰动预测")
    assert "virtualcell" in sel.brain_slugs  # lowercase 单源
    assert sel.scores.get("virtualcell", 0) >= 1
