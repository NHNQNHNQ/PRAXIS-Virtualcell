---
case_id: NEG-IPTM-AS-AFFINITY
neg_pattern: iPTM_treated_as_quantitative_binding_affinity
design_task: complex_prediction
target_pdb: nan
target_uniprot: nan
fold_class: any
tools: [AlphaFold-Multimer, Boltz-1, Chai-1]
key_paper_doi: 10.1038/s41586-024-07487-w
key_metrics:
  iptm_at_0.85_with_KD_no_better_than_microM: "common (case 002 / 010 evidence)"
  iptm_correlation_with_in_vitro_KD: "<0.5"
  iptm_purpose: "model confidence in interface placement, NOT binding strength"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, iPTM, affinity, confidence-vs-affinity, AF-Multimer]
---

# NEG: 把 iPTM 当 quantitative binding affinity / KD 推断

## ★ 失败模式
- AF-Multimer iPTM 0.85+ 不等于 picomolar binder
- iPTM 是 interface 位置 confidence, 不是 binding strength
- case-034 真数据: design_0079 iPTM 0.40 = false positive; design_0098 iPTM 0.86 但 in vitro KD 未知
- 报告中 "iPTM 0.9 = 强 binder" 是误导

## ★ 排除/禁止
- 不允许在报告中把 iPTM rank 1-1 等同于 binder rank
- 必须显式区分 "AF2 confidence" vs "binding affinity"
- 真亲和必须 Rosetta_ddG / FEP / 实验测 (rule 02 + rule 09)

## ★ 方法选择决策链（反向）
- 正确（rule 01 + 09）: iPTM ≥ 0.6 + pAE_int < 10 + pLDDT_b ≥ 80 + 真亲和 (BLI/SPR/FEP)
- 错误: iPTM 排序 → 直接 affinity ranking

## Anti-pattern triggered
等价 anti-rule 8 (single docking score sort) + 9 (FEP RMSE 假定外推工业)

## Evidence cases
- protein-001 (AF3 RBD-ACE2; iPTM = confidence, KD = experimental)
- protein-002 (Watson 2023 PD-L1 binder; iPTM 0.85 in silico → in vitro 5-15% binder rate)
- protein-007 (AF-Multimer heterodimer; iPTM 0.85+ NOT KD)
- protein-010 (Cao 2022 binder post-mortem; iPTM correlation < 0.5 with KD)
- protein-034 (PRAXIS self-generated; ESMFold-fold-OK ≠ AF2-Multimer-bind-OK ≠ in vitro KD)
