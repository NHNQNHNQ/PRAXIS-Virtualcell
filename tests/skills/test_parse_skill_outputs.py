from pathlib import Path

from scripts.uplift.parse_skill_outputs import parse_outputs_block, parse_skill_md


def test_parses_clean_json_block(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text(
        '---\nname: foo\nhost_env: bar\n---\n\n'
        '## 输出契约\n\n```json\n{"a": 1, "b": {"c": 2}}\n```\n'
    )
    out = parse_skill_md(md)
    assert out["verdict"] == "OK"
    assert out["keys"] == ["a", "b"]
    assert out["schema"]["a"] == 1


def test_handles_trailing_commas():
    body = '{"x": 1, "y": [1, 2,],}'
    obj, err = parse_outputs_block(body)
    assert err is None
    assert obj == {"x": 1, "y": [1, 2]}


def test_handles_line_comments():
    body = '{"x": 1,  // comment\n  "y": 2 }'
    obj, err = parse_outputs_block(body)
    assert err is None
    assert obj == {"x": 1, "y": 2}


def test_reports_missing_section(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text('---\nname: foo\n---\n\n# Title\n\nNo outputs section here.\n')
    out = parse_skill_md(md)
    assert out["verdict"] == "MISSING_SECTION"
    assert out["keys"] is None
