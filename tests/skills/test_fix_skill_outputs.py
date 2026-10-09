from pathlib import Path

from scripts.uplift.fix_skill_outputs import (
    default_schema_for_archetype,
    insert_outputs_section,
)


def test_default_schema_docking_has_poses():
    s = default_schema_for_archetype("docking", brain="dock", skill="foo_dock")
    assert "poses" in s
    assert "best_affinity" in s
    assert s["skill_id"] == "foo_dock"


def test_default_schema_unknown_archetype_falls_back_to_generic():
    s = default_schema_for_archetype("brand-new-thing", brain="x", skill="y")
    assert "ok" in s
    assert "skill_id" in s


def test_insert_outputs_section_appends_when_missing(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: foo\n---\n\n## 一句话原则\n\n做事.\n")
    out = insert_outputs_section(md, {"a": 1, "b": "x"})
    assert out["action"] == "inserted"
    txt = md.read_text()
    assert "## 输出契约" in txt
    assert '"a": 1' in txt


def test_insert_outputs_section_skips_when_present(tmp_path: Path):
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: foo\n---\n\n## 输出契约\n\n```json\n{\"a\": 1}\n```\n")
    out = insert_outputs_section(md, {"z": 9})
    assert out["action"] == "skipped"
