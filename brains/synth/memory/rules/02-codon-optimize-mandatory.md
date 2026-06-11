---
rule_id: 02-codon-optimize-mandatory
schema_version: 1
rule_type: case_distilled
applies_to:
  synth_tasks: [pathway_design, codon_opt, cell_free]
  host_organisms: [ALL]
  scale: [ALL]
evidence_cases: [synth-002-pathway-artemisinin, synth-004-codon-optimization, synth-007-cell-free-system]
confidence: high
last_updated: 2026-04-29
---

## 规则
当 host_organism ≠ source organism（heterologous expression）时，pipeline 必须包含一次 `codon_optimize` 调用，且发生在所有 expression / FBA / Golden Gate 之前。Reviewer 拒绝缺该步骤的 design plan。

## 依据
- **synth-002 (Paddon 2013, artemisinin)**：植物 P450 在 S. cerevisiae 直接 clone 不 codon optimize → ~10× 表达下降；artemisinin acid 25 g/L 是经过 codon opt 的结果
- **synth-004 (Chen 2018)**：human IL-2 在 yeast 直接 clone CAI 0.45，codon opt 后 0.88，translation rate 5-10× 提升
- **synth-007 (Shimizu 2004)**：cell-free 表达 antibody fragment / membrane protein 时不 codon opt → mg/mL → μg/mL 量级损失

## 边界 (★)
- Source organism = host（同宿主）时本规则不适用
- 若 `preserve_native: true` 显式声明（实验目的为研究 native sequence），可豁免；但 Reviewer 会标记 `confidence: low`
- 反例：synth-006 GFP 已是 E. coli native，不必 codon opt（但仍需 destroy restriction sites）

## How to apply
- **Design** stage：检测 `design_library[]` 含 heterologous 来源 → `computational_pipeline` 必须有 `codon_optimize` 步骤，且 order 在 `fba_simulate / golden_gate_assembly / cellfree_design` 之前
- **Reviewer**：扫描 pipeline ordering；若 `codon_optimize` 缺失或位于晚期，`required_repairs: ["rule 02: codon_optimize before downstream steps"]`
- **Execution**：skill 自动以 `host` 参数运行 DNAchisel 或 fallback JCAT
