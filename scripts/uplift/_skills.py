"""统一 'find skill dirs by brain' — 处理 brains/<brain>/skills/workflows/ 与
nested 路径(如 brains/md/Naruto-main/skills/workflows/)。"""
from __future__ import annotations

from pathlib import Path


def find_skill_dirs(brain: str, brains_root: Path = Path("brains")) -> list[Path]:
    """找 brain 下所有含 run.py 的 skill 目录,返回排序后的 Path 列表。"""
    bd = brains_root / brain
    if not bd.is_dir():
        return []
    out = sorted({rp.parent for rp in bd.rglob("run.py") if rp.is_file() and not rp.name.startswith("._")})
    return out


def all_brain_names(brains_root: Path = Path("brains")) -> list[str]:
    """枚举所有 brain 目录(顶层 brains/*/),忽略隐藏目录。"""
    return sorted(d.name for d in brains_root.iterdir() if d.is_dir() and not d.name.startswith("."))
