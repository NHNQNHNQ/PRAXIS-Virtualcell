#!/usr/bin/env python3
"""阶段 2: 对账, 产 _audit/parity_matrix.tsv + summary.json。
列: brain  skill  req_type  name  source  confidence  gap_kind  matched_in  suggestion

gap_kind ∈ green | red:env_missing | red:pkg_missing | red:cli_missing |
           red:data_missing | red:license_required | red:gpu_required(实有 GPU 时降级) |
           gray (host 有但大脑没用; 本脚本不产, 留 SOFTWARE-GAP-REPORT 阶段算)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

AUDIT = Path(__file__).resolve().parent.parent.parent / "_audit"
HOST_INV = json.loads((AUDIT / "host_inventory.json").read_text())

# 索引
HOST_ENVS: set[str] = set(HOST_INV["conda_envs"])
HOST_ENV_PKGS: dict[str, set[str]] = {
    env: set(pkgs) for env, pkgs in HOST_INV["conda_package_names"].items()
}
HOST_BIN_GLOBAL: set[str] = set(HOST_INV["binaries_global"].keys())
HOST_BIN_PER_ENV: dict[str, set[str]] = {
    env: set(bins) for env, bins in HOST_INV["binaries_per_env"].items()
}
HOST_HAS_GPU = len(HOST_INV["meta"]["gpus"]) > 0

# 跨 env 的 pkg / cli 总集 (做粗判)
ALL_PKGS: set[str] = set().union(*HOST_ENV_PKGS.values())
ALL_BINS: set[str] = HOST_BIN_GLOBAL | set().union(*HOST_BIN_PER_ENV.values())

# Fuzzy 工具名 ↔ host env name 映射:大脑写「alphafold」但 staging env 叫「af2」
# 等。规则:工具名是 env 名子串 / 别名;命中视为「专属 env 存在」。
TOOL_ENV_ALIASES: dict[str, list[str]] = {
    "alphafold": ["af2", "af2.bak"],
    "alphafold2": ["af2", "af2.bak"],
    "esm": ["esmfold"],
    "esmfold": ["esmfold"],
    "boltz": ["boltz"],
    "chai": ["chai"],
    "rfdiffusion": ["rfdiffusion"],
    "proteinmpnn": ["proteinmpnn"],
    "thermompnn": ["thermompnn"],
    "consurf": ["consurf"],
    "cellpose": ["PRAXIS-Cell"],
    "vina": ["praxis-dock"],
    "smina": ["praxis-dock"],
    "obabel": ["praxis-dock"],
    "openbabel": ["praxis-dock"],
    "rosetta": ["antibody"],   # antibody env 装了 pyrosetta
    "pyrosetta": ["antibody"],
    "kraken": ["praxis-microbiome-kraken"],
    "kraken2": ["praxis-microbiome-kraken"],
    "humann": ["praxis-microbiome-humann"],
    "humann3": ["praxis-microbiome-humann"],
    "metaphlan": ["praxis-microbiome-humann"],
    "checkm": ["praxis-microbiome-checkm2"],
    "checkm2": ["praxis-microbiome-checkm2"],
    "gtdbtk": ["praxis-microbiome-gtdbtk"],
    "dada2": ["praxis-microbiome-dada2-r"],
    "drep": ["praxis-microbiome-da", "praxis-microbiome-da-v2"],
    "dram": ["praxis-microbiome-da", "praxis-microbiome-da-v2"],
}


def fuzzy_env_for_tool(name: str) -> list[str]:
    """大脑工具名 → host env name (alias 表 + 子串)。"""
    nm = name.lower()
    out: set[str] = set()
    for env in HOST_ENVS:
        if env.lower() == nm:
            out.add(env)
        elif nm in env.lower() and len(nm) >= 4:
            # 防 "r" / "go" 等短名误判;≥4 才认子串
            out.add(env)
    out.update(TOOL_ENV_ALIASES.get(nm, []))
    # 仅保留实际存在的
    return sorted(e for e in out if e in HOST_ENVS)

# 数据路径有什么 → 摘要存
DATA_RAW = HOST_INV.get("data_paths_raw", "")


def find_pkg(name: str) -> list[str]:
    """返回拥有该 pkg 的 envs (小写比较)。"""
    nm = name.lower()
    return sorted(env for env, pkgs in HOST_ENV_PKGS.items() if nm in pkgs)


def find_bin(name: str) -> list[str]:
    out = []
    if name in HOST_BIN_GLOBAL:
        out.append("global")
    for env, bins in HOST_BIN_PER_ENV.items():
        if name in bins:
            out.append(env)
    return out


def find_data(keyword: str) -> bool:
    """粗判:数据集关键词出现在 /data 列出。"""
    return keyword.lower() in DATA_RAW.lower()


def main() -> int:
    rows: list[list] = []
    with (AUDIT / "brains_deps_inventory.tsv").open() as f:
        r = csv.DictReader(f, delimiter="\t")
        for d in r:
            brain = d["brain"]
            skill = d["skill"]
            req_type = d["req_type"]
            name = d["name"]
            source = d["source"]
            conf = d["confidence"]

            gap = "green"
            matched: list[str] = []
            sugg = ""

            if req_type == "env":
                if name in HOST_ENVS:
                    matched = [name]
                else:
                    gap = "red:env_missing"
                    # 给个建议:看 host 里有没有命名相近的
                    similar = [e for e in HOST_ENVS if name.lower().replace("-", "") in e.lower().replace("-", "")]
                    if similar:
                        sugg = f"或用相近 env: {','.join(similar[:3])}"
                    else:
                        sugg = f"建 env (或映射到 staging 现有 env)"

            elif req_type == "py_pkg":
                envs = find_pkg(name)
                if envs:
                    matched = envs
                else:
                    # 检查是否作为 cli 出现
                    cli_envs = find_bin(name)
                    if cli_envs:
                        matched = cli_envs
                        sugg = "存在为 CLI"
                    else:
                        gap = "red:pkg_missing"
                        sugg = f"pip install {name} 或 conda install -c bioconda {name}"

            elif req_type == "cli":
                cli_envs = find_bin(name)
                if cli_envs:
                    matched = cli_envs
                else:
                    # 也试着按 py_pkg 找
                    pkg_envs = find_pkg(name)
                    if pkg_envs:
                        matched = pkg_envs
                        sugg = "存在为 python 包,需 `python -m / -c` 调用"
                    else:
                        gap = "red:cli_missing"
                        sugg = f"装 {name} (apt/conda/源码)"

            elif req_type == "tool":
                # 白名单 medium - 按 pkg / cli / fuzzy env name 三层查
                pkg_envs = find_pkg(name)
                cli_envs = find_bin(name)
                fuzzy_envs = fuzzy_env_for_tool(name)
                matched = sorted(set(pkg_envs + cli_envs + fuzzy_envs))
                if not matched:
                    gap = "red:cli_missing"
                    sugg = "未发现 (低置信度提取, 可能误判)"
                elif fuzzy_envs and not pkg_envs and not cli_envs:
                    sugg = f"由 env name fuzzy 命中: {','.join(fuzzy_envs)}"

            elif req_type == "data":
                if find_data(name):
                    matched = ["data_path"]
                else:
                    gap = "red:data_missing"
                    sugg = f"拉 {name} 数据 → ~/data1/databases/{name}/"

            elif req_type == "gpu":
                if HOST_HAS_GPU:
                    matched = ["gpu_available"]
                else:
                    gap = "red:gpu_required"
                    sugg = "走 HPC bio000070 投递"
            else:
                sugg = f"未知 req_type={req_type}"

            rows.append([
                brain, skill, req_type, name, source, conf,
                gap, ",".join(matched), sugg,
            ])

    out_tsv = AUDIT / "parity_matrix.tsv"
    with out_tsv.open("w") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["brain", "skill", "req_type", "name", "source",
                    "confidence", "gap_kind", "matched_in", "suggestion"])
        w.writerows(rows)

    # 摘要
    summary = {
        "total_rows": len(rows),
        "by_gap_kind": {},
        "by_brain": {},
        "by_brain_skill_status": {},
        "skills_all_green": 0,
        "skills_any_red": 0,
    }
    for row in rows:
        gk = row[6]
        summary["by_gap_kind"][gk] = summary["by_gap_kind"].get(gk, 0) + 1
        b = row[0]
        summary["by_brain"].setdefault(b, {"green": 0, "red": 0})
        summary["by_brain"][b]["red" if gk.startswith("red") else "green"] += 1

    # 每个 skill 的状态: 任一 red → red
    per_skill_status: dict[tuple, str] = {}
    for row in rows:
        key = (row[0], row[1])
        s = per_skill_status.get(key, "green")
        if row[6].startswith("red"):
            per_skill_status[key] = "red"
        else:
            per_skill_status[key] = s if s == "red" else "green"
    summary["skills_all_green"] = sum(1 for v in per_skill_status.values() if v == "green")
    summary["skills_any_red"] = sum(1 for v in per_skill_status.values() if v == "red")

    # Top-N red name 命中频次 (装一个解锁最多 skill)
    red_name_counts: dict[tuple, int] = {}
    for row in rows:
        if not row[6].startswith("red"):
            continue
        key = (row[2], row[3])  # (req_type, name)
        red_name_counts[key] = red_name_counts.get(key, 0) + 1
    summary["top_missing"] = sorted(
        ({"req_type": k[0], "name": k[1], "count": v}
         for k, v in red_name_counts.items()),
        key=lambda x: -x["count"],
    )[:30]

    (AUDIT / "parity_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    print(f"→ {out_tsv}", file=sys.stderr)
    print(f"→ {AUDIT/'parity_summary.json'}", file=sys.stderr)
    print(f"总条数: {summary['total_rows']}", file=sys.stderr)
    print(f"by gap_kind: {summary['by_gap_kind']}", file=sys.stderr)
    print(f"skills all green: {summary['skills_all_green']} / "
          f"any red: {summary['skills_any_red']}", file=sys.stderr)
    print("Top 10 缺口:", file=sys.stderr)
    for t in summary["top_missing"][:10]:
        print(f"  {t['count']:>3}  {t['req_type']:>7}  {t['name']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
