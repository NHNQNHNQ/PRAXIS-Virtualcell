---
rule_id: NN-{topic-shortname}
schema_version: 1
applies_to:
  immuno_tasks: []          # ["mhc_class_i_epitope_prediction", ...] or ["ALL"]
  hla_classes: []           # ["HLA_I", "HLA_II", ...] or ["ALL"]
  antigen_classes: []       # ["viral", "tumor_neoantigen", ...] or ["ALL"]
evidence_cases: []          # ★ ≥3 case_id for promotion to confidence: high
confidence: low             # low | medium | high | cold_start
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
