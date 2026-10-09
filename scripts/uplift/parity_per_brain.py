"""单 brain 分桶器:把所有 skill 分成 GREEN/RED_EASY/N_A 三桶。

GREEN  : SKILL.md frontmatter 的 host_env 出现在 host conda env 列表里;
RED_EASY: host_env 在白名单(可现场装的小 cli 工具)且 host 上无;
N_A    : host_env 是商业软件、数据缺、或缺 host_env(license-blocked / unknown)。

判据维护在常量字典里;数据源是 _audit/host_inventory.json。
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.uplift._skills import all_brain_names, find_skill_dirs

# 这些 conda env 名一旦缺失,标 RED_EASY(我们可以现装)
INSTALLABLE_HINTS: set[str] = {"praxis-protein", "praxis-microbiome", "praxis-omics"}

# 这些标 N_A(商业/数据/license 受限)
LICENSE_BLOCKED_HINTS: set[str] = {
    "schrodinger", "maestro", "moe", "discovery_studio", "icm", "rosetta_commercial",
}

# SKILL.md frontmatter 缺 host_env 时,按 brain 推断默认 env(host 上确实装了的)
BRAIN_DEFAULT_HOST_ENV: dict[str, str] = {
    "_common": "base",
    "cell": "PRAXIS-Cell",
    "crispr": "PRAXIS-CRISPR",
    "dock": "praxis-dock",
    "drug": "praxis-drug",
    "enzyme": "PRAXIS-Enzyme",
    "immuno": "praxis-immuno",
    "md": "base",
    "microbiome": "praxis-microbiome",
    "omics": "praxis-omics",
    "pharma": "praxis-pharma",
    "protein": "praxis-protein",
    # cryo 故意不填(host 无通用 cryo env;真要的话 SKILL.md 必须显式声明)
}


def _frontmatter_field(md_path: Path, key: str) -> str | None:
    txt = md_path.read_text(encoding="utf-8", errors="replace")
    if not txt.startswith("---"):
        return None
    for ln in txt.splitlines()[1:]:
        if ln.strip() == "---":
            break
        if ln.startswith(f"{key}:"):
            return ln.split(":", 1)[1].strip()
    return None


def classify(skill_dir: Path, host_envs: set[str], *, brain: str | None = None) -> dict:
    md = skill_dir / "SKILL.md"
    declared = _frontmatter_field(md, "host_env") if md.is_file() else None
    skill = skill_dir.name
    if brain is None:
        brain = skill_dir.parent.parent.parent.name

    inferred = False
    host_env = declared
    if not host_env:
        host_env = BRAIN_DEFAULT_HOST_ENV.get(brain)
        inferred = host_env is not None

    if host_env and host_env.lower() in LICENSE_BLOCKED_HINTS:
        bucket = "N_A"
        reason = f"host_env {host_env} 是商业受限工具"
    elif not host_env:
        bucket = "N_A"
        reason = f"SKILL.md 未声明 host_env 且 brain={brain} 无默认 env"
    elif host_env in host_envs:
        bucket = "GREEN"
        reason = f"host_env {host_env} 在 .53 conda envs" + (" (brain-inferred)" if inferred else "")
    elif host_env in INSTALLABLE_HINTS:
        bucket = "RED_EASY"
        reason = f"host_env {host_env} 缺,可后续 conda create"
    else:
        bucket = "N_A"
        reason = f"host_env {host_env} 未识别且不在可装白名单"
    return {
        "brain": brain, "skill": skill,
        "host_env": host_env, "host_env_inferred": inferred,
        "bucket": bucket, "reason": reason,
    }


def load_host_envs(inventory_json: Path = Path("_audit/host_inventory.json")) -> set[str]:
    if not inventory_json.is_file():
        return set()
    data = json.loads(inventory_json.read_text())
    return set(data.get("conda_envs", []) or [])


def classify_brain(brain: str, brains_root: Path = Path("brains")) -> list[dict]:
    host_envs = load_host_envs()
    return [classify(sd, host_envs, brain=brain) for sd in find_skill_dirs(brain, brains_root)]


if __name__ == "__main__":
    import sys
    brain = sys.argv[1] if len(sys.argv) > 1 else None
    if brain:
        rows = classify_brain(brain)
    else:
        rows = []
        for bn in all_brain_names():
            rows.extend(classify_brain(bn))
    by_b = {}
    for r in rows:
        by_b[r["bucket"]] = by_b.get(r["bucket"], 0) + 1
    print(json.dumps({"total": len(rows), "by_bucket": by_b}, indent=2, ensure_ascii=False))
    out_path = Path("_audit/parity_v1_per_brain.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}", file=sys.stderr)
