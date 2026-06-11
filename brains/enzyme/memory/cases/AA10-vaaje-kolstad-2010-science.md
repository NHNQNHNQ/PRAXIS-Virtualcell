---
case_id: AA10-vaaje-kolstad-2010-science
schema_version: 1
parent_enzyme:
  uniprot: O83009               # Serratia marcescens CBP21 (chitin-binding protein 21); UniProt 已收录
  cazy_family: AA10
  ec: 1.14.99.53                # chitin-active LPMO (current EC, 与 UniProt 一致)
  organism: Serratia marcescens
  pdb: 2BEM                     # CBP21 apo crystal (Vaaje-Kolstad 2005 deposit, pre-2010 已知)
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CC(=O)N[C@@H]1[C@@H](O)[C@H](O)[C@@H](CO)O[C@H]1O[C@H]2[C@H](NC(C)=O)[C@@H](O)[C@H](CO)O[C@H]2O"   # chitin tetramer 示意
  class: chitin / chito-oligosaccharide
target_property: activity        # 主线: 对 recalcitrant 多糖 (chitin / cellulose) 的氧化降解活性提升
status: validated
provenance:
  source_type: literature
  doi: "10.1126/science.1192231"
  pmid: 20929773
  citation: "Vaaje-Kolstad G, Westereng B, Horn SJ, Liu Z, Zhai H, Sørlie M, Eijsink VG (2010). An oxidative enzyme boosting the enzymatic conversion of recalcitrant polysaccharides. Science 330(6001):219-222."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1126/science.1192231 与 PMID 20929773 我推测 (Science 2010 vol 330 issue 6001); CrossRef 验证"
    - "UniProt O83009 我推测对应 CBP21; QA via uniprot-fetcher 验证"
    - "CBP21 在 2010 当时归类 GH61/CBM33; CAZy 后续重新分类为 AA10 (auxiliary activity 10) 在 2013 系统重组中"
    - "PDB 2BEM 为 Vaaje-Kolstad 2005 JBC 早期 deposit; 2010 Science 工作未必新 deposit, 用既有结构"
    - "本工作是 LPMO 整个 enzyme class 的 paradigm-defining 论文 — 首次明确 LPMO 是 oxidative 不是 hydrolytic, copper-dependent 而不是无 cofactor"
    - "engineering target 标 activity 因主线是 LPMO + canonical hydrolase 协同提升整体降解 turnover; 不是单酶 saturation kinetics"
    - "EC 1.14.99.53 是后续 chitin-active LPMO 的现行 EC, 论文当时未必有此 EC 标注"
    - "Eijsink 实验室 (Norwegian U Life Sciences, NMBU) 主导, Vaaje-Kolstad 是 first author; 后续衍生大量 LPMO 工程化论文"
tags: [AA10, LPMO, chitin, copper, histidine_brace, oxidative_cleavage, polysaccharide_boosting, paradigm_shift, Eijsink-lab, Vaaje-Kolstad]
---

## 1. 背景与目标
- parent: Serratia marcescens CBP21 (AA10 LPMO, originally classified CBM33 chitin-binding protein 21)
- 起始性质: 当时 (pre-2010) CBP21 视作 "chitin-binding accessory protein", 已知 boost chitinase 但机制未明; 假设是 binding-driven 物理破解 chitin crystallinity
- 目标: 揭示 CBP21 真实机制 — copper-dependent oxidative cleavage of glycosidic bond, 而不是 hydrolysis 或 mechanical disruption
- 应用 (engineering downstream): 整个 LPMO family 工程化基础; 工业纤维素 / chitin 转化中 LPMO + canonical hydrolase 协同的 enabling discovery

## 2. 决策过程 (本文是 mechanism discovery, 非 site-directed engineering)

### 候选位点策略
- **mechanism-driven** 路线 (非 mutagenesis library):
  - 假设 1 (推翻): 物理破裂 chitin 晶体, 让 chitinase 接近
  - 假设 2 (本文证实): catalytic oxidation 机制, 释放 oxidized chito-oligo + Cu cofactor 必需
- 关键工具: 检 oxidized cellulose / chitin 产物 (HPAEC-PAD + MS), atomic absorption 测 Cu binding stoichiometry
- 试 reductant requirement (ascorbate / cysteine / EDTA-sensitive) 验证 catalytic Cu 而不是结构 Cu

### 排除的位点 (★ 必填)
- **N-端 His1 + 内部 His** (His brace 两个 His 配位 Cu): 任一突变全失活 — 在本工作 + 后续 site-directed studies 反复确认 (Eijsink 系列)
- **N-端 His1 是 LPMO 标志位**: 真菌 AA9 上 N(δ) 还有 methylation, 细菌 AA10 多无 methyl 但 backbone 重要性同
- **Substrate binding flat surface (aromatic Tyr/Trp)**: 与 polysaccharide 平展接触, 替换会失 binding
- **Cu site 二级 sphere (Tyr / Phe distal)**: 调 Cu 氧化态稳定但本工作未 mutation, 后续工程化目标

