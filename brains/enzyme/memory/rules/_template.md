---
rule_id: NN-{topic-shortname}
schema_version: 1
applies_to:
  cazy_families: []           # [GH7, ...] 或 ALL
  property: ""                # thermostability | substrate_specificity | activity | ...
  enzyme_classes: []          # 可选: hydrolase / transferase / ...
evidence_cases: []            # ★ 至少 3 个 case_id
confidence: low               # low / medium / high
last_updated: YYYY-MM-DD
---

## 规则
（一句话可执行规则。例如:"GH7 共识替换在表面 loop 区, PyRosetta ΔΔG < -1.5 kcal/mol 即可期望小幅 Tm 提升"）

## 依据
- case_id: 该案例中的何种观察支持此规则
- ...

## 边界 (★ 必填)
- 何时不适用 (例如:活性位点 5 Å 内不适用; 糖基化位点周围不适用)
- 已知反例 (case_id + 反例描述)

## How to apply
- 哪个 Agent 阶段使用 (scoping / design / execution / reporting)
- 怎样使用 (例如:"Design Agent 在生成候选位点时,过滤 ΔΔG > -1.5 的项")
