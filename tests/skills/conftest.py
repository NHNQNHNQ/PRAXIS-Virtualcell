"""公共 fixture:列出所有 skill,按 brain 参数化。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BRAINS_ROOT = REPO_ROOT / "brains"


def _list_skill_dirs(brain: str | None = None) -> list[Path]:
    out: list[Path] = []
    if brain:
        bd = BRAINS_ROOT / brain
        if not bd.is_dir():
            return []
        return sorted({rp.parent for rp in bd.rglob("run.py")
                       if rp.is_file() and not rp.name.startswith("._")})
    for bd in sorted(BRAINS_ROOT.iterdir()):
        if not bd.is_dir() or bd.name.startswith("."):
            continue
        out.extend({rp.parent for rp in bd.rglob("run.py")
                    if rp.is_file() and not rp.name.startswith("._")})
    return sorted(out)


def all_skill_dirs() -> list[Path]:
    return _list_skill_dirs()


def brain_skill_dirs(brain: str) -> list[Path]:
    return _list_skill_dirs(brain)


def run_skill(skill_dir: Path, payload: dict, timeout: int = 15) -> dict:
    """跑 skill 的 run.py,返回 {exit, stdout_json, stderr}。"""
    rp = skill_dir / "run.py"
    env = {**os.environ,
           "PRAXIS_SKILL_DRY_HOST": "1",
           "PYTHONPATH": str(REPO_ROOT) + ":" + os.environ.get("PYTHONPATH", "")}
    proc = subprocess.run(
        [sys.executable, str(rp)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=timeout, env=env,
    )
    try:
        j = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        j = None
    return {"exit": proc.returncode, "stdout_json": j, "stderr": proc.stderr}


@pytest.fixture
def skill_runner():
    return run_skill
