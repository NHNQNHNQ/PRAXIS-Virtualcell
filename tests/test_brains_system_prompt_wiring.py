from __future__ import annotations

from praxis2.agents.loader import resolve_agent
from praxis2.brains.system_prompt import build_chat_system_prompt


def test_build_chat_system_prompt_returns_non_empty_for_discipline_agent():

    sel = resolve_agent(
        "virtualcell", user_query="\u6211\u8981\u9884\u6d4b\u57fa\u56e0perturbation\u540e\u7684transcriptome"
    )
    assert sel.brain_slugs == ["_common", "virtualcell"]
    out = build_chat_system_prompt(sel, "\u6211\u8981\u505a\u9176\u70ed\u7a33\u5b9a\u6027 ddG \u626b\u63cf")
    assert out, "The system prompt must provide instructions for selecting tools."

    assert out[0].get("cache_control") == {"type": "ephemeral"}

    flat = "\n".join(b.get("text", "") for b in out)
    assert "RMCP" in flat or "rmcp" in flat.lower()


def test_build_chat_system_prompt_filters_skills_by_host_env():

    sel = resolve_agent("virtualcell", user_query="\u9884\u6d4b\u57fa\u56e0perturbation")
    out = build_chat_system_prompt(sel, "\u9884\u6d4b\u86cb\u767d\u7ed3\u6784")
    flat = "\n".join(b.get("text", "") for b in out)

    assert "2d_3d_classify" not in flat
    assert "motion_correct_ctf" not in flat


def test_empty_brain_slugs_returns_empty():

    class FakeSel:
        brain_slugs: list[str] = []

    out = build_chat_system_prompt(FakeSel(), "anything")
    assert out == []
