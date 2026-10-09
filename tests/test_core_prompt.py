import pytest

from praxis2.core.prompt import (
    SPECIALIZED_PROMPTS,
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
    Section,
    SectionCache,
    append_system_context,
    build_effective_system_prompt,
    get_default_system_prompt,
    get_specialized_prompt,
    get_system_context,
    get_user_context,
    prepend_user_context,
    render_and_persist,
    section_hash,
    to_api_system,
)
from praxis2.core.state import State


def test_section_is_named_piece_with_cache_break_default_false():
    s = Section("identity", "\u4f60\u662f\u52a9\u624b")
    assert s.name == "identity"
    assert s.text == "\u4f60\u662f\u52a9\u624b"
    assert s.cache_break is False
    assert Section("mcp", "x", cache_break=True).cache_break is True


def test_default_prompt_is_section_list_with_boundary():
    secs = get_default_system_prompt()
    assert isinstance(secs, list)
    assert all(isinstance(s, Section) for s in secs)
    names = [s.name for s in secs]

    assert names.count(SYSTEM_PROMPT_DYNAMIC_BOUNDARY) == 1

    bidx = names.index(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)
    assert bidx >= 1
    assert secs[bidx].text == ""


def _s(name):
    return [Section(name, name + "-text")]


def test_priority_override_wins_over_all():
    out = build_effective_system_prompt(
        override=_s("ov"),
        coordinator=_s("co"),
        agent=_s("ag"),
        custom=_s("cu"),
        default=_s("de"),
    )
    assert [s.name for s in out] == ["ov"]


def test_priority_chain_descends_when_higher_layers_absent():
    assert [
        s.name
        for s in build_effective_system_prompt(coordinator=_s("co"), agent=_s("ag"), custom=_s("cu"), default=_s("de"))
    ] == ["co"]
    assert [s.name for s in build_effective_system_prompt(agent=_s("ag"), custom=_s("cu"), default=_s("de"))] == ["ag"]
    assert [s.name for s in build_effective_system_prompt(custom=_s("cu"), default=_s("de"))] == ["cu"]
    assert [s.name for s in build_effective_system_prompt(default=_s("de"))] == ["de"]


def test_default_always_exists_even_when_nothing_passed():

    out = build_effective_system_prompt()
    assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in [s.name for s in out]


def test_append_is_always_linearly_last_in_fixed_order():

    out = build_effective_system_prompt(
        override=_s("ov"),
        append=[Section("cli", "c"), Section("proactive", "p"), Section("teammate", "t")],
    )
    assert [s.name for s in out] == ["ov", "cli", "proactive", "teammate"]


def test_append_appended_after_default_when_no_base_layer():
    out = build_effective_system_prompt(append=[Section("cli", "c")])
    names = [s.name for s in out]
    assert names[-1] == "cli"
    assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in names


def test_empty_list_override_is_explicit_empty_base_not_fallback():

    assert build_effective_system_prompt(override=[]) == []


def test_section_cache_returns_cached_value_until_invalidated():
    c = SectionCache()
    assert c.render(Section("a", "v1")) == "v1"

    assert c.render(Section("a", "v2")) == "v1"
    c.invalidate()
    assert c.render(Section("a", "v3")) == "v3"


def test_section_cache_skips_cache_break_sections_every_time():
    c = SectionCache()
    assert c.render(Section("mcp", "first", cache_break=True)) == "first"

    assert c.render(Section("mcp", "second", cache_break=True)) == "second"


def test_cache_break_does_not_pollute_cache():

    c = SectionCache()
    c.render(Section("mcp", "dirty", cache_break=True))
    assert c.render(Section("mcp", "clean")) == "clean"


