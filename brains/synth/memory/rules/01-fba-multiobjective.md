---
rule_id: 01-fba-multiobjective
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [fba, strain_engineering]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-001-fba-ecoli-iml1515, synth-009-strain-engineering-ko]
confidence: high
last_updated: 2026-04-29
---

## 规则
所有 FBA / OptKnock 调用必须采用 multi-objective Pareto formulation（biomass + product + 至少一个 cofactor balance term）。Single-objective FBA 直接被 Reviewer 拒绝。

## 依据
- **synth-001 (Monk 2017, iML1515)**：「Single objective only：实际 metabolic engineering multi-objective（biomass + product + co-factor）」并提示 NADH/NADPH co-factor 平衡是关键
- **synth-009 (Burgard 2003, OptKnock)**：predicted vs experimental gap 30-50%，single-objective 是主因之一；C. glutamicum lysine 工业菌实际 KO 组合（3-5 KOs）是 Pareto trade-off

## 边界 (★)
- Dynamic FBA 不直接适用（time-resolved kinetics 是另一个范式）
- Pure WT growth-rate audit 单跑（仅 sanity）允许 single-objective
- 反例：未报道

## How to apply
- **Design** stage：`computational_pipeline` 中任何 `fba_simulate` / `optknock_strain` 步骤必须 `multi_objective: true` 且至少声明 `secondary_objective`
- **Reviewer**：若 `multi_objective: false` 且无 `--allow-single-objective` 显式 flag，stage_output `passed=false`、`required_repairs` 提示「rule 01」
- **Execution**：skill `fba_simulate` 默认 `multi_objective=True`；MEMOTE QC 失败时输出 `tool_provenance.simulated=true` + `passed_qc=false`
