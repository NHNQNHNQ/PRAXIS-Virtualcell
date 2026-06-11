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
    s = Section("identity", "你是助手")
    assert s.name == "identity"
    assert s.text == "你是助手"
    assert s.cache_break is False
    assert Section("mcp", "x", cache_break=True).cache_break is True


def test_default_prompt_is_section_list_with_boundary():
    secs = get_default_system_prompt()
    assert isinstance(secs, list)
    assert all(isinstance(s, Section) for s in secs)
    names = [s.name for s in secs]
    # §7.2.2 section 化;§7.2.3 含且仅含一个动态边界 sentinel
    assert names.count(SYSTEM_PROMPT_DYNAMIC_BOUNDARY) == 1
    # 边界前是静态层(identity/safety),边界本身 text 为空占位
    bidx = names.index(SYSTEM_PROMPT_DYNAMIC_BOUNDARY)
    assert bidx >= 1  # 边界前至少有静态 section
    assert secs[bidx].text == ""


def test_config_has_dump_prompts_off_by_default():
    # M8 §6⑤:Settings 单一源新形态,dump_prompts="" 即关(零值即关闭语义)
    from praxis2.config import Settings
    s = Settings(
        anthropic_api_key="sk", anthropic_base_url="u",
        model="m", max_tokens=64, max_turns=20,
        recovery_budget=3, max_output_recovery=2,
        host="h", port=1, workers=1,
        max_concurrent_per_user=1, user_qps=1.0,
        global_llm_inflight=1, quota_global_max_queued=1,
    )
    assert s.dump_prompts == ""  # §7.2.8:空字符串=关闭,非空才写 JSONL


def _s(name):
    return [Section(name, name + "-text")]


def test_priority_override_wins_over_all():
    out = build_effective_system_prompt(
        override=_s("ov"), coordinator=_s("co"), agent=_s("ag"),
        custom=_s("cu"), default=_s("de"),
    )
    assert [s.name for s in out] == ["ov"]


def test_priority_chain_descends_when_higher_layers_absent():
    assert [s.name for s in build_effective_system_prompt(
        coordinator=_s("co"), agent=_s("ag"), custom=_s("cu"), default=_s("de"))] == ["co"]
    assert [s.name for s in build_effective_system_prompt(
        agent=_s("ag"), custom=_s("cu"), default=_s("de"))] == ["ag"]
    assert [s.name for s in build_effective_system_prompt(
        custom=_s("cu"), default=_s("de"))] == ["cu"]
    assert [s.name for s in build_effective_system_prompt(default=_s("de"))] == ["de"]


def test_default_always_exists_even_when_nothing_passed():
    # §7.2.4:default 总是有 —— 全空也回落到 get_default_system_prompt()
    out = build_effective_system_prompt()
    assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in [s.name for s in out]


def test_append_is_always_linearly_last_in_fixed_order():
    # §7.2.4:append(cli/proactive/teammate 多来源)恒线性追加在最后,顺序固定
    out = build_effective_system_prompt(
        override=_s("ov"),
        append=[Section("cli", "c"), Section("proactive", "p"), Section("teammate", "t")],
    )
    assert [s.name for s in out] == ["ov", "cli", "proactive", "teammate"]


def test_append_appended_after_default_when_no_base_layer():
    out = build_effective_system_prompt(append=[Section("cli", "c")])
    names = [s.name for s in out]
    assert names[-1] == "cli"  # 不漏层、不乱序:append 仍在最后
    assert SYSTEM_PROMPT_DYNAMIC_BOUNDARY in names  # default 仍兜底


def test_empty_list_override_is_explicit_empty_base_not_fallback():
    # override=[] 是有意"空覆盖"(用 is not None 区分"未传"与"显式空"),
    # 不回落 get_default_system_prompt();契约锁定,防后续误"修复"成 fallback
    assert build_effective_system_prompt(override=[]) == []


def test_section_cache_returns_cached_value_until_invalidated():
    c = SectionCache()
    assert c.render(Section("a", "v1")) == "v1"
    # 同名再来(text 变了)应命中旧缓存,证明确实缓存(§7.2.3 key=section name)
    assert c.render(Section("a", "v2")) == "v1"
    c.invalidate()  # /clear、compact、worktree 切换时显式失效
    assert c.render(Section("a", "v3")) == "v3"


def test_section_cache_skips_cache_break_sections_every_time():
    c = SectionCache()
    assert c.render(Section("mcp", "first", cache_break=True)) == "first"
    # cache_break=True 每轮重算,不缓存(如 MCP 指令类)
    assert c.render(Section("mcp", "second", cache_break=True)) == "second"


def test_cache_break_does_not_pollute_cache():
    # 语义边界:cache_break 渲染不写 _cache,同名 non-cache_break 不受污染
    c = SectionCache()
    c.render(Section("mcp", "dirty", cache_break=True))
    assert c.render(Section("mcp", "clean")) == "clean"


