from praxis2.agents.loader import resolve_agent
from praxis2.brains.inject import assemble_agent_sections
from praxis2.brains.migrate import build_fixture_brain
from praxis2.brains.retrieve import retrieve_brain
from praxis2.core.prompt import (
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
    Section,
    build_effective_system_prompt,
    to_api_system,
)


def test_assemble_returns_sections_with_common_and_hits_before_boundary():

    sel = resolve_agent("Virtualcell", user_query="Virtualcell \u9886\u57df")
    common = build_fixture_brain("_common")
    cryo = build_fixture_brain("Virtualcell")
    r = retrieve_brain(cryo, "Virtualcell \u9886\u57df", top_k=2)
    secs = assemble_agent_sections(
        sel,
        retrieval=r,
        common_docs=common,
        skill_summary="## skill: wf1\n- description: d",
        memory_text="- [Rule](rmcp.md) \u2014 \u89c4\u5219\u7d22\u5f15",
    )
    assert all(isinstance(s, Section) for s in secs)
    names = [s.name for s in secs]
    assert "brain_common_rules" in names
    assert "brain_domain_hits" in names
    assert "skill_disclosure" in names
    assert "memory_index" in names
    assert names[-1] == SYSTEM_PROMPT_DYNAMIC_BOUNDARY
    blob = "\n".join(s.text for s in secs)
    assert "Virtualcell" in blob or "\u9886\u57df" in blob


def test_injects_into_agent_layer_of_build_effective_system_prompt():
    sel = resolve_agent("general", user_query="\u8de8\u5b66\u79d1")
    common = build_fixture_brain("_common")
    gen = build_fixture_brain("general")
    r = retrieve_brain(gen, "\u6b63\u4f8b \u9886\u57df", top_k=1)
    agent_secs = assemble_agent_sections(
        sel,
        retrieval=r,
        common_docs=common,
        skill_summary="",
        memory_text="",
    )
    eff = build_effective_system_prompt(agent=agent_secs)
    assert eff is agent_secs or eff[: len(agent_secs)] == agent_secs
    api = to_api_system(eff)
    assert api and api[0].get("cache_control") == {"type": "ephemeral"}


def test_bare_degrade_keeps_common_and_records_degrade_section_not_silent():
    sel = resolve_agent("bare", user_query="\u968f\u4fbf")
    common = build_fixture_brain("_common")
    r = retrieve_brain([], "x", top_k=3)  # degraded_to_bare
    secs = assemble_agent_sections(
        sel,
        retrieval=r,
        common_docs=common,
        skill_summary="",
        memory_text="",
    )
    names = [s.name for s in secs]
    assert "brain_common_rules" in names
    assert "brain_domain_hits" not in names
    assert "retrieval_degraded" in names
    blob = "\n".join(s.text for s in secs)
    assert "Retrieval fallback" in blob or "bare" in blob
