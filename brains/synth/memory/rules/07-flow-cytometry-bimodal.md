---
rule_id: 07-flow-cytometry-bimodal
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [circuit, biosensor]
  host_organisms: [ALL]
  scale: [test_tube, shake_flask]
evidence_cases: [synth-005-toggle-switch-circuit, synth-008-biosensor-design]
confidence: high
last_updated: 2026-04-29
---

## 规则
Bistable / digital biosensor / toggle 输出的 wet-lab readout 必须是 single-cell（flow cytometry / microfluidics），禁用 plate-reader bulk fluorescence。Bulk 读数把 ON / OFF 平均成无意义中间值。

## 依据
- **synth-005**：bulk plate reader 把 bistable population 平均化为 unimodal distribution，丢失 bimodality 信号
- **synth-008**：biosensor digital response 同样需要 single-cell 读数验证 ON / OFF 切换

## 边界 (★)
- Pure analog biosensor / continuous output OK 用 plate reader
- 反例：未报道

## How to apply
- **Design** stage：`validation_plan.readout` 必须含 `flow_cytometry: true`（或微流控）
- **Reviewer**：检查 readout 字段；plate reader 加 bistable target → repair
