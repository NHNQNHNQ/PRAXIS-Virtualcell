"""Build cached system instructions from the selected brain and available skills."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from praxis2.brains.inject import assemble_agent_sections
from praxis2.brains.migrate import migrate_dir_tree
from praxis2.brains.retrieve import retrieve_brain
from praxis2.core.prompt import build_effective_system_prompt, to_api_system
from praxis2.skills.loader import parse_skill_md, progressive_disclosure

_QUERY_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"
_HOST_INV_DEFAULT = _REPO_ROOT / "_audit" / "host_inventory.json"

_host_envs_cache: set[str] | None = None


def _host_envs(inv_path: Path = _HOST_INV_DEFAULT) -> set[str]:

    global _host_envs_cache
    if _host_envs_cache is not None:
        return _host_envs_cache
    if inv_path.is_file():
        try:
            inv = json.loads(inv_path.read_text(encoding="utf-8"))
            _host_envs_cache = set(inv.get("conda_envs", []))
        except Exception:  # noqa: BLE001
            _host_envs_cache = set()
    else:
        _host_envs_cache = set()
    return _host_envs_cache


def _parse_host_env(skill_md_text: str) -> str | None:

    if not skill_md_text.startswith("---"):
        return None
    for line in skill_md_text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if line.startswith("host_env:"):
            return line.split(":", 1)[1].strip()
    return None


def _score_skill(manifest: Any, query_tokens: set[str]) -> int:

    text = " ".join([manifest.name, manifest.description or "", manifest.when_to_use or ""]).lower()
    return sum(1 for tok in query_tokens if tok in text)


def build_chat_system_prompt(
    selection: Any,
    user_query: str,
    *,
    brains_root: Path | None = None,
    inv_path: Path | None = None,
    top_k: int = 5,
    skill_max_chars: int = 250,


    skill_budget_chars: int = 5_000_000,
) -> list[dict]:
    """Return cached instruction blocks for the selected brain and available skills."""
    root = brains_root or _BRAINS_ROOT_DEFAULT
    if not root.is_dir() or not getattr(selection, "brain_slugs", None):
        return []


    all_docs: list[Any] = []
    for slug in selection.brain_slugs:
        slug_dir = root / slug
        if slug_dir.is_dir():
            all_docs.extend(migrate_dir_tree(slug_dir, slug))

    common_docs = [d for d in all_docs if d.slug == "_common"]
    domain_docs = [
        d for d in all_docs
        if d.slug != "_common" and d.kind != "skills"
    ]
    skill_docs = [d for d in all_docs if d.kind == "skills"]

    # 2. retrieve domain hits
    retrieval = retrieve_brain(domain_docs, user_query, top_k=top_k)


    host_envs = _host_envs(inv_path or _HOST_INV_DEFAULT)
    manifests = []
    for d in skill_docs:
        host_env = _parse_host_env(d.text)
        if host_env is None:

            continue
        if host_envs and host_env not in host_envs:
            continue
        try:
            m = parse_skill_md(d.text, folder_name=d.stem)
            manifests.append(m)
        except (ValueError, Exception):  # noqa: BLE001

            continue


    query_tokens = set(_QUERY_TOKEN_RE.findall(user_query.lower()))
    manifests.sort(key=lambda m: (-_score_skill(m, query_tokens), m.name))

    skill_summary = progressive_disclosure(
        manifests,
        max_chars=skill_max_chars,
        budget_chars=skill_budget_chars,
    )

    # 4. assemble + 5. build/to_api
    sections = assemble_agent_sections(
        selection,
        retrieval=retrieval,
        common_docs=common_docs,
        skill_summary=skill_summary,
        memory_text="",
    )
    effective = build_effective_system_prompt(agent=sections)
    return to_api_system(effective)
