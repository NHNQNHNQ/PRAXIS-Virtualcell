---
rule_id: 11-p450-cpr-partner
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [pathway_design]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-002-pathway-artemisinin]
confidence: high
last_updated: 2026-04-29
---

## 规则
任何 heterologous pathway 含 cytochrome P450（EC 1.14.x.x family，多见于 terpenoid / alkaloid / polyketide）必须配对一个对应的 cytochrome P450 reductase（CPR / NADPH-CPR）作为电子伴侣，并做活性 assay 校验。

## 依据
- **synth-002 (Paddon 2013, artemisinin)**：CYP71AV1 在 yeast 不配 CPR partner → 无活性；artemisinin acid 高 titer 严格依赖 CYP-CPR 配对（同 source organism 或 interchangeable yeast NADPH-CPR）

## 边界 (★)
- 不适用 P450 in vitro reconstitution（外源 NADPH 即可）
- 反例：未报道

## How to apply
- **Design** stage：`design_library[].kind=plasmid_construct` 中含 P450（按 EC 或 keyword 匹配）→ `partner_check: CPR_required` flag 必须 true，且 CPR enzyme 在 cassette 列表
- **Reviewer**：缺 CPR partner → repair；rule_id 提示 `rule 11`
