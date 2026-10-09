import pytest

from praxis2.skills.loader import SkillManifest, parse_skill_md, progressive_disclosure


def test_parse_domain_style_frontmatter_with_closing_fence():
    text = (
        "---\n"
        "name: nature_plot\n"
        "description: 生成 Nature 风格图\n"
        "when-to-use: 需要发表级配图时\n"
        "allowed-tools: [Read, Write]\n"
        "user-invocable: true\n"
        "context: fork\n"
        "paths: ['*.csv']\n"
        "hooks: [doi_required]\n"
        "model: claude-x\n"
        "effort: 30\n"
        "---\n"
        "正文:绘图步骤……\n"
    )
    m = parse_skill_md(text, folder_name="nature_plot")
    assert m.name == "nature_plot"
    assert m.description == "生成 Nature 风格图"
    assert m.when_to_use == "需要发表级配图时"
    assert m.allowed_tools == ["Read", "Write"]
    assert m.user_invocable is True
    assert m.context == "fork"
    assert m.paths == ["*.csv"]
    assert m.hooks == ["doi_required"]
    assert m.model == "claude-x"
    assert m.effort == 30
    assert "绘图步骤" in m.body
    assert isinstance(m, SkillManifest)


def test_parse_common_style_yaml_to_eof_no_closing_fence():
    # v1 _common 跨 agent 技能:--- yaml 到 EOF,无结束 ---
    text = "---\nname: shared_skill\ndescription: 共享技能\n"
    m = parse_skill_md(text, folder_name="shared_skill")
    assert m.name == "shared_skill"
    assert m.description == "共享技能"
    assert m.body == ""  # 无正文


def test_migration_defaults_filled_when_fields_missing():
    # v1 缺 when-to-use/paths/context/hooks/user-invocable/model/effort/allowed-tools
    text = "---\nname: legacy\ndescription: 旧技能仅两字段\n---\n旧正文"
    m = parse_skill_md(text, folder_name="legacy")
    # 缺 when-to-use → 用 description 兜底(不留空,否则渐进披露退化冷启动)
    assert m.when_to_use == "旧技能仅两字段"
    assert m.paths == []           # 默认空 = 不条件触发
    assert m.context == "inline"   # 默认进程内(非 fork)
    assert m.hooks == []
    assert m.user_invocable is False  # 默认保守
    assert m.model is None         # 不覆盖
    assert m.effort is None        # 未知估时
    assert m.allowed_tools == []   # 默认空 = 继承 agent 级


def test_name_defaults_to_folder_when_absent():
    m = parse_skill_md("---\ndescription: 无 name\n---\n", folder_name="folderX")
    assert m.name == "folderX"


def test_missing_description_is_hard_error_fail_fast():
    # description 模型可见、发现关键,缺失 fail-fast(配置不静默兜假值)
    with pytest.raises(ValueError, match="description"):
        parse_skill_md("---\nname: x\n---\n", folder_name="x")


def test_no_frontmatter_is_hard_error():
    with pytest.raises(ValueError, match="frontmatter"):
        parse_skill_md("没有任何 frontmatter 的纯文本", folder_name="x")


def test_scalar_double_dash_value_kept_as_raw_not_crash():
    # C1 回归:--<digits> 不得触发 int() 崩溃,按原始字符串保留(守 docstring 契约)
    from praxis2.skills.loader import _scalar

    assert _scalar("--3") == "--3"
    assert _scalar("-12") == -12   # 单负号仍是整数
    assert _scalar("30") == 30
    assert _scalar("--fast") == "--fast"


def _mk(name, desc, when):
    return SkillManifest(name=name, description=desc, when_to_use=when)


def test_progressive_disclosure_only_desc_and_when_truncated_250():
    long = "x" * 400
    s = progressive_disclosure(
        [_mk("s1", long, long)], max_chars=250, budget_chars=100_000
    )
    # 仅 description + when-to-use,各截到 250(+省略号);不含正文(无 body 字段)
    assert "s1" in s
    assert s.count("x" * 250) == 2          # desc 与 when 各一段截到 250
    assert "x" * 251 not in s               # 不超 250(省略号是非 x 字符)
    assert "…" in s


def test_skill_list_capped_at_one_percent_budget_drops_tail_with_notice():
    # budget_chars 模拟上下文预算;skill 列表上限 ≈ 1% → 超出丢尾部 + 记提示
    many = [_mk(f"s{i}", "d" * 50, "w" * 50) for i in range(50)]
    s = progressive_disclosure(many, max_chars=250, budget_chars=2_000)
    cap = 2_000 // 100
    one_block = len(
        "## skill: s0\n- description: " + "d" * 50 + "\n- when-to-use: " + "w" * 50
    )
    notice = len("\n\n[已省略 49 个 skill:超 ~1% 上下文预算,调用时按需展开]")
    # 精确上界:cap + 至多一个强制收录块 + 提示行(无模糊 +200,真约束预算不被掩盖)
    assert len(s) <= cap + one_block + notice
    assert "已省略" in s                  # 丢尾部有可见提示(不静默)
    assert "s0" in s                      # 头部保留


def test_empty_manifests_yields_empty_string():
    assert progressive_disclosure([], max_chars=250, budget_chars=100_000) == ""
