---
rule_id: 02-mandatory-hotspot-and-paired-msa
schema_version: 1
applies_to:
  design_tasks: ["de_novo_binder", "symmetric_oligomer_de_novo", "complex_prediction", "structure_prediction_complex"]
  fold_classes: ["ALL"]
evidence_cases: ["protein-001-af3-rbd-spike", "protein-002-rfdiffusion-pdl1-binder", "protein-007-af-multimer-heterodimer", "protein-009-symmetric-rfdiffusion-oligomer"]
confidence: high
last_updated: 2026-04-29
---

## 规则
两条强约束：
1. **Binder / 对称设计必须显式给出 hotspot[]**——RFdiffusion / 任何 binder generator 不知道 epitope 时，输出会飘离 target，in vitro 失败率 > 95%
2. **AF-Multimer / AF3 复合物预测必须 paired MSA**——unpaired MSA 给假高 iPTM 但 interface 错

## 依据
- **protein-002**：明文 "no hotspot annotation → RFdiffusion output drifts away"（hotspot Y56 / M115 / R125 是 PD-L1-PD-1 接触面）
- **protein-009**：对称 C3 设计中 hotspot 决定 monomer-monomer interface，缺失则 funnel 错
- **protein-001**：AF-Multimer 没 paired MSA 时给 self-chain 假高 iPTM
- **protein-007**：AF-Multimer 2.3 5×5=25 prediction 必须 `--use_paired_msa`，否则 SecB-RBS interface 落 chain B 错位

## 边界 (★ 必填)
- 不适用于 monomer 预测（protein-001 monomer ESMFold 无 multimer paired MSA 概念）
- 不适用于 redesign（freeze backbone，hotspot 是从原结构 derive 的，不是 input）
- 已知反例：**protein-006 Foldseek**——纯结构搜索不含"设计"概念

## How to apply
- **Scoping**：design_task ∈ {de_novo_binder, symmetric_oligomer_de_novo} → 强制 problem.hotspot[] 非空
- **Design**：design_pipeline 中任何 RFdiffusion 调用 input 必含 hotspot；任何 AF-Multimer/AF3 调用必须 `paired_msa: true`
- **Reviewer**：
  - design_task ∈ {de_novo_binder, symmetric_oligomer_de_novo} 但 hotspot 缺失或空 → block
  - skill_id ∈ {predict_complex, de_novo_binder_pipeline} 的 inputs 缺 `paired_msa: true` → block
  - skill_id == predict_complex 且 inputs.tool == "ESMFold" → block（ESMFold 不能跑 multimer，protein-008 明文）
