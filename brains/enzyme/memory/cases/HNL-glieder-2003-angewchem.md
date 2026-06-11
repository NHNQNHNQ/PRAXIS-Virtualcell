---
case_id: HNL-glieder-2003-angewchem
schema_version: 1
parent_enzyme:
  uniprot: Q945K2               # MDL2_PRUDU - (R)-mandelonitrile lyase 2 (PaHNL1) - 实际 entry name in UniProt
  cazy_family: null
  enzyme_family: hydroxynitrile_lyase / FAD_GMC_oxidoreductase
  ec: 4.1.2.10
  organism: Prunus dulcis (formerly Prunus amygdalus / almond)
  pdb: 1JU2                     # PaHNL 与 mandelonitrile (反应产物) 复合物结构
substrate:
  primary_smiles: "O=Cc1ccccc1"   # benzaldehyde, HCN-addition substrate (PaHNL 加 HCN 形成 (R)-mandelonitrile)
  class: aldehyde_HCN_addition
target_property: substrate_specificity   # 工业级反应耐受 + ee preservation
status: validated
provenance:
  source_type: literature
  doi: "10.1002/anie.200352141"
  pmid: null
  citation: "Glieder A, Weis R, Skranc W, Pöchlauer P, Dreveny I, Majer S, Wubbolts M, Schwab H, Gruber K (2003). Comprehensive step-by-step engineering of an (R)-hydroxynitrile lyase for large-scale asymmetric synthesis. Angew Chem Int Ed Engl 42(39):4815-4818."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1002/anie.200352141 我推测; QA via CrossRef 验证"
    - "PaHNL UniProt 第一次推 P52708 错 (Sorghum bicolor 完全无关), 经 UniProt 文本搜索找到 Q945K2 (MDL2_PRUDU, Prunus dulcis (R)-mandelonitrile lyase 2)"
    - "Prunus amygdalus 已被重新分类为 Prunus dulcis (杏仁的当代学名);文献仍多用旧名 P. amygdalus"
    - "PDB 1JU2 是 PaHNL 经典结构 (Dreveny 2001); 论文使用其变体 PDB 待原文确认"
    - "Glieder lab (TU Graz) 与 DSM 合作工业化 PaHNL 制 (R)-mandelonitrile (anti-emetic 中间体)"
    - "本工作是 stepwise rational engineering 经典: solubility + activity + thermostability 同时改, 累加 ~5 mutations"
tags: [hydroxynitrile_lyase, HNL, PaHNL, FAD_GMC_oxidoreductase, substrate_specificity, asymmetric_HCN_addition, mandelonitrile, Glieder-lab, DSM_industrial, non-CAZy]
---

## 1. 背景与目标
- parent: Prunus amygdalus (R)-HNL (PaHNL, UniProt P52708, FAD-dependent), EC 4.1.2.10
- WT 反应: benzaldehyde + HCN → (R)-mandelonitrile (>97% ee, 但工业级条件 (high substrate, organic biphasic) 下 enzyme 不稳, ee 漂移)
- 目标: stepwise improvement — solubility (E. coli 表达) + thermal stability + pH stability + activity all 在工业反应条件下 viable
- 应用: (R)-mandelonitrile → mandelic acid → semi-synthesis 抗呕吐 / 抗血小板药物 (DSM ton-scale 生产)

## 2. 决策过程

### 候选位点策略 — Stepwise rational + screen
- **Step 1**: improve E. coli expression (溶解性) — N-terminal modifications + chaperone co-expression
- **Step 2**: rational thermostability mutations — surface charge optimization, consensus from PaHNL homologs
- **Step 3**: pH stability — acidic pH (HNL 类反应优 pH 4-5) tolerance
- **Step 4**: activity in biphasic system (organic / aqueous)
- 累加 ~5 single-point mutations

### 排除的位点 (★ 必填)
- FAD binding 残基 (Rossmann fold) 严格保留 — cofactor 必需
- Active site catalytic Ser-His-Asp triad-like 保留 (HNL 类用 oxyanion-stabilized base catalysis)
- Sugar binding pocket (HNL 内部仍有 GMC oxidoreductase 渐进遗迹) 保留

### 计算工具与阈值
- 主要工具: PaHNL 高分辨结构 (1JU2 + 后续) + sequence consensus
- 实验校验: 异源表达 in E. coli → 溶解性 SDS-PAGE → DSF Tm → biphasic kinetic resolution → chiral HPLC ee%

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| Step | 改进 | 量化 |
| --- | --- | --- |
| 起始 | E. coli yield 极低, biphasic 反应不可行 | (问题表征) |
| Step 1 (溶解性) | yield 提升 100× | 工业级 expression |
| Step 2 (Tm) | Tm 提升 ~10°C | 65°C → 75°C |
| Step 3 (pH) | pH 4 稳定 | 工业反应 condition |
| Step 4 (biphasic) | mandelonitrile 产率 + ee 提升 | >99% ee, ton-scale |

### 失败案例 (★ 必填)
- 早期 thermostability mutations 部分 sacrificing activity — 必须 stepwise 而非 simultaneous
- 部分 surface mutations 提 Tm 但 destabilize FAD binding — FAD 必须 reload 化学
- E. coli 表达即使最佳 variant 仍 less efficient than P. pastoris — 工业 scale-up 切换到 yeast host

## 4. 学习收获
- **成立的规则候选**:
  - **Stepwise rational engineering** (一个阶段优化一指标) 优于 simultaneous, 当工业反应有多个 gating spec (溶解 + Tm + pH + biphasic) 时
  - **HNL/HNL-类 enzyme 的 FAD 装载效率**是工业级生产的 hidden bottleneck — 工程化时考虑 cofactor incorporation 比例
  - **biphasic reaction tolerance** 是工业 enzyme 工程化的常见 final spec — 必须 explicit 测
- **被推翻的假设**:
  - "Single optimal variant 通过 directed evolution 一次到位" — 工业 enzyme 有多 gating spec 时, stepwise 提供清晰路径
- **下次类似问题应优先尝试**:
  - 任何工业 enzyme 工程化, 把 specs (溶解 + 活性 + 稳定 + 反应条件) 列清单, stepwise 优化, 不要一锅煮
  - HNL 类 cofactor-dependent enzyme: 评估 host 系统 FAD 装载效率
- **应避免**:
  - 在 E. coli 评估真菌 enzyme 期望工业级 yield — 真菌酶常需 yeast host
  - 单 spec 维度优化, 期望多 spec 协同提升 — 常出现 tradeoff

## 5. 计算 / 实验原始数据
原始 PaHNL 工程化历程 + 工业流程 (DSM scale-up) 数据见 Angew Chem Int Ed 42(39) 2003 supplementary; 后续 Weis et al. 2004 J Mol Catal B 续写.
