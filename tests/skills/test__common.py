from __future__ import annotations

import pytest

from tests.skills.conftest import brain_skill_dirs, run_skill

SKILLS = brain_skill_dirs("_common")


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda p: p.name)
def test_simulate_ok(skill_dir):
    r = run_skill(skill_dir, {"simulate": True, "seed": 1})
    assert r["exit"] == 0, r["stderr"][:300]
    assert isinstance(r["stdout_json"], dict)


@pytest.mark.parametrize("skill_dir", SKILLS, ids=lambda p: p.name)
def test_real_dry_host_ok(skill_dir):
    r = run_skill(skill_dir, {"simulate": False, "seed": 1})
    assert r["exit"] == 0, r["stderr"][:300]
    assert isinstance(r["stdout_json"], dict)
