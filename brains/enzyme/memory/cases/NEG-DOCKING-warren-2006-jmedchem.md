---
case_id: NEG-DOCKING-warren-2006-jmedchem
schema_version: 1
parent_enzyme:
  uniprot: null
  enzyme_family: methodology_critique
  cazy_family: null
  ec: null
  organism: review_anchor
  pdb: null
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: ""
  class: review_anchor / docking_critique
target_property: substrate_specificity
status: partial
provenance:
  source_type: literature
  doi: "10.1021/jm050362n"
  pmid: 17004707
  citation: "Warren GL, Andrews CW, Capelli AM, Clarke B, LaLonde J, Lambert MH, Lindvall M, Nevins N, Semus SF, Senger S, Tedesco G, Wall ID, Woolven JM, Peishoff CE, Head MS (2006). A critical assessment of docking programs and scoring functions. Journal of Medicinal Chemistry 49(20):5912-5931."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1021/jm050362n 与 PMID 17004707 我推测; CrossRef 验证"
    - "本论文是 docking program 的经典 benchmark 综评 — GlaxoSmithKline 团队系统比较 10 个 commercial / academic docking program"
    - "测试 8 个 protein-ligand 系统, 共 ~136 个 ligand; pose 准确性 + scoring 排序能力 + virtual screening 富集 三方面评估"
    - "标记反例 (NEG-) 因核心结论是: 没有任何 docking 程序在所有 target 上 acceptable; pose 准确性 vs 排序能力高度 system-dependent; scoring function 整体不可信"
    - "对 PRAXIS-Enzyme 反规则: 任何用 docking + score 直接做 substrate engineering 排序的策略需要 explicit reservoir + 实验验证"
tags: [docking, scoring_function, virtual_screening, NEGATIVE_case, failure_mode_anchor, methodology_critique, GSK_benchmark, structure_based_drug_design, system_dependent]
---

## 1. 背景与目标 — 反例性质
- 背景: docking 是 substrate / ligand 工程化与 design 的常用工具; 假设是 docking 程序能可靠 predict pose + rank 候选
- 论文 systematic 比较 10 docking 程序 (FlexX, Glide, GOLD, ICM, Surflex, DOCK, MOE, Schrodinger, etc) 在多 target 上的 pose accuracy + scoring 能力
- 反例核心: **docking 程序 system-dependent, scoring function 整体不可信, 没有 universally acceptable program**

## 2. 决策过程 (本论文是 benchmark 综评)

### 评估维度
- **Pose accuracy**: docked pose 与 X-ray crystal pose 的 RMSD (< 2 Å 是 acceptable threshold)
- **Scoring power**: docking score 与实测 binding affinity 的相关性 (Pearson r 或 ranking 准确度)
- **Virtual screening**: 在 active vs decoy 库中识别 active 的富集能力 (enrichment factor at 1% / 5% / 10%)

### 主要发现
- 各 docking 程序在不同 target 表现差异大 (~20-80% pose 准确率)
- 没有单一程序在 ALL targets 上 > 60% pose 准确率
- Scoring 能力普遍弱: docking score vs 实测 affinity Pearson r 多 < 0.5
- 同一系统不同 program 的 pose 排序结果可能完全不同
- Virtual screening enrichment factor 高度 system-dependent (1.5× 到 50×)

### 排除的位点 (★ 必填)
- 本案例为 GSK benchmark / methodology 综评, 不针对单一 enzyme 残基级排除
- Implicit 排除: 任何依赖单 docking 程序 score 排序 mutation 候选的策略, 在 anti-retrieval 索引中作为 veto
- Cofactor / 金属位 / explicit water 网络周围必须 explicit 排除于 rigid + dry docking 范畴 (anti-rule)

## 3. 失败案例 (★ 必填) — 本案例的核心

- **跨 program 一致性差**: 10 个 docking 程序对同一 ligand pose 的 prediction 可彼此 RMSD > 5 Å — 不同程序对"正确 pose"无共识
- **Scoring function 不能区分 active vs nano-active**: 多个 program 给出的 score 在 active 与弱 inhibitor 间无显著差异
- **Pose 'accurate' 不等于 'biologically relevant'**: 小分子 docking 与 X-ray pose 接近 (RMSD < 2 Å) 但不一定对应 productive binding mode
- **Flexible receptor docking 复杂度爆炸**: 多 program 用 rigid receptor 假设, 无法处理 induced fit / 大 conformational change
- **Solvent 与离子的简化处理**: 多 program 隐式 solvent + 忽略 explicit water-mediated interactions, 但 active site 多有 buried water
- **Cofactor 周围 docking 失败率特高**: P450 heme / 金属酶 active site 的 docking 准确率 < 50%
- **跨 system 'best program' 不稳定**: 系统 A 上 program X 最好, 系统 B 上 program Y 最好, 不能 transfer

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **没有 universal best docking program**: 必须在目标 system 用 known X-ray binders 校准之后再用
  - **Docking score 不直接对应 affinity**: ranking 候选用 score 不可信, 必须 + MM-PBSA / FEP / 实验
  - **Active site 的 explicit water 与 cofactor 必须保留**: rigid + dry docking 对 enzyme engineering 误导率高
  - **Pose 'visual reasonableness' 不等于 productive binding**: 必须用 X-ray validation 或 experimental binding studies
  - **Cofactor-dependent enzyme docking 准确率显著低**: P450 / 金属酶 / cofactor-dependent 系统 docking 高度警惕
- **被推翻的假设**:
  - "Docking score 是 reliable affinity estimate" — 实测 r < 0.5 对绝大多数 system
  - "用 commercial program (e.g. Glide) 自动正确" — system-dependent, 不存在 program-level 最优
- **下次类似问题应优先尝试**:
  - 任何 substrate engineering 项目用 docking 排序前, 先用 known binders X-ray pose 校准 docking method
  - 配 MM-PBSA / FEP-relative / 实验 binding 验证 top-N 候选
  - Cofactor-dependent system 必须 retain heme / metal + explicit water
- **应避免**:
  - 单 docking score 排序 ship 候选 mutation
  - rigid receptor + dry docking on 工程化项目
  - 跨 system 转移 'best program' 经验

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何 "docking + 单 score 排序工程化候选不做 X-ray 校准" 被 vetoed; 任何 "rigid docking on cofactor-dependent enzyme + 不 explicit water" 被 vetoed; 任何 "Glide / Surflex / GOLD 等 commercial docking score 直接当 affinity proxy" 被 vetoed.

## 5. 计算 / 实验原始数据
10 docking program × 8 protein system × 多 ligand × 多评估维度的 benchmark 数据见 J Med Chem 2006 supplementary; 后续 GSK / pharma 团队多次重做 benchmark (Cross 2009 等), 结论一致.
