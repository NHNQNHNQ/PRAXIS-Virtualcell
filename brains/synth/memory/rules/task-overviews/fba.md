---
rule_id: task-overview-fba
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [fba]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## FBA 域景观

**目标**：在给定 genome-scale metabolic model 上预测 growth rate / KO 效应 / pathway flux / cofactor balance。

**主流模型**（按宿主选）：iML1515 (E.coli K-12), iJN1463 (P. putida), iCW773 / iCW893 (C. glutamicum), iMM904 (S. cerevisiae), iWFL1372 (B. subtilis), iSyn669 (Synechocystis)。

**主流工具**：COBRApy / Cameo / reframed (Python), COBRA Toolbox (MATLAB), MEMOTE (QC).

**典型 pipeline**：
1. Load model → MEMOTE QC（一致性 / mass balance / charge balance / SBO terms）
2. Set medium (M9 + glucose 默认)
3. Optimize biomass → growth rate baseline
4. Single gene deletion scan → essential gene 列表
5. Multi-objective Pareto for product target

**常见失败**：
- 单 objective only → 工业上不可行
- Substrate uptake bound 错配 → growth 偏高 / 偏低
- O₂ bound 默认 -1000，实际有限
- 不跑 MEMOTE → garbage in garbage out
- Strain-specific assumption 错（K-12 vs BL21 vs W3110）

**进入 design 阶段必检**：rule 01（multi-objective），rule 08（essential audit if downstream KO）。
