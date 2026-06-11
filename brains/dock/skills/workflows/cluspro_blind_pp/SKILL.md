---
name: cluspro_blind_pp
description: ClusPro PIPER FFT-based blind PP docking — 6D 旋转-平移空间穷尽搜索（~70k poses）+ cluster top-30 + multi-weight 投票（balanced / electrostatic / hydrophobic / antibody）。Cluster size 是主排名信号（不是 PIPER score）。ClusPro 是 web-server 优先（无本地 binary）；通过 web API。
status: skeleton
source_case: dock-003-cluspro-blind-pp
---

# cluspro_blind_pp — FFT-based blind PP docking

## 一句话原则
**Cluster size > raw score + multi-weight 投票 (≥ 3 weight set 一致 = high conf) + 抗体走 antibody mode**.

## 输入契约

```json
{
  "receptor_pdb": "/path/to/receptor.pdb",
  "partner_pdb": "/path/to/partner.pdb",
  "weight_sets": ["balanced", "electrostatic", "hydrophobic"],
  "antibody_mode": false,
  "cluster_radius_A": 9.0,
  "use_web_api": true,
  "username": null
}
```

## 输出契约

```json
{
  "skill_id": "cluspro_blind_pp",
  "weight_sets_run": ["balanced", "electrostatic", "hydrophobic"],
  "top_clusters_per_weight": [
    {"weight": "balanced", "cluster_rank": 1, "cluster_size": 87,
     "piper_score": -1024, "model_pdb": "..."}
  ],
  "consensus_clusters": [{"appears_in_n_weights": 3, "centroid_rmsd_A": 1.8}],
  "ranking_by": "cluster_size",
  "passed_sanity": true
}
```

## ★ Sanity checks
1. **Cluster size 主排名**, NOT PIPER score
2. **Multi-weight ≥ 3** else low-confidence
3. **Antibody → antibody_mode=true** else BLOCK (case dock-004 lesson)
4. **Cluster radius 9-10 Å** sweet spot
5. **Receptor < 999 残基** for ClusPro web; 大蛋白 split domain
6. **Apo input** for benchmark; conformational change 警告

## 实现状态: skeleton
ClusPro 是 web server，无本地 binary。`run.py` 待实现：用 ClusPro REST API（需 academic registration）+ 解析返回的 cluster table。

## 引用案例
- **dock-003-cluspro-blind-pp**: 7DMU (mAb-RBD), antibody mode + multi-weight 一致 = 高置信
