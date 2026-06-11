---
rule_id: 03-class-i-vs-class-ii-pipeline-split
schema_version: 1
applies_to:
  immuno_tasks: ["mhc_class_i_epitope_prediction", "mhc_class_ii_epitope_prediction", "tcr_pmhc_complex_modeling"]
  hla_classes: ["HLA_I", "HLA_II"]
  antigen_classes: ["ALL"]
evidence_cases: ["immuno-002-mhcii-long-peptide", "immuno-010-tcr-pmhc-docking"]
confidence: medium
last_updated: 2026-04-29
---

## 规则
Class I 和 Class II 用不同 predictor 家族 + 不同 length grid + 不同 binding-mode 假设，必须分 pipeline 处理。Class I：8-11 mer（canonical 9），closed-end groove，NetMHCpan 家族（NetMHCpan / MHCflurry / BigMHC）；Class II：13-25 mer（variable length），open-end groove + register prediction，NetMHCIIpan 家族（NetMHCIIpan / MARIA / MixMHC2pred）。Cross-application（用 Class I model 跑 long peptide / 用 Class II model 跑 9-mer）直接 block。

## 依据
- **immuno-002**：MHC-II Antigen 85B (M.tuberculosis) 长肽预测必须用 NetMHCIIpan + register predictor (核心 9-mer 在 13-25 mer 中浮动)；用 NetMHCpan 跑 long peptide 截断到 9-mer 丢失 flanking 信息
- **immuno-010**：TCR-pMHC 复合物建模时 Class I 接口（α1/α2 + 8-11 mer）和 Class II 接口（α1/β1 + 13-18 mer）几何完全不同；TCRdock 已分 head 处理，generic PP-docker 不行

## 边界 (★ 必填)
- 不适用允许长肽 Class I cross-presentation（罕见特例，需显式标 `non_canonical_class_I`）
- 不适用 HLA-E / HLA-F 非经典 MHC（length 9 但 hydrophobic anchor 不同）
- 已知反例：HLA-Cw 上偶有 8-mer 优势，本身仍是 Class I

## How to apply
- **Scoping**：problem.hla_context.hla_class 必须 ∈ {HLA_I, HLA_II}；problem.peptide_length_bin 必须与 hla_class 匹配（HLA_I → 8-11；HLA_II → 13-25）
- **Design**：design_pipeline.skill_id 选择 `mhc_class_i_predict` vs `mhc_class_ii_predict`，inputs.predictors 必须从对应家族选
- **Execution**：单 skill 执行不允许跨 length；Class II skill 输出必须含 `core_9mer_consensus` + `register_predicted`
- **Reviewer**：检测 mhc_class_i_predict 输入 length > 11 → block；检测 mhc_class_ii_predict 输入 length < 13 → block；检测 tcr_pmhc_dock peptide length 与 hla_class 不符 → block
