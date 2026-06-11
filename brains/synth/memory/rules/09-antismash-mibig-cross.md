---
rule_id: 09-antismash-mibig-cross
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [bgc_mining]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-010-bgcs-natural-product]
confidence: high
last_updated: 2026-04-29
---

## 规则
antiSMASH 的所有 BGC 输出必须 cross-check MIBiG database 评估 novelty：≥80% identity → known cluster；30–80% → variant；<30% → novel. 不做 cross-MIBiG 的 mining run 直接拒绝。

## 依据
- **synth-010 (Blin 2020, antiSMASH 7)**：80% rediscovery rate baseline；MIBiG 是已知 BGC 的标准库；novelty 判断必须用此对照

## 边界 (★)
- 不适用纯 NP（natural product）structure prediction（与 BGC mining 不同）
- 极小数据集 / 残缺 contig 时 cross-check 仍需做但置信度标 `low`
- 反例：未报道

## How to apply
- **Design** stage：`computational_pipeline.bgc_mining` 步骤必须 declare `cross_mibig: true`
- **Execution**：skill `bgc_mining` 输出 `mibig_match_pct` 字段，`<80` 标 novel candidate
- **Reviewer**：缺 `mibig_match_pct` → repair