def test_to_api_system_splits_static_prefix_with_cache_control():
    secs = [
        Section("identity", "静态A"),
        Section("safety", "静态B"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
        Section("turn_state", "动态C"),
    ]
    blocks = to_api_system(secs)
    # §7.2.3:静态前缀合一个 block 且打 cache_control: ephemeral(prompt cache 命中点)
    assert blocks[0] == {
        "type": "text",
        "text": "静态A\n\n静态B",
        "cache_control": {"type": "ephemeral"},
    }
    # 动态部分独立 block,无 cache_control(每轮变,缓存会污染)
    assert blocks[1] == {"type": "text", "text": "动态C"}
    assert len(blocks) == 2


def test_to_api_system_no_boundary_means_all_static():
    blocks = to_api_system([Section("a", "x"), Section("b", "y")])
    assert blocks == [
        {"type": "text", "text": "x\n\ny", "cache_control": {"type": "ephemeral"}}
    ]


def test_to_api_system_skips_empty_text_sections():
    # 边界 sentinel(text="")与空 section 不产生空 block / 空行
    blocks = to_api_system([
        Section("a", "x"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
        Section("empty", ""),
    ])
    assert blocks == [
        {"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}
    ]


def test_to_api_system_empty_in_empty_out_caller_maps_to_none():
    # 契约锁定:无内容(如 build_effective_system_prompt(override=[]))→ []。
    # Anthropic 拒绝 system=[];调用方(T9 query)须把 [] 视为不传 system(None)。
    assert to_api_system([]) == []
    assert to_api_system([Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, "")]) == []


def test_to_api_system_multiple_boundaries_first_wins():
    # §7.2.3 钦定单一 boundary;若误含多个,首个生效、其后全归 dynamic
    # (保守失败模式:正确性优先于缓存效率,不会把动态内容误缓存)
    blocks = to_api_system([
        Section("a", "静态"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),
        Section("b", "动1"),
        Section(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, ""),  # 第二个 boundary,被忽略
        Section("c", "动2"),
    ])
    assert len(blocks) == 2
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert blocks[1] == {"type": "text", "text": "动1\n\n动2"}


def test_get_user_context_combines_date_and_md_or_none():
    ctx = get_user_context(claude_md="规则X", agents_md="A说明", today="2026-05-19")
    assert "2026-05-19" in ctx and "规则X" in ctx and "A说明" in ctx
    assert get_user_context() is None  # 全空不注入空 context


def test_prepend_user_context_inserts_as_first_user_message_immutably():
    msgs = [{"role": "user", "content": "原始问"}]
    out = prepend_user_context(msgs, "日期+规则")
    assert out[0] == {"role": "user", "content": "日期+规则"}
    assert out[1] == {"role": "user", "content": "原始问"}
    assert msgs == [{"role": "user", "content": "原始问"}]  # 不就地改原 list
    none_out = prepend_user_context(msgs, None)
    assert none_out == msgs and none_out is not msgs  # None:不注入,但仍返回新 list


def test_get_system_context_git_and_cache_breaker_or_none():
    sc = get_system_context(git_status="M a.py", cache_breaker="abc123")
    assert "M a.py" in sc and "abc123" in sc
    assert get_system_context() is None


def test_append_system_context_is_last_cache_break_section_after_boundary():
    base = get_default_system_prompt()
    out = append_system_context(base, "git+breaker")
    last = out[-1]
    # §7.2.5:system context 追在末尾、cache_break=True(在动态边界之后,不进缓存前缀)
    assert last.name == "system_context"
    assert last.text == "git+breaker"
    assert last.cache_break is True
    assert append_system_context(base, None) == list(base)  # None 不追加
    # 经 to_api_system:它落在动态 block,不带 cache_control
    blocks = to_api_system(out)
    assert "git+breaker" in blocks[-1]["text"]
    assert "cache_control" not in blocks[-1]


def test_specialized_prompts_cover_required_family():
    # §7.2.6:compact / memory-extract / memory-update / 路由判定 各有独立协议
    assert set(SPECIALIZED_PROMPTS) == {
        "compact", "memory-extract", "memory-update", "route"
    }


def test_specialized_prompt_does_not_reuse_main_prompt():
    main_text = " ".join(s.text for s in get_default_system_prompt())
    for name in SPECIALIZED_PROMPTS:
        p = get_specialized_prompt(name)
        # 检查专项串非空且不是主 prompt 文本的子串(M2 占位下足够;M4/M5 填实际
        # 协议后"不复用"由内容本身保证,此测试不做全文相似度检测)
        assert p and p not in main_text


def test_get_specialized_prompt_unknown_is_fail_fast():
    # 未知名 fail-fast,不静默兜底到主 prompt(对治 v1"默认值骗人")
    with pytest.raises(KeyError):
        get_specialized_prompt("nope")


def test_section_hash_stable_and_drift_sensitive():
    a = [Section("x", "v"), Section("y", "w")]
    b = [Section("x", "v"), Section("y", "w")]
    assert section_hash(a) == section_hash(b)  # 同内容稳定
    assert section_hash(a) != section_hash([Section("x", "v"), Section("y", "W")])
    assert section_hash(a) != section_hash([Section("x", "v")])  # 漏 section 也变
    # 分隔符直证:name/text 边界不可拼接歧义
    assert section_hash([Section("a", "b")]) != section_hash([Section("ab", "")])


def test_render_and_persist_hangs_api_system_and_hash_on_tool_use_context():
    st = State()
    secs = get_default_system_prompt()
    api = render_and_persist(st, secs)
    # §7.2.7:渲染结果挂 state.tool_use_context,fork/subagent/hook 看同一份防 drift
    assert st.tool_use_context["rendered_system_prompt"] == api
    assert api == to_api_system(secs)
    assert st.tool_use_context["system_prompt_hash"] == section_hash(secs)
