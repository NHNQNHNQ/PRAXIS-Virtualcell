---
rule_id: 03-golden-gate-overhang-collision
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [plasmid_assembly]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-003-golden-gate-moclo]
confidence: high
last_updated: 2026-04-29
---

## 规则
所有 Golden Gate / MoClo 反应在生成前必须运行 overhang 唯一性 / 非回文 / GC%≤75% 校验。验证不通过的 part 集必须重新选 overhang 或拒绝输出。

## 依据
- **synth-003 (Engler 2009, PLoS ONE 「A Modular Cloning System for Standardized Assembly...」)**：5-fragment 70% 成功率 / 10-fragment 30% 成功率，overhang collision 是首要失败模式；MoClo 标准 4-bp overhang library 防 collision

## 边界 (★)
- 不适用 Gibson / SLIC / yeast assembly
- Hierarchical assembly（1 级 → 2 级）独立 enzyme（BsaI vs BsmBI），各自独立校验
- 反例：未报道

## How to apply
- **Design** stage：`design_library[].kind=plasmid_construct` 必须列出每段 part 的 5'/3' overhang
- **Execution**：skill `golden_gate_assembly` 内置 `validate_overhang_collisions()`，4-bp Hamming distance < 1 即报错
- **Reviewer**：若 execution_results 缺 `overhang_validation.passed=true` 字段，触发 repair
