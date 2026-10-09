from __future__ import annotations

import pytest

from tests.skills.conftest import all_skill_dirs, run_skill

SYNTH_SKILL_UPLIFT_PENDING = "v2.0.3 carry: synth 13 skill SKILL.md schema \u5f85 uplift"


def _skill_id(p):

    parts = p.parts
    try:
        idx = parts.index("brains")
        brain = parts[idx + 1]
    except (ValueError, IndexError):
        brain = "?"
    return f"{brain}/{p.name}"


def _maybe_xfail_synth(skill_dir):
    parts = skill_dir.parts
    try:
        idx = parts.index("brains")
    except ValueError:
        return
    if idx + 1 < len(parts) and parts[idx + 1] == "synth":
        pytest.xfail(SYNTH_SKILL_UPLIFT_PENDING)


@pytest.mark.parametrize("skill_dir", all_skill_dirs(), ids=_skill_id)
def test_simulate_path_ok(skill_dir):
    _maybe_xfail_synth(skill_dir)
    r = run_skill(skill_dir, {"simulate": True, "seed": 42})
    assert r["exit"] == 0, f"exit={r['exit']}, stderr={r['stderr'][:300]}"
    assert isinstance(r["stdout_json"], dict), f"non-dict stdout, stderr={r['stderr'][:300]}"


@pytest.mark.parametrize("skill_dir", all_skill_dirs(), ids=_skill_id)
def test_real_dry_host_path_ok(skill_dir):

    _maybe_xfail_synth(skill_dir)
    r = run_skill(skill_dir, {"simulate": False, "seed": 42})
    assert r["exit"] == 0, f"exit={r['exit']}, stderr={r['stderr'][:300]}"
    assert isinstance(r["stdout_json"], dict), f"stderr={r['stderr'][:300]}"
