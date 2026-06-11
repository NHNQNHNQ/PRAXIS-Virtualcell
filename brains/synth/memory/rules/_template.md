---
rule_id: NN-{topic-shortname}
schema_version: 1
rule_type: case_distilled       # case_distilled | landscape | cold_start_defaults
applies_to:
  synth_tasks: []               # subset of fba|pathway_design|plasmid_assembly|codon_opt|circuit|cell_free|biosensor|strain_engineering|bgc_mining, or [ALL]
  host_organisms: []            # canonical names (E. coli / S. cerevisiae / ...) or [ALL]
  scale: []                     # test_tube / shake_flask / fermenter / industrial, or [ALL]
evidence_cases: []              # ≥2 case_id required for rule_type=case_distilled
confidence: medium              # low | medium | high
last_updated: YYYY-MM-DD
---

## 规则
（一句话可执行规则。例如：「OptKnock 候选 KO 集合在投递给 wet lab 之前必须经过 essential-gene audit，移除 single-gene-deletion growth ≤ 1% WT 的基因」）

## 依据
- case_id：该案例中的何种观察支持此规则
- ...

## 边界 (★ 必填)
- 何时不适用（例如：dynamic FBA 不适用此 steady-state 规则）
- 已知反例（case_id + 反例描述；可填「未报道」）

## How to apply
- 哪个 Agent 阶段使用（scoping / design / execution / reporting）
- 怎样使用（例如：「Design Agent 在生成 OptKnock 计划时，必须包含一个 audit_essential_genes 步骤」）
