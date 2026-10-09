

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from praxis2.brains.migrate import DISCIPLINE_SLUGS


_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "brains"


_CACHE: dict[str, dict[str, Any]] | None = None


def load_all_profiles(*, root: Path | None = None) -> dict[str, dict[str, Any]]:

    global _CACHE
    if _CACHE is not None:
        return _CACHE
    actual_root = root or _DEFAULT_ROOT
    _CACHE = {slug: _walk_brain(slug, root=actual_root) for slug in DISCIPLINE_SLUGS}
    return _CACHE


def reset_cache_for_tests() -> None:

    global _CACHE
    _CACHE = None


def _walk_brain(slug: str, *, root: Path) -> dict[str, Any]:
    brain_dir = root / slug
    case_count = _count_files(brain_dir / "memory" / "cases", "*.md")
    rule_count = _count_lines_in_files(brain_dir / "memory" / "rules", "*.md")
    skill_workflows = _list_workflow_dirs(brain_dir / "skills" / "workflows")
    sample_cases = _top_5_cases(brain_dir / "memory" / "cases", slug)
    yaml_data = _load_metadata_yaml(brain_dir / "metadata.yaml")
    prof = {
        "case_count": case_count,
        "rule_count": rule_count,
        "skill_workflows": skill_workflows,
        "sample_cases": sample_cases,
        "short_prompt": yaml_data.get("short_prompt", ""),
        "methods": yaml_data.get("methods", []),
        "helps_with": yaml_data.get("helps_with", []),
        "delivers": yaml_data.get("delivers", []),
    }


    examples = yaml_data.get("examples")
    if examples:
        prof["examples"] = examples
    return prof


def _count_files(dir_path: Path, pattern: str) -> int:
    if not dir_path.is_dir():
        return 0
    return sum(1 for p in dir_path.glob(pattern) if not p.name.startswith("._"))


def _count_lines_in_files(dir_path: Path, pattern: str) -> int:

    if not dir_path.is_dir():
        return 0
    total = 0
    for p in dir_path.glob(pattern):

        if p.name.startswith("._"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        total += 1
        except OSError:
            pass
    return total


def _list_workflow_dirs(dir_path: Path) -> list[str]:
    if not dir_path.is_dir():
        return []
    return sorted(
        d.name for d in dir_path.iterdir()
        if d.is_dir() and not d.name.startswith("._") and (d / "SKILL.md").is_file()
    )


def _top_5_cases(dir_path: Path, slug: str) -> list[dict[str, str]]:
    if not dir_path.is_dir():
        return []
    cases = sorted(
        (p for p in dir_path.glob("*.md") if not p.name.startswith("._")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:5]
    out = []
    for p in cases:
        title = _extract_title(p) or p.stem
        out.append({
            "case_id": p.stem,
            "title": title,
            "file": f"brains/{slug}/memory/cases/{p.name}",
        })
    return out


def _extract_title(path: Path) -> str | None:

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
                if line.startswith("title:"):
                    return line.split(":", 1)[1].strip().strip('"\'')
                if line and not line.startswith("#"):
                    break
    except OSError:
        return None
    return None


def _load_metadata_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}