def test_to_api_system_splits_static_prefix_with_cache_control():
    secs = [
        Section("identity", "\u9759\u6001A"),
        Section("safety", "\u9759\u6001B"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
        Section("turn_state", "\u52a8\u6001C"),
    ]
    blocks = to_api_system(secs)

    assert blocks[0] == {
        "type": "text",
        "text": "\u9759\u6001A\n\n\u9759\u6001B",
        "cache_control": {"type": "ephemeral"},
    }

    assert blocks[1] == {"type": "text", "text": "\u52a8\u6001C"}
    assert len(blocks) == 2


def test_to_api_system_no_boundary_means_all_static():
    blocks = to_api_system([Section("a", "x"), Section("b", "y")])
    assert blocks == [{"type": "text", "text": "x\n\ny", "cache_control": {"type": "ephemeral"}}]


def test_to_api_system_skips_empty_text_sections():

    blocks = to_api_system(
        [
            Section("a", "x"),
            Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
            Section("empty", ""),
        ]
    )
    assert blocks == [{"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}]


def test_to_api_system_empty_in_empty_out_caller_maps_to_none():

    assert to_api_system([]) == []
    assert to_api_system([Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, "")]) == []


def test_to_api_system_multiple_boundaries_first_wins():

    blocks = to_api_system(
        [
            Section("a", "\u9759\u6001"),
            Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
            Section("b", "\u52a81"),
            Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
            Section("c", "\u52a82"),
        ]
    )
    assert len(blocks) == 2
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert blocks[1] == {"type": "text", "text": "\u52a81\n\n\u52a82"}


def test_get_user_context_combines_date_and_md_or_none():
    ctx = get_user_context(claude_md="\u89c4\u5219X", agents_md="A\u8bf4\u660e", today="2026-05-19")
    assert "2026-05-19" in ctx and "\u89c4\u5219X" in ctx and "A\u8bf4\u660e" in ctx
    assert get_user_context() is None


def test_prepend_user_context_inserts_as_first_user_message_immutably():
    msgs = [{"role": "user", "content": "\u539f\u59cb\u95ee"}]
    out = prepend_user_context(msgs, "\u65e5\u671f+\u89c4\u5219")
    assert out[0] == {"role": "user", "content": "\u65e5\u671f+\u89c4\u5219"}
    assert out[1] == {"role": "user", "content": "\u539f\u59cb\u95ee"}
    assert msgs == [{"role": "user", "content": "\u539f\u59cb\u95ee"}]
    none_out = prepend_user_context(msgs, None)
    assert none_out == msgs and none_out is not msgs


def test_get_system_context_git_and_cache_breaker_or_none():
    sc = get_system_context(git_status="M a.py", cache_breaker="abc123")
    assert "M a.py" in sc and "abc123" in sc
    assert get_system_context() is None


def test_append_system_context_is_last_cache_break_section_after_boundary():
    base = get_default_system_prompt()
    out = append_system_context(base, "git+breaker")
    last = out[-1]

    assert last.name == "system_context"
    assert last.text == "git+breaker"
    assert last.cache_break is True
    assert append_system_context(base, None) == list(base)

    blocks = to_api_system(out)
    assert "git+breaker" in blocks[-1]["text"]
    assert "cache_control" not in blocks[-1]


def test_specialized_prompts_cover_required_family():

    assert set(SPECIALIZED_PROMPTS) == {"compact", "memory-extract", "memory-update", "route"}


def test_specialized_prompt_does_not_reuse_main_prompt():
    main_text = " ".join(s.text for s in get_default_system_prompt())
    for name in SPECIALIZED_PROMPTS:
        p = get_specialized_prompt(name)

        assert p and p not in main_text


def test_get_specialized_prompt_unknown_is_fail_fast():

    with pytest.raises(KeyError):
        get_specialized_prompt("nope")


def test_section_hash_stable_and_drift_sensitive():
    a = [Section("x", "v"), Section("y", "w")]
    b = [Section("x", "v"), Section("y", "w")]
    assert section_hash(a) == section_hash(b)
    assert section_hash(a) != section_hash([Section("x", "v"), Section("y", "W")])
    assert section_hash(a) != section_hash([Section("x", "v")])

    assert section_hash([Section("a", "b")]) != section_hash([Section("ab", "")])


def test_render_and_persist_hangs_api_system_and_hash_on_tool_use_context():
    st = State()
    secs = get_default_system_prompt()
    api = render_and_persist(st, secs)

    assert st.tool_use_context["rendered_system_prompt"] == api
    assert api == to_api_system(secs)
    assert st.tool_use_context["system_prompt_hash"] == section_hash(secs)
