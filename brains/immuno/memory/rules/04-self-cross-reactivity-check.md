---
rule_id: 04-self-cross-reactivity-check
schema_version: 1
applies_to:
  immuno_tasks: ["mhc_class_i_epitope_prediction", "mhc_class_ii_epitope_prediction", "tumor_neoantigen_identification", "allergenicity_assessment", "mrna_vaccine_sequence_design"]
  hla_classes: ["ALL"]
  antigen_classes: ["ALL"]
evidence_cases: ["immuno-001-mhci-netmhcpan", "immuno-002-mhcii-long-peptide", "immuno-003-neoantigen-pipeline", "immuno-009-allergen-prediction"]
confidence: high
last_updated: 2026-04-29
---

## 规则
所有推过的 epitope / peptide / vaccine antigen 必须 BLAST vs 人源 UniProt proteome（UP000005640）；> 80% identity over 8aa contiguous window flagged for autoimmune / central-tolerance / cross-reactivity risk。Allergen workflow 强制 WHO 80aa-window-≥35%-identity criteria + DL classifier consensus 同时执行，二者一致才 reject 或 proceed。

## 依据
- **immuno-001**：MHC-I epitope 预测 high binder 但与 human protein 高 self-similarity → 中枢耐受清除 T 细胞库 → 实际 immunogenicity 弱（甚至 autoimmune 风险）
- **immuno-002**：MHC-II long peptide 与 human DRB1-restricted self-epitope overlap 直接 cross-react，MS 数据集 (HLA Ligand Atlas) 是 ground truth
- **immuno-003**：Tumor neoantigen ranking 强制 self-similarity 列；driver mutation (KRAS G12D 等) 虽 immunogenic 但需 self-similar flank 检查
- **immuno-009**：Allergen WHO criteria 单走漏报 conformational epitope；DL classifier 单走漏报序列 motif；二者交叉验证

## 边界 (★ 必填)
- 不适用 TCR repertoire / BCR lineage 任务（不产 epitope 候选）
- 不适用 HLA typing 任务（不涉及 antigen 推荐）
- 已知反例：cancer-testis antigen（如 NY-ESO-1）本身是 self-derived 但表达局限睾丸 + tumor，central tolerance 不严，可豁免阈值（需显式标 `cancer_testis_antigen_exception`）

## How to apply
- **Design**：design_pipeline 必须含 `self_proteome_BLAST` in_silico_check；validation_plan.in_silico[].check_type 至少 1 项为 `self_proteome_BLAST`
- **Execution**：每个 epitope/neoantigen 输出 metrics.self_similarity_max_pct 必填；> 80% 标 `passed_qc=false` 或归入 excluded_epitopes
- **Reporting**：top_n_entities 中 self_similarity > 80% 项必须移到 excluded_epitopes_explanation 并解释 `category=self_cross_reactive`
- **Reviewer**：检测 design_plan.validation_plan 缺 self_proteome_BLAST → block；检测 final report 含 self_similarity > 80% epitope 但未 excluded → block
