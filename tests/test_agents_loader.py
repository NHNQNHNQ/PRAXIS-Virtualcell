import pytest

from praxis2.agents.loader import AgentMode, AgentSelection, resolve_agent


def test_discipline_mode_selects_that_slug_plus_common():

    sel = resolve_agent("Virtualcell", user_query="\u57fa\u56e0perturbation\u9884\u6d4b")
    assert isinstance(sel, AgentSelection)
    assert sel.mode is AgentMode.DISCIPLINE
    assert sel.brain_slugs == ["_common", "virtualcell"]
    assert sel.is_discipline is True  # §7.5.4 → disallowed AgentTool
    assert sel.readonly is False


def test_general_mode_selects_general_plus_common():
    sel = resolve_agent("general", user_query="\u8de8\u5b66\u79d1\u95ee\u9898")
    assert sel.mode is AgentMode.GENERAL
    assert sel.brain_slugs == ["_common", "general"]
    assert sel.is_discipline is False


def test_bare_mode_keeps_common_only_no_domain_brain_s13():
    sel = resolve_agent("bare", user_query="\u968f\u4fbf\u95ee")
    assert sel.mode is AgentMode.BARE
    assert sel.brain_slugs == ["_common"]


def test_one_above_all_routes_by_intent_and_records_reason():
    rec: list[dict] = []
    sel = resolve_agent(
        "one-above-all",
        user_query="Norman perturbation \u57fa\u56e0perturbation transcriptome",
        transcript_sink=rec.append,
    )
    assert sel.mode is AgentMode.ONE_ABOVE_ALL
    assert "virtualcell" in sel.brain_slugs
    assert sel.max_turns is not None and sel.max_turns <= 5  # §7.5.4

    assert rec and rec[0]["type"] == "agent_route"
    assert rec[0]["chosen"] == "virtualcell" and "score" in rec[0]


def test_one_above_all_falls_back_to_general_when_unsure():
    rec: list[dict] = []
    sel = resolve_agent(
        "one-above-all",
        user_query="\u5b8c\u5168\u65e0\u5173\u7684\u65e5\u5e38\u95f2\u804a",
        transcript_sink=rec.append,
    )
    assert "general" in sel.brain_slugs
    assert rec[0]["chosen"] == "general"
    assert rec[0]["fallback"] is True


def test_yourself_synthesizes_readonly_slice_from_disciplines():
    sel = resolve_agent(
        "yourself",
        user_query="\u6211\u5173\u6ce8\u57fa\u56e0perturbation\u9884\u6d4b norman perturbation",
    )
    assert sel.mode is AgentMode.YOURSELF
    assert "_common" in sel.brain_slugs

    assert "virtualcell" in sel.brain_slugs
    assert sel.readonly is True


def test_unknown_spec_is_hard_error_fail_fast():
    with pytest.raises(ValueError, match="Unknown agent"):
        resolve_agent("not-a-mode", user_query="x")


def test_one_above_all_routes_virtualcell_by_keyword():

    sel = resolve_agent("one-above-all", user_query="norman perturbation perturbation\u9884\u6d4b")
    assert "virtualcell" in sel.brain_slugs
    assert sel.scores.get("virtualcell", 0) >= 1
