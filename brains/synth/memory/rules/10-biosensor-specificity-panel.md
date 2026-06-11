---
rule_id: 10-biosensor-specificity-panel
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [biosensor]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-008-biosensor-design]
confidence: high
last_updated: 2026-04-29
---

## 规则
所有 biosensor design 必须含 cross-reactant specificity panel：≥5 种结构相近的非目标分子在生理浓度下 dose-response 测定。Specificity ratio = response(target) / max(response(off-target)) ≥ 10× 是基本门槛。

## 依据
- **synth-008 (Yang 2017, Nature Biotech)**：arabinose biosensor specificity panel（glucose / galactose / xylose / lyxose / fructose）；只测 target 的 sensor 在复杂背景失效率高

## 边界 (★)
- 单一 input 工程化研究（pure mechanism study）允许 panel 简化
- 反例：未报道

## How to apply
- **Design** stage：`validation_plan.experiments[]` 必须含 `cross_reactant_panel: {n_compounds: ≥5, list: [...]}`
- **Reviewer**：缺 panel → repair
