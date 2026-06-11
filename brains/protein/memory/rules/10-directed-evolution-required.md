---
rule_id: 10-directed-evolution-required
schema_version: 1
applies_to:
  design_tasks: ["enzyme_de_novo_design", "de_novo_binder", "antibody_design"]
  fold_classes: ["ALL"]
evidence_cases:
  - "protein-011-cao2020-lcb-spike-binder"
  - "protein-012-chevalier2017-flu-ha-mini-binder"
  - "protein-020-yeh2023-de-novo-luciferase"
  - "protein-025-mason2021-antibody-specificity-dl"
  - "protein-029-siegel2010-diels-alderase"
  - "protein-030-jiang2008-retro-aldolase"
confidence: high
last_updated: 2026-05-01
---

## 规则
**De novo enzyme + binder + antibody affinity-improvement 项目必须包含 directed evolution (DE) 阶段**——raw computational design 通常 sub-optimal，需要 site-saturation mutagenesis (SSM) + selection 多轮提升 100-1000x。

任务-specific 推荐：
| 任务 | Raw computational 性能 | DE 后达到 | 必须 DE 轮数 |
|---|---|---|---|
| De novo enzyme | kcat/KM ~10^-3-10^-1 M⁻¹s⁻¹ | ~10²-10⁴ M⁻¹s⁻¹ | 2-3 rounds SSM + select |
| De novo mini-binder (raw) | KD μM-mM | KD nM-pM | 1-2 rounds SSM (Cao 2020 LCB 需要选, Chevalier 2017 yeast display 内嵌 selection) |
| Antibody affinity maturation | KD initially nM | KD pM (post-DE) | 1-3 rounds CDR-H3 SSM |

报告必须 include:
- DE plan (SSM strategy, library size, selection method)
- Expected affinity / activity improvement based on cohort literature
- Resource estimate (rounds × library size × time)

## 依据
- **protein-011 (Cao 2020 LCB)**：Raw RIF + Rosetta design 多数 micromolar；最终 picomolar (LCB1 100 pM) 必须 selection (yeast / phage display)；论文中后续 SSM 提升进一步
- **protein-012 (Chevalier 2017)**：Yeast display + FACS selection 自带 DE 性质；raw design 大多数 μM；matured 选 nM
- **protein-020 (Yeh 2023 luciferase)**：Raw design kcat ~10⁻³/s；directed evolution 后续工作 100-1000x 提升；论文明确"DE 必要"
- **protein-025 (Mason 2021 antibody specificity DL)**：100 individual variants from ~1000 DL-predicted；single-round DE 后已经覆盖 specificity 改进
- **protein-029 (Siegel 2010 DA)**：DA-20 raw kcat/KM ~0.04 M⁻¹s⁻¹；后续 Khersonsky DE 提升 ~300x
- **protein-030 (Jiang 2008 retro-aldol)**：RA-22 raw kcat/KM 0.74；Althoff 2012 + Giger 2013 DE 提升 ~10⁴ to industrial level

## 边界 (★ 必填)
- **Stabilization 任务 (case 003, 023, 024)**：design 直接给 stable variant，no DE typically required (PROSS / FireProt 直接给 +5-12°C Tm)
- **Cyclic peptide fold-only (case 013, 014)**：100% fold success；no DE needed at fold-design stage（cyclic peptide drug 后续可能优化 PK 但不在 fold scope）
- **Symmetric assembly fold-only (case 031, 033)**：直接 stable cage；no DE needed at design stage
- **Hallucination / generative (case 015, 022)**：fold-only 任务，no functional metric for DE
- **Already-mature antibody (case 026 Hie)**：affinity ceiling 接近；single-round PLM scoring 提升 2-7x 已是 max；多 round DE diminishing returns
- **Computational enzyme design with Lipsh-Sokolik / RFdiffusion-AA 时代**：raw catalysis 比 2008-2010 强，但 DE 仍 typically 必要

## How to apply
- **Scoping**：enzyme/binder/antibody-affinity-maturation 任务的 strategy 必须含 `directed_evolution_plan` 字段
- **Design**：design_plan 必须 outline (a) SSM library scope, (b) selection method (display / activity assay), (c) expected improvement multiplier
- **Execution**：computational design 不直接 commit lab；report includes DE recommendation
- **Reporting**：top-N candidates 表必须含 `expected_DE_improvement` 列 (basis: cohort literature)
- **Reviewer**：检测 (a) enzyme/binder report 缺 DE plan → block; (b) "industrial-grade" claim 但 raw kcat < 10/s → block 直到 DE
