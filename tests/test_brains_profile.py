"""M10 brains/profile.py — 13 brain walk + metadata.yaml + sample_cases。"""
from __future__ import annotations

from praxis2.brains.migrate import DISCIPLINE_SLUGS


def test_load_all_profiles_returns_expected_slugs():
    from praxis2.brains.profile import load_all_profiles, reset_cache_for_tests
    reset_cache_for_tests()
    profiles = load_all_profiles()
    assert set(profiles.keys()) == set(DISCIPLINE_SLUGS)
    assert len(profiles) == 1


def test_profile_has_required_fields():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for slug, prof in profiles.items():
        for key in ("case_count", "rule_count", "skill_workflows",
                    "sample_cases", "short_prompt", "methods",
                    "helps_with", "delivers"):
            assert key in prof, f"{slug} missing {key}"


def test_profile_case_count_is_int():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for _slug, prof in profiles.items():
        assert isinstance(prof["case_count"], int)
        assert prof["case_count"] >= 0


def test_profile_skill_workflows_is_sorted_list():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for _slug, prof in profiles.items():
        wfs = prof["skill_workflows"]
        assert isinstance(wfs, list)
        assert wfs == sorted(wfs)


def test_profile_sample_cases_at_most_5():
    from praxis2.brains.profile import load_all_profiles
    profiles = load_all_profiles()
    for _slug, prof in profiles.items():
        sc = prof["sample_cases"]
        assert isinstance(sc, list)
        assert len(sc) <= 5
        for c in sc:
            assert "case_id" in c
            assert "title" in c
            assert "file" in c


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
