---
rule_id: 01-multi-model-consensus
schema_version: 1
applies_to:
  design_tasks: ["structure_prediction", "structure_prediction_complex", "complex_prediction", "mutation_effect_prediction", "high_throughput_structure_prediction"]
  fold_classes: ["ALL"]
evidence_cases: ["protein-001-af3-rbd-spike", "protein-002-rfdiffusion-pdl1-binder", "protein-004-thermompnn-saturation", "protein-007-af-multimer-heterodimer"]
confidence: high
last_updated: 2026-04-29
---

## 规则
预测/设计任务必须 ≥ 2 个 predictor + ≥ 5 seed/model 输出，cross-model 一致性必须显式报告（agreement RMSD < 3 Å 视为高一致；> 5 Å 视为低）。**single tool / single seed 输出**视为 anti-pattern，Reviewer gate 阻塞。

## 依据
- **protein-001**：AF-Multimer 5 model × 5 seed = 25 prediction，最低 iPTM-pTM-pLDDT trinity 才推；single seed 在 RBD-ACE2 上失败
- **protein-002**：1000 binder design 经 5-metric ensemble 筛到 ~50；single metric (Rosetta ddG only) 时 in vitro 完全失效
- **protein-004**：单一 ΔΔG predictor (ThermoMPNN ~0.65 / Rosetta ~0.55 / PyRosetta ~0.40) 都 < 0.7 correlation；2-predictor intersection 才把 precision 拉到 80%
- **protein-007**：AF-Multimer + AF3 + Boltz-1 三模型 cross-validation 才捕到 SecB-RBS interface；single model 给 high iPTM 但 interface 错位

## 边界 (★ 必填)
- 不适用于纯检索任务（**protein-006 Foldseek**）—— 检索没有"模型一致性"概念
- 不适用于"探索性"模式（用户显式 `--explore` flag），但必须在报告中标 `low_consensus`
- 已知反例：**protein-008 ESMFold high-throughput**——为吞吐牺牲一致性是合理 trade-off，但报告必须显式标 single-model + 触发 follow-up AF2 验证

## How to apply
- **Scoping**：Strategy 必须列出 ≥ 2 predictor backbones
- **Design**：Composite metric filter 必须 minItems 3 metric（synthesis §五 给出 5-metric 标准 set）
- **Execution**：每个 design 必须跑 ≥ 5 seed
- **Reporting**：Headline metric 表必须显示 cross-model agreement 列
- **Reviewer**：检测 design_pipeline 中只有 1 predictor → block；single ΔΔG predictor 在 mutation_effect_prediction → block
