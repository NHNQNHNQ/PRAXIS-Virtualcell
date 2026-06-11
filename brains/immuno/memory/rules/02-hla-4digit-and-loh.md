---
rule_id: 02-hla-4digit-and-loh
schema_version: 1
applies_to:
  immuno_tasks: ["tumor_neoantigen_identification", "hla_typing_from_rnaseq", "tcr_pmhc_complex_modeling", "mhc_class_i_epitope_prediction", "mhc_class_ii_epitope_prediction"]
  hla_classes: ["HLA_I", "HLA_II", "allele_specific"]
  antigen_classes: ["ALL"]
evidence_cases: ["immuno-003-neoantigen-pipeline", "immuno-007-hla-imputation-rnaseq"]
confidence: medium
last_updated: 2026-04-29
---

## 规则
HLA 必须 4-digit（locus + 2-digit + 2-digit，如 `HLA-A*02:01` 而非 `HLA-A02`）；tumor 任务必须先跑 LOHHLA 检测 HLA loss-of-heterozygosity；HLA typing from RNA-seq 必须 ≥ 2 caller consensus（OptiType / arcasHLA / HLA-LA / seq2HLA / xHLA / Polysolver 任选 ≥ 3，consensus ≥ 2/3）。

## 依据
- **immuno-003**：TCGA-SKCM neoantigen pipeline 中，2-digit HLA (e.g. HLA-A02) 不区分 A*02:01 vs A*02:03，binding affinity 差异大；HLA LOH 在 melanoma ~30% tumor 出现，丢 1 HLA copy 后该 allele 表位不 present，必须 LOHHLA 排除
- **immuno-007**：RNA-seq HLA typing 单 caller (OptiType only) 错误率 5-10%；3-caller (OptiType + arcasHLA + HLA-LA) consensus ≥ 2 一致 → 4-digit accuracy >95%

## 边界 (★ 必填)
- 不适用非 HLA-restricted 任务（TCR repertoire diversity / BCR lineage / CAR target / allergen 不需 HLA typing）
- 不适用罕见 HLA（IMGT/HLA 中频率 < 0.001 的 allele）—— 训练集稀疏，4-digit 可能不可靠，需标 `low_confidence_rare_allele`
- 已知反例：homozygous 个体（同 locus 两 copy 一致）单 caller 也可信；但仍要标记

## How to apply
- **Scoping**：problem.hla_context.hla_alleles[] 必须 4-digit；2-digit 输入直接 reject
- **Design**：tumor_neoantigen_identification 必须含 `hla_loh_check: true` 步骤；hla_typing_from_rnaseq 必须 callers ≥ 3
- **Execution**：HLA typing 输出必须含 `supporting_callers[]` 计数；neoantigen 输出必须含 `hla_loh_status ∈ {intact, loss_class_I, loss_specific_allele, unknown}`
- **Reporting**：top_n_entities 中含 `hla_loh_dropped` epitope 必须列入 excluded_epitopes_explanation
- **Reviewer**：检测 HLA allele 不符合 `^HLA-[A-Z]\d?\*\d{2}:\d{2}$` 格式 → block；tumor 任务无 LOH check → block
