"""Brain metadata parsing against isolated local fixtures."""

def test_profile_text_fields_empty_when_no_metadata_yaml(tmp_path):
    """没 metadata.yaml 的 brain:short_prompt='' / methods=[] / helps_with=[] / delivers=[]。"""
    from praxis2.brains.profile import _walk_brain
    brain_dir = tmp_path / "dummy"
    (brain_dir / "memory" / "cases").mkdir(parents=True)
    (brain_dir / "memory" / "rules").mkdir(parents=True)
    (brain_dir / "skills" / "workflows").mkdir(parents=True)

    prof = _walk_brain("dummy", root=tmp_path)
    assert prof["short_prompt"] == ""
    assert prof["methods"] == []
    assert prof["helps_with"] == []
    assert prof["delivers"] == []



def test_profile_metadata_yaml_loaded_when_present(tmp_path):
    """有 metadata.yaml:4 个字段从 yaml 拿。"""
    import yaml

    from praxis2.brains.profile import _walk_brain
    brain_dir = tmp_path / "dummy2"
    (brain_dir / "memory" / "cases").mkdir(parents=True)
    metadata = {
        "short_prompt": "Dummy 测试用",
        "methods": ["antiSMASH", "cobra"],
        "helps_with": ["通路设计"],
        "delivers": ["JSON 报告"],
    }
    (brain_dir / "metadata.yaml").write_text(
        yaml.safe_dump(metadata, allow_unicode=True), encoding="utf-8",
    )

    prof = _walk_brain("dummy2", root=tmp_path)
    assert prof["short_prompt"] == "Dummy 测试用"
    assert prof["methods"] == ["antiSMASH", "cobra"]
    assert prof["helps_with"] == ["通路设计"]
    assert prof["delivers"] == ["JSON 报告"]
