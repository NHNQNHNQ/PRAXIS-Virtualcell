---
case_id: NEG-ANTIBODY-VIA-GENERIC-AF
neg_pattern: antibody_modeled_with_generic_AlphaFold_not_antibody_specific
design_task: antibody_cdr_modeling
target_pdb: 7K9I
target_uniprot: nan
fold_class: immunoglobulin
tools: [AlphaFold-Multimer, AlphaFold2]
key_paper_doi: 10.1038/s42003-023-04927-7
key_metrics:
  af_multimer_antibody_false_negative_rate: "~50% (CDR-H3 hard cases)"
  cdr_h3_long_loop_RMSD: ">3 Å for H3 > 15 aa"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, antibody, IgFold, ImmuneBuilder, generic-AF, CDR-H3]
---

# NEG: 抗体 CDR/Fv 用通用 AlphaFold 而非 antibody-specific 工具栈

## ★ 失败模式
- AF-Multimer 在 Fv-Ag 复合物上 false negative > 50% (case 005 数据)
- AF2 generic 在 CDR-H3 long loop (>15 aa) 上 RMSD > 3 Å 
- 完全错过 paratope geometry，binder 误判 non-binder

## ★ 排除/禁止
- 不允许 antibody 任务自动走通用 AF/ESMFold pipeline
- 必须 route 到 antibody env (IgFold + ImmuneBuilder + AbLang2 + ANARCI)
- skill `antibody_pipeline` 是唯一允许的抗体 fold 入口

## ★ 方法选择决策链（反向）
- 正确: ANARCI Chothia 编号 → IgFold + ImmuneBuilder 双 ensemble → AbLang2 PLL → 复合物 SnugDock
- 错误: AF-Multimer (Fv + antigen) 直接跑

## Anti-pattern triggered
违反 rule 04 (task-aware tool routing); 等价 anti-rule 1 (wrong tool for task)

## Evidence cases
- protein-005 (IgFold antibody CDR; AF-Multimer false negative > 50%)
- protein-025 (Mason 2021 antibody specificity DL — antibody-specific pipeline)
- protein-026 (Hie 2024 antibody PLM evolution — antibody-specific)
