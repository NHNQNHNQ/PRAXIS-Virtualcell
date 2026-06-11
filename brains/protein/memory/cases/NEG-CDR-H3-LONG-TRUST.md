---
case_id: NEG-CDR-H3-LONG-TRUST
neg_pattern: trust_high_confidence_on_long_CDR_H3
design_task: antibody_cdr_modeling
target_pdb: 7K9I
target_uniprot: nan
fold_class: immunoglobulin
tools: [IgFold, ImmuneBuilder, AbLang2]
key_paper_doi: 10.1038/s42003-023-04927-7
key_metrics:
  cdr_h3_short_lt_15aa_RMSD: "1-2 Å (reliable)"
  cdr_h3_long_gt_15aa_RMSD: ">3 Å (NOT reliable)"
  failure_mode_count_in_pool: "~30% of clinical antibodies have H3 > 15 aa"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, antibody, CDR-H3, long-loop, IgFold, low-confidence]
---

# NEG: 长 CDR-H3 (> 15 aa) 上 IgFold/ImmuneBuilder 高 confidence 信任

## ★ 失败模式
- IgFold 给 H3 > 20 aa designed antibody pLDDT 高 — 但 RMSD vs X-ray > 3 Å
- 所有抗体 fold tool (IgFold, ImmuneBuilder, AbLang2) 在 long H3 上 failure mode 一致
- 临床抗体 ~30% 有 H3 > 15 aa → CDR 设计 / humanization risk 非常高
- 抗原表位放置不可信

## ★ 排除/禁止
- 不允许 H3 > 15 aa 的 antibody 设计直接进 wet lab 无 X-ray confirmation
- 必须自动 flag low-confidence in `antibody_pipeline` runner
- skill `antibody_pipeline` 已 enforce: H3 > 15 → low_confidence_flags

## ★ 方法选择决策链（反向）
- 正确（rule 04）: H3 ≤ 15 aa → IgFold/ImmuneBuilder 信任; H3 > 15 → 必须 X-ray 验证
- 错误: 在 long H3 design 上以 fold tool RMSE 1Å 假定推 lab

## Anti-pattern triggered
违反 rule 04 (antibody routing) + rule 09 (multi-modality validation when prediction unreliable)

## Evidence cases
- protein-005 (IgFold antibody CDR; H3 > 15 → RMSD > 3 Å warning)
- protein-025 (Mason 2021 antibody specificity; mammalian display + crystal subset)
