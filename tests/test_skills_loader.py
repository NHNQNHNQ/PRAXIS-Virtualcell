import pytest

from praxis2.skills.loader import SkillManifest, parse_skill_md, progressive_disclosure


def test_parse_domain_style_frontmatter_with_closing_fence():
    text = (
        "---\nname: nature_plot\ndescription: \u751f\u6210 Nature \u98ce\u683c\u56fe"
        "\nwhen-to-use: \u9700\u8981\u53d1\u8868\u7ea7\u914d\u56fe\u65f6\nallowed-tools: [Read, Wri"
        "te]\nuser-invocable: true\ncontext: fork\npaths: ['"
        "*.csv']\nhooks: [doi_required]\nmodel: claude-x\nef"
        "fort: 30\n---\n\u6b63\u6587:\u7ed8\u56fe\u6b65\u9aa4\u2026\u2026\n"
    )
    m = parse_skill_md(text, folder_name="nature_plot")
    assert m.name == "nature_plot"
    assert m.description == "\u751f\u6210 Nature \u98ce\u683c\u56fe"
    assert m.when_to_use == "\u9700\u8981\u53d1\u8868\u7ea7\u914d\u56fe\u65f6"
    assert m.allowed_tools == ["Read", "Write"]
    assert m.user_invocable is True
    assert m.context == "fork"
    assert m.paths == ["*.csv"]
    assert m.hooks == ["doi_required"]
    assert m.model == "claude-x"
    assert m.effort == 30
    assert "\u7ed8\u56fe\u6b65\u9aa4" in m.body
    assert isinstance(m, SkillManifest)


def test_parse_common_style_yaml_to_eof_no_closing_fence():

    text = "---\nname: shared_skill\ndescription: \u5171\u4eab\u6280\u80fd\n"
    m = parse_skill_md(text, folder_name="shared_skill")
    assert m.name == "shared_skill"
    assert m.description == "\u5171\u4eab\u6280\u80fd"
    assert m.body == ""


def test_migration_defaults_filled_when_fields_missing():

    text = "---\nname: legacy\ndescription: \u65e7\u6280\u80fd\u4ec5\u4e24\u5b57\u6bb5\n---\n\u65e7\u6b63\u6587"
    m = parse_skill_md(text, folder_name="legacy")

    assert m.when_to_use == "\u65e7\u6280\u80fd\u4ec5\u4e24\u5b57\u6bb5"
    assert m.paths == []
    assert m.context == "inline"
    assert m.hooks == []
    assert m.user_invocable is False
    assert m.model is None
    assert m.effort is None
    assert m.allowed_tools == []


def test_name_defaults_to_folder_when_absent():
    m = parse_skill_md("---\ndescription: \u65e0 name\n---\n", folder_name="folderX")
    assert m.name == "folderX"


def test_missing_description_is_hard_error_fail_fast():

    with pytest.raises(ValueError, match="description"):
        parse_skill_md("---\nname: x\n---\n", folder_name="x")


def test_no_frontmatter_is_hard_error():
    with pytest.raises(ValueError, match="frontmatter"):
        parse_skill_md("\u6ca1\u6709\u4efb\u4f55 frontmatter \u7684\u7eaf\u6587\u672c", folder_name="x")


def test_scalar_double_dash_value_kept_as_raw_not_crash():

    from praxis2.skills.loader import _scalar

    assert _scalar("--3") == "--3"
    assert _scalar("-12") == -12
    assert _scalar("30") == 30
    assert _scalar("--fast") == "--fast"


def _mk(name, desc, when):
    return SkillManifest(name=name, description=desc, when_to_use=when)


def test_progressive_disclosure_only_desc_and_when_truncated_250():
    long = "x" * 400
    s = progressive_disclosure([_mk("s1", long, long)], max_chars=250, budget_chars=100_000)

    assert "s1" in s
    assert s.count("x" * 250) == 2
    assert "x" * 251 not in s
    assert "…" in s


def test_skill_list_capped_at_one_percent_budget_drops_tail_with_notice():

    many = [_mk(f"s{i}", "d" * 50, "w" * 50) for i in range(50)]
    s = progressive_disclosure(many, max_chars=250, budget_chars=2_000)
    cap = 2_000 // 100
    one_block = len("## skill: s0\n- description: " + "d" * 50 + "\n- when-to-use: " + "w" * 50)
    notice = len("\n\n[Omitted 49skills beyond the summary budget; expand them on demand]")

    assert len(s) <= cap + one_block + notice
    assert "Omitted" in s
    assert "s0" in s


def test_empty_manifests_yields_empty_string():
    assert progressive_disclosure([], max_chars=250, budget_chars=100_000) == ""
