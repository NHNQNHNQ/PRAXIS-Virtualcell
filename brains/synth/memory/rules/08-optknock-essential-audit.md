---
rule_id: 08-optknock-essential-audit
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [strain_engineering]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-009-strain-engineering-ko]
confidence: high
last_updated: 2026-04-29
---

## 规则
所有 OptKnock / OptStoic 输出必须经过 essential-gene audit：先跑 `single_gene_deletion()`，剔除 growth ≤ 1% WT 的基因，再让 OptKnock 仅在剩余 candidate universe 中搜索。任何最终 KO set 包含 essential gene 视为 fatal error，Reviewer 阻塞。

## 依据
- **synth-009 (Burgard 2003)**：OptKnock 数学最优解经常包含 ribosomal protein / essential metabolic enzyme，wet-lab 即 lethal；C. glutamicum lysine top KO 实际剔除核心代谢基因后才工业化可行

## 边界 (★)
- 不同 host 不同 essential set；切 host 必须重跑 audit（K-12 vs BL21 vs C. glutamicum 各异）
- Conditional essential（O₂-dependent / nutrient-dependent）按目标培养条件判定
- 反例：未报道

## How to apply
- **Design** stage：`computational_pipeline.optknock_strain` step 必须含 `audit_essential: true`
- **Execution**：skill `optknock_strain` 内部 `audit_essential=True` 默认，输出含 `essential_genes_audited_out: [list]`
- **Reviewer**：scan top-N KO sets for `^(rps|rpl|rpm|infA|infB|infC|tufA|tufB)` regex； Hit → fatal
