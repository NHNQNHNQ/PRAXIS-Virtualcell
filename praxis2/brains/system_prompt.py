"""把 selection 转成 chat-stream 用的 system prompt list[dict](PLAN §11)。

接线五步(此前 `_chat_stream` 不传 system → 模型只看到 tools,不知何时调):
1. 用 migrate_dir_tree 从 brains/<slug>/ 加载所有 BrainDoc
2. retrieve_brain(top_k) 选命中文档
3. parse_skill_md + 主路径过滤(skill 的 host_env ∈ staging conda_envs)
4. assemble_agent_sections(common + 命中 + skill 摘要)
5. build_effective_system_prompt → to_api_system → list[dict]

主路径过滤的副作用:智能体 turn-1 只看见 `.53` 上真能跑的 skill,直接消除「方案推荐 = 用户跑不了」的幻觉(PLAN §12.1)。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import re

from praxis2.brains.inject import assemble_agent_sections
from praxis2.brains.migrate import migrate_dir_tree
from praxis2.brains.retrieve import retrieve_brain
from praxis2.core.prompt import build_effective_system_prompt, to_api_system
from praxis2.skills.loader import parse_skill_md, progressive_disclosure

_QUERY_TOKEN_RE = re.compile(r"[\w一-鿿]+")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRAINS_ROOT_DEFAULT = _REPO_ROOT / "brains"
_HOST_INV_DEFAULT = _REPO_ROOT / "_audit" / "host_inventory.json"

_host_envs_cache: set[str] | None = None


def _host_envs(inv_path: Path = _HOST_INV_DEFAULT) -> set[str]:
    """staging .53 上真实存在的 conda env 名集合。文件缺失 → 空集 →
    所有 skill 都不被 host_env 过滤(即降级到「看所有 skill」,不阻塞)。"""
    global _host_envs_cache
    if _host_envs_cache is not None:
        return _host_envs_cache
    if inv_path.is_file():
        try:
            inv = json.loads(inv_path.read_text(encoding="utf-8"))
            _host_envs_cache = set(inv.get("conda_envs", []))
        except Exception:  # noqa: BLE001 — 启发式 cache,本来就是非阻塞兜底
            _host_envs_cache = set()
    else:
        _host_envs_cache = set()
    return _host_envs_cache


def _parse_host_env(skill_md_text: str) -> str | None:
    """从 SKILL.md frontmatter 简单 grep `host_env:` 字段(避免依赖 yaml)。"""
    if not skill_md_text.startswith("---"):
        return None
    for line in skill_md_text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if line.startswith("host_env:"):
            return line.split(":", 1)[1].strip()
    return None


def _score_skill(manifest: Any, query_tokens: set[str]) -> int:
    """简单 query-term 重叠度评分:description + name + when_to_use 出现 query token 次数。
    用于把最相关的 skill 排到 progressive_disclosure 前面(预算不够时,vina_gnina_dock
    这种关键候选不会因为字母序排在 v 而被砍掉)。"""
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
    # 5 MB → cap = 50 KB(progressive_disclosure 默认按 budget//100 算 cap)。
    # 52 个 green skill × ~600 字符 ≈ 31 KB 足够全披露。
    skill_budget_chars: int = 5_000_000,
) -> list[dict]:
    """组装 chat-stream 用 system list-of-dict。

    返回 [] 时调用方须传 system=None(to_api_system 契约)。
    """
    root = brains_root or _BRAINS_ROOT_DEFAULT
    if not root.is_dir() or not getattr(selection, "brain_slugs", None):
        return []

    # 1. 加载 slug 全部 docs
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

    # 3. skill 主路径过滤:host_env 必须落在 staging 已有 env 内
    host_envs = _host_envs(inv_path or _HOST_INV_DEFAULT)
    manifests = []
    for d in skill_docs:
        host_env = _parse_host_env(d.text)
        if host_env is None:
            # 没标 host_env 的暂不入主路径(PLAN §12.1 严守:零报错才入)
            continue
        if host_envs and host_env not in host_envs:
            continue
        try:
            m = parse_skill_md(d.text, folder_name=d.stem)
            manifests.append(m)
        except (ValueError, Exception):  # noqa: BLE001
            # 跳过坏 frontmatter / 缺 description 的 skill,不让一颗坏苹果毁掉整盘
            continue

    # 按 user_query 相关度排序(高分先,字母序 tie-break),让 budget 不够时
    # 最相关 skill 不会被字母序末尾的 skill 顶掉(PLAN §12.1)
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
