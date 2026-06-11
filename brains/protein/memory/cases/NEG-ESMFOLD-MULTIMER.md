---
case_id: NEG-ESMFOLD-MULTIMER
neg_pattern: esmfold_used_for_multimer_complex_prediction
design_task: complex_prediction
target_pdb: nan
target_uniprot: nan
fold_class: any
tools: [ESMFold]
key_paper_doi: 10.1126/science.ade2574
key_metrics:
  esmfold_multimer_capability: "NOT supported by architecture"
  fake_concatenation_pseudo_structure: "low-confidence + nonsense interface"
status: failed
schema_version: 1
source: praxis_neg_pattern
extracted_at: 2026-05-04
tags: [NEG, anti-rule, ESMFold, multimer, tool-misuse]
---

# NEG: ESMFold 用于 multimer 复合物预测

## ★ 失败模式
- ESMFold 架构不支持 multimer (single-chain only)
- 拼 chain 用 GS linker (`AAA:BBB`) → 输出 pseudo-structure，interface 完全乱
- pLDDT 仍然高，但 inter-chain contact 没有意义

## ★ 排除/禁止
- 不允许 ESMFold + multi-chain input
- 多 chain 任务必须 route 到 AF-Multimer / Boltz-1 / Chai-1

## ★ 方法选择决策链（反向）
- 正确: complex prediction → AF-Multimer + Boltz-1 + Chai-1 多模型共识 (rule 01)
- 错误: ESMFold("AAA:BBB") = 错误 modality

## Anti-pattern triggered
违反 rule 04 (task-aware tool routing); ESMFold 是 monomer-only 工具

## Evidence cases
- protein-008 (Lin 2023 ESMFold; explicitly monomer-only, multimer NOT supported)
