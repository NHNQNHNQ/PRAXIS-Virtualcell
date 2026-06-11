---
rule_id: 01-multi-method-mhc-consensus
schema_version: 1
applies_to:
  immuno_tasks: ["mhc_class_i_epitope_prediction", "mhc_class_ii_epitope_prediction", "tumor_neoantigen_identification", "allergenicity_assessment"]
  hla_classes: ["ALL"]
  antigen_classes: ["ALL"]
evidence_cases: ["immuno-001-mhci-netmhcpan", "immuno-002-mhcii-long-peptide", "immuno-003-neoantigen-pipeline", "immuno-009-allergen-prediction"]
confidence: high
last_updated: 2026-04-29
---

## 规则
MHC binding / immunogenicity / allergenicity 决策必须 ≥ 2 method consensus；single-tool 输出视为 anti-pattern，Reviewer gate 阻塞。具体：Class I 用 {NetMHCpan-4.1, MHCflurry-2, BigMHC} ≥ 2/3；Class II 用 {NetMHCIIpan-4.3, MARIA, MixMHC2pred} ≥ 2/3；allergenicity 用 {AllergenOnline WHO criteria, AllerCatPro, AlgPred-2.0, AllerTOP} ≥ 3 一致才能 reject。

## 依据
- **immuno-001**：NetMHCpan + MHCflurry + BigMHC 三方 consensus 是临床推荐做法；single-method false call rate ~30%
- **immuno-002**：MHC-II register prediction 不同工具差异大（NetMHCIIpan vs MARIA core 9-mer 偏移），≥ 2 register consensus 才可信
- **immuno-003**：Neoantigen pipeline 强制 ≥ 2 MHC predictor + immunogenicity score (BigMHC-IM / PRIME-2.0) 与 binding 解耦
- **immuno-009**：Allergen 仅靠 WHO criteria（80aa window / 35% identity）漏报 conformational allergen；DL classifier (AllerCatPro / AlgPred-2.0) 必补；多工具一致才 reject

## 边界 (★ 必填)
- 不适用纯 HLA typing（**immuno-007** 用三 caller consensus 但属于 hla_typing rule 02 范畴）
- 不适用 TCR/BCR-seq 任务（无 MHC predictor 概念）
- 已知反例：稀有 HLA allele（如 HLA-B*15:03）某些 predictor 训练集缺，consensus 反而误导 → 报告必须显式标 `low_confidence_rare_allele`，不可强行 ≥ 2 一致

## How to apply
- **Scoping**：candidate_strategies 必须列出 ≥ 2 predictor backbones
- **Design**：design_pipeline 中 MHC skill input 必含 `predictors: [≥2 names]`
- **Execution**：每个 epitope 输出必须含 `n_predictors_used ≥ 2` + `consensus_strong_binders` 计数
- **Reporting**：headline_metrics 表必须显示 cross-method consensus 列；不允许仅引用单一工具分数
- **Reviewer**：检测 design_pipeline 中 MHC skill 仅 1 predictor → block；allergen 仅 WHO criteria → block
