---
rule_id: 05-multi-colony-pick
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [plasmid_assembly]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-003-golden-gate-moclo]
confidence: medium
last_updated: 2026-04-29
---

## 规则
任何 cloning 实验的 wet-lab 计划必须包含 ≥ 3 个 colony pick + colony PCR + 全质粒序列校验（Sanger / Plasmidsaurus / Nanopore）。

## 依据
- **synth-003**：MoClo 实践经验，single colony pick 拍到 mis-ligated / partial 产物概率 10-30%；3 colony 涵盖 95%+ 真阳性

## 边界 (★)
- 不适用 in vitro reactions / cell-free / linear DNA
- 大型 BAC / YAC（>30kb）经常需要更多 colony（≥5）
- 反例：未报道

## How to apply
- **Design** stage：`validation_plan.experiments[]` 必须含 `colony_pick_n: ≥3` + `colony_pcr: true` + `full_plasmid_seq: true`
- **Reviewer**：scan `validation_plan` for these fields