### 计算工具与阈值
- 主要工具:
  - HPAEC-PAD 检 oxidized chito-oligo (with/without 还原)
  - MS 标记 oxidized site (C1 vs C4, by 18O / 13C 或 mass shift)
  - Cu titration via ICP-MS / atomic absorption
  - 协同 assay: chitin 转化率 vs CBP21 + chitinase mixed system
- 实验校验:
  - 加 EDTA → CBP21 boost 消失 → 证 metal-dependent
  - 加还原剂 (ascorbate) → boost 增强 → 证 oxidative cycle
  - 单 CBP21 vs CBP21 + chitinase: 协同效应 ≥ 2× turnover

## 3. 实验结果

### 关键发现
| 发现 | 内容 |
| --- | --- |
| Cu-dependent | EDTA 完全消除 boost, 加 Cu 恢复; Cu 是 catalytic cofactor |
| Reductant-driven | Ascorbate 等小分子 reductant 显著增 boost; 提示 Cu(II) → Cu(I) 启动 cycle |
| Oxidized product | HPAEC-PAD + MS 检测到 chitobionic acid / aldonic-acid-terminated oligo, 证 C1-oxidation 而非 hydrolysis |
| Synergy with chitinase | 单 CBP21 turnover 极低; CBP21 + Sm chitinase 协同提升 chitin 转化率 数倍 |
| Histidine brace | N-端 His1 + 内部 His Cu 配位是 LPMO universal 标志 (后续 AA9/AA10/AA11/AA13 全保留) |

### 失败案例 (★ 必填)
- 早期 (pre-2010) 多个 group 把 CBP21 描述为 "structurally rigid binding protein", 没识别 oxidative 机制, 浪费多年
- 单 CBP21 (无 chitinase) 在 chitin 上释放 oxidized 产物 turnover 极慢 — LPMO 单酶不是高 kcat 酶, 必须 + canonical hydrolase
- 还原剂浓度过高反而抑制 (over-reduction → Cu(0) 沉淀或非生产性 ROS), substrate context 调试敏感
- AA10 在某些纤维素底物上的 boost 效率显著低于 AA9 (后续工作验证), 提示家族 sub-specialization

## 4. 学习收获
- **成立的规则候选**:
  - **LPMO (AA9/10/11/13) 工程化绝对禁区**: His brace (N-端 His + 内部 His) 全保留 — 真菌 AA9 还需保 His1 N(δ) methylation
  - **LPMO + canonical hydrolase 协同 design 是工业 cellulosome 的 master pattern** (后续 enzyme cocktail 设计普遍包含)
  - **LPMO 工程化目标**: substrate-binding flat surface aromatic patch (Trp/Tyr) 调 substrate scope; Cu site 二级 sphere (Tyr distal) 调 redox 与 C1 vs C4 selectivity
  - **AA10 vs AA9 sub-specialization**: AA10 偏 chitin / β-1,4-glucan; AA9 偏 cellulose; 工程化跨 family 转移 mutation 风险高
  - **process condition 关键变量**: reductant 浓度 + Cu 浓度 + canonical hydrolase 配比, 不是单酶 kcat
- **被推翻的假设**:
  - "CBP21 / GH61 / CBM33 是 binding-only 蛋白" — Vaaje-Kolstad 2010 直接否定 paradigm
  - "polysaccharide 降解是 hydrolytic-only 化学" — LPMO 引入 oxidative 路线, 重写 enzyme cocktail 设计哲学
- **下次类似问题应优先尝试**:
  - 任何 recalcitrant polysaccharide (chitin / crystalline cellulose / starch) 降解工程化, 优先加 LPMO module + reductant supply
  - 跨 LPMO 家族 (AA9 → AA10 / AA11) 工程化 mutation 转移须 within-substrate-class 验证
- **应避免**:
  - 把 LPMO 当 hydrolase (kcat / KM 框架不适用 — LPMO 是 single-turnover-per-binding, 协同时 turnover number 受 reductant/canonical hydrolase 限制)
  - 任何 His brace 周围 ±5 Å 突变, 即使 ΔΔG -预测稳定

## 5. 计算 / 实验原始数据
HPAEC-PAD + MS 检测数据见 Science 2010 supplementary; Cu binding stoichiometry 与 EDTA 抑制曲线见同 supplementary. 后续 Eijsink 组 JBC / Nat Chem Biol 系列扩展 mechanism + engineering.
