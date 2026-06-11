---
rule_id: 05-in-silico-to-in-vitro-conversion
schema_version: 1
applies_to:
  design_tasks: ["de_novo_binder", "symmetric_oligomer_de_novo", "stabilization", "antibody_design", "binder_validation_post_mortem"]
  fold_classes: ["ALL"]
evidence_cases: ["protein-002-rfdiffusion-pdl1-binder", "protein-009-symmetric-rfdiffusion-oligomer", "protein-010-binder-success-failure-gap"]
confidence: high
last_updated: 2026-04-29
---

## 规则
任何 in silico 设计任务的 Reporting 必须含 **`in_silico_to_in_vitro_conversion_estimate`** 字段，给出预期转化率范围 + 历史依据 + 4-axis breakdown（expression / fold / binding / high-affinity）。**多同源靶点必须有 specificity panel**（negative design）。**湿实验 plan 必须在 Design 阶段就给出**（不是 Reporting 添加）。

## 依据
- **protein-002 (PD-L1 binder)**：明文 "in vitro success: expression 30%, binding function 5-15%"；同源 PD-L1/L2 (37%) 必须 negative design
- **protein-009 (symmetric oligomer)**：明文 "in silico → in vitro: 5-15% expression + correct oligomeric state"；SEC 验证 oligomeric state 不可省
- **protein-010 (post-mortem)**：明文 "70-95% in silico pass → in vitro fail"；4-axis: expression 40% / misfold 20% / non-binding 30% / weak-affinity 10%；single-metric all correlate < 0.5 with in vitro success

## 边界 (★ 必填)
- 不适用于纯预测任务（protein-001 / 006 / 008）—— 没 design 输出，没 conversion 概念
- 不适用于"已经做过 in vitro"的回顾任务，但即使是 post-mortem (protein-010) 也要给历史 conversion 数据
- 转化率 estimate 是 range 不是点估——10 case 不够估出 std；标 cold_start

## How to apply
- **Design**：design_plan.validation_plan.wet_lab_plan ★ MANDATORY；含 expression_system + purification + oligomeric_state_assay (e.g. SEC) + affinity_assay (e.g. BLI)
- **Design**：multi-homolog target 必须填 design_plan.specificity_panel[]（已知 PD-L1/L2 / HER family / kinase family 等）
- **Reporting**：`in_silico_to_in_vitro_conversion_estimate` 字段含：
  - estimated_pct_range (e.g. "5-15%" for binder)
  - rationale（基于哪些 historical cases）
  - based_on_cases（case_id list）
  - 4-axis breakdown（expression_pct, fold_pct, function_pct, high_affinity_pct）
- **Reviewer**：
  - design_task ∈ {de_novo_binder, symmetric_oligomer_de_novo, antibody_design} 且 `report.in_silico_to_in_vitro_conversion_estimate` 字段缺失或空 → block
  - design_task == de_novo_binder + multi-homolog target 但 specificity_panel 为空 → block
  - design_plan.validation_plan.wet_lab_plan 缺 expression_system → block
