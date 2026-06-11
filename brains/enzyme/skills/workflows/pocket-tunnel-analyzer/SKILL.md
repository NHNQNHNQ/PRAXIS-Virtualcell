---
name: pocket-tunnel-analyzer
description: CAVER (隧道) + CASTp (口袋) + SiteMap / FTMap (drugability) 整合, 输出底物访问通道、活性口袋、瓶颈残基分析. 给 substrate engineering / tunnel engineering / DhaA-style 工程化提供位点候选. 与 anti-rule 8 (单 docking 不可信) 联动避免 docking 误用. Hard Rule 9 强制分析门控的核心 skill 之一 (substrate-scope / activity 类工程化必跑).
---

# Pocket & Tunnel Analyzer Skill

## 一句话原则
**Substrate-scope / activity 工程化必须有 pocket / tunnel 几何分析数据**, 不允许 design agent 凭 active-site 同心球 5 Å 内随机选位点. 与 anti-rule 8 (单 docking score 不可信) 联动避免 docking misuse.

## 适用阶段
Design Agent 在涉及 substrate-scope expansion / regioselectivity switching / tunnel engineering 任务时**强制调用**. thermostability 工程化非必须 (但仍推荐).

## 先检查环境
```bash
which caver_analyst caver       # CAVER (Damborsky lab tunnel analysis)
# 替代: PyMOL plugin 'CAVER 3.0' 或 PyCaver Python 接口
which fpocket                    # FPocket (Le Guilloux 2009) — pocket detection
which schrodinger sitemap 2>/dev/null   # SiteMap (商业) — drugability
# Python: PyKVFinder / PocketFinderPlus
python -c "import pykvfinder" 2>&1 || pip install pyKVFinder
```

## 输入契约
```json
{
  "pdb_path": "/Volumes/T7/EnzymeAgent/data/pdb/1cel.cif",
  "chain": "A",
  "active_site_residues": [212, 217],         // 来自 catalytic-site-annotator
  "ligand_smiles": "C(C(C(C(C(CO)O)O)O)O)O",  // 当前 / 目标底物 SMILES
  "tunnel_analysis_method": "caver",           // caver / pyKVFinder / mole2
  "tunnel_min_radius": 1.4,                    // Å, 0.9 (water) / 1.4 (small molecule) / 2.5 (sugar)
  "n_tunnels": 5,                               // 输出 top-N 隧道
  "do_pocket_analysis": true,                   // CASTp / FPocket
  "do_drugability_score": false                 // SiteMap (需商业 license)
}
```

## 输出契约
```json
{
  "skill_id": "pocket-tunnel-analyzer",
  "msa_path": "",
  "n_sequences": 0,
  "conservation_csv": "",
  "diagnostics": {
    "brain": "enzyme",
    "archetype": "msa_conservation"
  }
}
```

## 关键准则 (★ 强制)
1. **Tunnel 半径与底物半径必须匹配**: 计算底物 RDKit 最小 enclosing radius vs 隧道 min radius; 不匹配 → 工程化目标为 widening
2. **Bottleneck 残基**: 隧道半径最小的 1-3 个位点是 tunnel engineering 第一目标 (DhaA / P450 BM3 类经典案例)
3. **Pocket lining 分类**: 催化 / 芳香 stacking / polar / shape-defining 四类——每类的工程化策略不同
4. **多 ligand 比较**: 当前底物 vs 目标底物的 fingerprint 与几何对齐, 给出"扩谱所需位点"
5. **不可乱动区列表**: 与 catalytic-site-annotator + structural-context-analyzer 的输出取并集

## 与上下游的衔接
- **上游必跑**:
  - `pdb-fetcher` → PDB 结构
  - `catalytic-site-annotator` → active_site_residues + 不可乱动区
  - `structural-context-analyzer` → loop / RSA 上下文
- **本 skill 输出供下游**:
  - `esm-mutation-scan` → 在 tunnel 与 pocket 残基上跑 PLM scoring
  - `pyrosetta-stability-scan` → 在 tunnel widening 候选上跑 ΔΔG
  - `proteinmpnn-design-skill` → pocket reshape 时可用 inverse folding

## 失败模式与排查
| 现象 | 根因 | 解法 |
|---|---|---|
| CAVER 找不到隧道 | active site 在表面 / 浅 pocket | 标 'surface_active_site', 跳隧道分析 |
| 隧道太多 (> 10) | 蛋白多孔 | 按 importance 排序, 取 top-3 |
| 底物 SMILES 错 | RDKit 解析失败 | catalytic-site-annotator 给出 product 类用作 fallback |
| 隧道半径异常大 | PDB 缺侧链 / 多构象 | 取 dominant conformation, 报告 std |
| 多 binding mode | substrate 有多个有效结合姿态 | 输出多个 top mode + 说明依赖姿态 |

## 与 Anti-rule 的关联
- **Anti-rule 8 (单 docking score 不可信)**: 本 skill 提供几何先验, 防止纯 docking 排序; design agent 在 substrate engineering 必须基于本 skill 输出而非 docking score
- **Anti-rule 4 (AF + PyRosetta)**: AF model 上跑本 skill 时, 隧道半径误差 ~0.3 Å; 输出加 warning

## 引用与出处
- Chovancova E et al. "CAVER 3.0: A Tool for the Analysis of Transport Pathways in Dynamic Protein Structures." PLoS Comput Biol 2012;8:e1002708.
- Le Guilloux V, Schmidtke P, Tuffery P. "Fpocket: An open source platform for ligand pocket detection." BMC Bioinformatics 2009;10:168.
- Pavelka A et al. "CAVER Analyst 2.0: Analysis and Visualization of Channels and Tunnels in Protein Structures and Molecular Dynamics Trajectories." Bioinformatics 2018;34:3586-3588.
- Halgren TA. "Identifying and characterizing binding sites and assessing druggability." J Chem Inf Model 2009;49:377-389. (SiteMap)
- Damborsky J, Brezovsky J. "Computational tools for designing and engineering enzymes." Curr Opin Chem Biol 2014;19:8-16. (DhaA tunnel engineering reference)

## Skill 版本
v1.0, 2026-04-29.
