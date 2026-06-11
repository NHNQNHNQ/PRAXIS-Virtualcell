---
rule_id: 06-bistable-parametric-sim
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [circuit]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-005-toggle-switch-circuit]
confidence: high
last_updated: 2026-04-29
---

## 规则
任何 bistable / toggle / oscillator circuit 设计必须做 4-D 参数扫描（生产率 α、降解率 β、Hill 系数 n、转换阈值 K）的 ODE simulation；不做参数扫描的 design 直接拒绝。

## 依据
- **synth-005 (Gardner 2000, Nature, toggle switch)**：bistability 要求 Hill n > 1（cooperative 抑制）；α/β 比和 K 决定 bistable region；不在 region 内的 design 退化为 monostable

## 边界 (★)
- 不适用 simple linear amplifier / single-input gate（参数 sweep 无收益）
- 反例：未报道

## How to apply
- **Design** stage：`design_library[].kind=circuit_topology` 必须含 `parametric_sweep_plan: {dimensions: 4, ranges: ...}`
- **Execution**：skill `circuit_simulate` 必须输出 `bistable_region_present: bool` + `parameter_robustness_score`
- **Reviewer**：若该字段缺失，repair
