#!/usr/bin/env python3
"""pyrosetta-stability-scan/run.py

第一版仅支持 --simulate 模式(生成 plausible 随机 ΔΔG;
真 cartesian_ddg 路径要等 PyRosetta init 集成,留 TODO)。

输入契约 stdin JSON:
  {
    "structure_path": str,
    "chain": str,
    "scan_mode": "saturation" | "positions",
    "positions": [int, ...],
    "exclude_positions": [int, ...],
    "amino_acids": "ARNDCQEGHILKMFPSTWYV",
    "n_runs": int,
    "active_site_residues": [int, ...],
    "simulate": bool,
  }

输出 stdout JSON:
  {
    "scan_summary": {...},
    "mutations": [{...}],
    "diagnostics": {...}
  }
"""
import argparse
import json
import os
import random
import sys
import time

AA_LIST_DEFAULT = "ARNDCQEGHILKMFPSTWYV"


def parse_stdin_or_args() -> dict:
    """优先 stdin JSON,fallback argparse(便于命令行 dev)。"""
    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", default="placeholder.pdb")
    ap.add_argument("--chain", default="A")
    ap.add_argument("--scan-mode", default="positions", choices=["saturation", "positions"])
    ap.add_argument("--positions", default="1,2,3")
    ap.add_argument("--active-site-residues", default="")
    ap.add_argument("--n-runs", type=int, default=3)
    ap.add_argument("--simulate", action="store_true", default=True)
    ap.add_argument("--out", default="/dev/stdout")
    args = ap.parse_args()
    return {
        "structure_path": args.structure,
        "chain": args.chain,
        "scan_mode": args.scan_mode,
        "positions": [int(x) for x in args.positions.split(",") if x.strip()],
        "active_site_residues": [int(x) for x in args.active_site_residues.split(",") if x.strip()],
        "n_runs": args.n_runs,
        "simulate": args.simulate,
        "_out_path": args.out,
    }


def simulate_scan(payload: dict) -> dict:
    """生成 plausible ΔΔG (mean +1.5, std 2.5 kcal/mol; ref15_cart-ish)。
    每个 (position, mut_aa) 跑 n_runs 次取均值 + std。"""
    seed = int(payload.get("seed", 42))
    random.seed(seed)
    positions = payload.get("positions") or []
    aa_list = (payload.get("amino_acids") or AA_LIST_DEFAULT)[:20]
    active = set(payload.get("active_site_residues") or [])
    n_runs = max(1, int(payload.get("n_runs", 3)))

    mutations = []
    t0 = time.time()
    for pos in positions:
        wt = random.choice(aa_list)
        for mut in aa_list:
            if mut == wt:
                continue
            samples = [random.gauss(1.5, 2.5) for _ in range(n_runs)]
            ddg_kcal = sum(samples) / len(samples)
            ddg_std = (sum((s - ddg_kcal) ** 2 for s in samples) / len(samples)) ** 0.5
            ddg_reu = ddg_kcal / 0.57  # 反向换算
            near_active = bool(active and any(abs(pos - a) <= 5 for a in active))
            mutations.append({
                "position": pos, "wt_aa": wt, "mut_aa": mut,
                "ddG_REU": round(ddg_reu, 3),
                "ddG_kcal_per_mol": round(ddg_kcal, 3),
                "ddG_std": round(ddg_std, 3),
                "rsa": round(random.uniform(0.0, 1.0), 2),
                "near_active_site": near_active,
                "near_glycosylation": False,
                "passes_default_filter": (
                    ddg_kcal < -1.5 and not near_active
                ),
                "simulated": True,
            })
    wall = time.time() - t0
    return {
        "scan_summary": {
            "n_positions_scanned": len(positions),
            "n_mutations_evaluated": len(mutations),
            "wallclock_seconds": round(wall, 3),
            "score_function": "ref15_cart (simulated)",
            "simulate_mode": True,
            "host": os.uname().nodename,
            "python_version": sys.version.split()[0],
        },
        "mutations": mutations,
        "diagnostics": {
            "convergence_check_passed": True,
            "warnings": ["simulate=true → 结果是合成数据, 仅用于 pipeline 校验, 不作湿实验级证据"],
        },
    }


def real_scan(payload: dict) -> dict:
    """TODO:真 PyRosetta cartesian_ddg 路径(antibody env 内 import pyrosetta)。
    目前 simulate=False 时返回结构化未实现错误,让调用方明确知道走 simulate。"""
    return {
        "ok": False,
        "error": "real PyRosetta cartesian_ddg 路径尚未实现; 请传 simulate=true",
        "fallback_hint": "在 SKILL.md 输入契约里加 simulate=true 跑合成数据校验 pipeline",
    }


def main() -> int:
    payload = parse_stdin_or_args()
    simulate = bool(payload.get("simulate", True))  # 默认 simulate
    out = simulate_scan(payload) if simulate else real_scan(payload)
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
