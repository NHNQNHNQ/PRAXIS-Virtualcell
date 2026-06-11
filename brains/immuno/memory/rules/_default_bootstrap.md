---
rule_id: 00-default-bootstrap
schema_version: 1
applies_to:
  immuno_tasks: ["ALL"]
  hla_classes: ["ALL"]
  antigen_classes: ["ALL"]
evidence_cases: []
confidence: cold_start
last_updated: 2026-04-29
---

## 规则
Cold-start fallback rule for immunology tasks: when no case-distilled rule applies (e.g. case pool < 5 or task entirely novel), follow the universal immunoinformatics checklist before generating any recommendation.

## 依据
- 综合 immuno-synthesis §七（统一原则）
- 这条规则在 case 库 < 5 时 always-applies；当 ≥5 cases 后由更具体的 rule 01-05 接管

## 边界 (★ 必填)
- 当具体 rule 触发时不适用：rule 01-05 比 bootstrap 优先
- Cold-start 标签必须保留在所有推荐的 confidence 字段

## How to apply
**所有 stage 都要遵循下面这张 checklist**：

1. **Task identification (Scoping)**：第一步识别 `immuno_task` ∈ {mhc_class_i_epitope_prediction, mhc_class_ii_epitope_prediction, tumor_neoantigen_identification, tcr_repertoire_analysis, bcr_repertoire_lineage_analysis, mrna_vaccine_sequence_design, hla_typing_from_rnaseq, car_target_selection_safety, allergenicity_assessment, tcr_pmhc_complex_modeling}
2. **Tool routing (Design)**：tool 选择必须 task-aware（NetMHCpan 仅 Class I；NetMHCIIpan 仅 Class II；MiXCR+IgBLAST cross-validate；TCRdock 不可换通用 PP-docker；OptiType+arcasHLA+HLA-LA 三 caller consensus）
3. **Multi-method consensus (Design + Execution)**：MHC 任务 ≥ 2 predictor 强制；allergenicity ≥ 3 工具 一致才 reject；HLA typing 3-caller ≥ 2 一致
4. **HLA 4-digit minimum**：tumor_neoantigen / hla_typing / mhc / tcr_pmhc_dock 任务必须 4-digit alleles，2-digit 直接 block
5. **HLA LOH check (tumor)**：tumor_neoantigen_identification 必须 LOHHLA pre-step
6. **Self cross-reactivity (vaccine / neoantigen / allergen / mhc)**：所有推过的 epitope/peptide 必须 BLAST vs 人源 proteome；> 80% identity over 8aa flagged
7. **Class I vs II separate pipeline**：8-11 mer (Class I, NetMHCpan family) vs 13-25 mer (Class II, NetMHCIIpan family) 不可混
8. **Composite metric (Design)**：每任务 ≥ 3 metric 联合（EL_rank + presentation_score + immunogenicity_score 等）
9. **Excluded epitopes mandatory (Design)**：design_plan.excluded_epitopes[] 必须显式列出 self_cross_reactive / non_presented / hla_loh_dropped / subclonal 项
10. **Failure modes mandatory (Reporting)**：report.interpretation.why_failed 必须非空（除非 mechanism_link 显式 'no failures observed'）
11. **Confidence label (Reporting)**：每条推荐 cold_start | low | medium | high | domain_knowledge
12. **Provenance (Execution)**：tool / version / seed / hyperparam / simulated 标志全记录
