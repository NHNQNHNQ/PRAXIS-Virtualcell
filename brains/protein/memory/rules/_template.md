---
rule_id: NN-{topic-shortname}
schema_version: 1
applies_to:
  design_tasks: []          # ["de_novo_binder", ...] or ["ALL"]
  fold_classes: []          # ["immunoglobulin", ...] or ["ALL"]
  length_range: ""          # optional, e.g. "60-150"
evidence_cases: []          # ★ ≥3 case_id
confidence: low             # low | medium | high
last_updated: YYYY-MM-DD
---

## 规则
（一句话可执行规则）

## 依据
- case_id: 该案例中的何种观察支持此规则
- ...

## 边界 (★ 必填)
- 何时不适用:
- 已知反例 (case_id + 反例描述):

## How to apply
- 哪个 Agent 阶段使用 (scoping / design / execution / reporting / reviewer):
- 怎样使用:
