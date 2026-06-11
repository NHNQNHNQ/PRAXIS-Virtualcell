---
case_id: NEG-ESMFOLD-MONOMER-FALSE-POSITIVE
neg_pattern: esmfold_monomer_plddt_alone_for_binder_quality
design_task: de_novo_binder
target_pdb: 4Z18
target_uniprot: Q9NZQ7
fold_class: any
length_range: 50-100
tools: [ESMFold, RFdiffusion, ProteinMPNN, AlphaFold-Multimer]
key_paper_doi: 10.1038/s41467-023-38328-5
key_metrics:
  evidence_source: "PRAXIS-self-generated case-034 (28-design PDL1 campaign 2026-05)"
  esmfold_pre_filter_pass_rate: "91.5% pLDDT >= 80"
  af2_multimer_real_pass_rate: "32.1% (5-metric)"
  false_positive_rate: "~60% of ESMFold-pass designs FAIL AF2-Multimer"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, ESMFold, monomer-pLDDT, binder, false-positive, multi-modality-violation]
unverified_details: []
---

# NEG: 用 ESMFold 单 modality pLDDT 当 binder quality 标杆是反模式

## What this NEG case captures
单纯用 ESMFold 单体 pLDDT (binder fold-only) 作为 binder candidate 排序或筛选信号 — **强反模式**。设计 0079, 0089, 0150, 0170, 0015 在 PRAXIS-Protein case-034 真验证中均 ESMFold pLDDT ≥ 93 但 AF2-Multimer iPTM 0.21-0.40。

## ★ 失败模式
- ESMFold 单跑 binder 序列 → pLDDT 高（91-94）但完全不知 binder 在 target 表面是否合身
- 91.5% 的 ESMFold-pre-filter pass 中只有 ~32% 通过真正的 AF2-Multimer 5-metric (case-034 真数据)
- ESMFold over-confident on Ala/Glu/helical-pattern 序列（自带 fold prior bias）
- 单 modality validation 违反 rule 09

## ★ 排除/禁止
- 不允许 "ESMFold pLDDT > 80 → 直接 in vitro test" 的 candidate flow
- 不允许 ESMFold 作为 final filter，必须 AF2-Multimer 复验
- 不允许在 binder report 中只 cite ESMFold 数据

## ★ 方法选择决策链（反向）
- 正确 flow: RFdiff → MPNN → ESMFold (cheap pre-filter, throughput) → AF2-Multimer (true binder quality bar)
- 错误 flow: RFdiff → MPNN → ESMFold → ship to lab (this NEG anchors against)

## ★ In silico vs in vitro 差距
- ESMFold 91.5% pass → AF2-Multimer 32% real → in vitro 期望 5-15% (per case 002 / 018)
- ESMFold-pre-filter 节省 time 但**绝不替代** AF2-Multimer 验证

## Anti-pattern triggered
**anti-rule 4** (single-method binder ranking) + **anti-rule 10** (top-1 ship without experimental check) — 等价于"AF model + 单一方法 ddG (例如 PyRosetta cartesian_ddg) 单跑"的 protein-binder 版本

## Evidence cases
- protein-034 (PRAXIS self-generated, 真数据)
- protein-002 (Watson 2023 RFdiff, 5-metric mandatory)
- protein-010 (Cao 2022 binder validation post-mortem)
- protein-018 (Bennett 2023 DL-improved filter)
