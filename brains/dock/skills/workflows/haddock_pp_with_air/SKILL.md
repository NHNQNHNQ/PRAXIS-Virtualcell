---
name: haddock_pp_with_air
description: HADDOCK 2.4 PP docking with Ambiguous Interaction Restraints (AIR) — 三阶段 it0 / it1 / itw + cluster top-200 + cluster_size 主排名（不是 raw score）。AIR active+passive ≤ 30 enforce。HADDOCK 2.4 二进制需用户单独 license（远程或本地装），通过 SSH bridge。
status: usable
source_case: dock-002-haddock-pp-restraints
---

# haddock_pp_with_air — Protein-Protein docking with experimental restraints

## 一句话原则
**AIR active+passive ≤ 30 + cluster_size 主排名 + apo input + CAPRI quality 必报**。无 AIR 的 HADDOCK 不该跑（成功率 < 30%）。

## 适用阶段
Stage 3 (Execution) — `docking_type == protein_protein_with_restraints`.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "partner_pdb": "/path/to/partner.pdb",
  "air": {
    "active_receptor": [12, 15, 17],
    "passive_receptor": [10, 11, 16, 18, 19, 20],
    "active_partner": [99, 100, 101],
    "passive_partner": [98, 102, 103]
  },
  "max_air_residues": 30,
  "n_models_it0": 1000,
  "n_models_it1": 200,
  "n_models_itw": 200,
  "cluster_radius_A": 5.0,
  "remote_gpu": false,
  "use_haddock3": false,
  "out_dir": "/runs/{tid}/haddock_pp_with_air/"
}
```

## 输出契约

```json
{
  "skill_id": "haddock_pp_with_air",
  "version": "HADDOCK 2.4",
  "stages_run": ["it0", "it1", "itw"],
  "n_models_per_stage": {"it0": 1000, "it1": 200, "itw": 200},
  "clusters": [
    {"cluster_rank": 1, "cluster_size": 23, "haddock_score": -120.4,
     "interface_rmsd_A": 1.8, "ligand_rmsd_A": 2.1,
     "representative_pdb": "/runs/{tid}/haddock_pp_with_air/cluster1_rep.pdb"}
  ],
  "ranking_signal": "cluster_size",
  "capri_quality_top_cluster": "medium",
  "passed_sanity": true,
  "provenance": {"command": "...", "runtime_sec": 4231.5}
}
```

## ★ 强制 sanity checks (case dock-002 lessons)

1. **AIR active + passive ≤ 30**：超过则约束被淹没，效果同 blind → SanityFail
2. **AIR 必须存在**：无 AIR 不允许跑 HADDOCK（即使 user 强制也 SanityFail，提示用 ClusPro blind）
3. **Apo input recommended for benchmark**：检测 receptor 是否含 partner co-crystal（chain count > expected）→ warn "信息泄漏"
4. **Cluster size > raw score**：top-1 by score 经常 outlier；ranking 必须按 cluster_size
5. **CAPRI quality 必报**：interface_RMSD 与 ligand_RMSD 必算并贴标签 high/medium/acceptable/incorrect
6. **Conformational change 警告**：若 receptor + partner 有已知 apo→holo RMSD > 3 Å → confidence_label=low

## 实现状态: usable (binary 依赖 license)
- `run.py` 完整可跑：subprocess 调用 HADDOCK 2.4 CLI；可远程通过 SSH bridge
- HADDOCK 2.4 license: https://www.bonvinlab.org/software/haddock2.4/ (academic free + registration)
- HADDOCK3 fallback：`use_haddock3=true` 切到新版（需 `haddock3` Python 包）
- 本地缺 HADDOCK binary 时 raise EnvUnavailable + 给安装命令

## 引用案例
- **dock-002-haddock-pp-restraints**: BPTI-trypsin (1AVX) benchmark, AIR-driven 60-80% success rate vs blind < 30%
- 失败模式: conformational change (kinase activation loop, antibody CDR), interface symmetry, multiple binding modes, IDR in interface, glycosylation, allosteric mechanisms
