---
rule_id: task-overview-biosensor
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [biosensor]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## Biosensor 景观

**Topology 分类**：
- TF-promoter pair（AraC-pBAD, LacI-pLac, TetR-pTet）：经典，inducible
- Riboswitch / aptamer：RNA-level，快速
- Two-component system（histidine kinase）：bacteria 主流
- Quorum-sensing：population-level
- 引擎化 GPCR（mammalian）：高敏感度

**关键 metrics**：
- Dynamic range（fold-change ON/OFF）：≥5× 基本，≥10× 优秀
- Specificity ratio：rule 10（≥10× off-target）
- Response time：< 30 min 优选
- Detection limit：μM 范围常见，nM 是高级目标

**Tools**：iBioSim, Cello, Sensemaker, SBML circuit simulators, COPASI for dose-response。

**常见失败**：
- 单一 target test 不做 cross-reactant panel（rule 10）
- Bulk plate reader 读 digital sensor → 误判（rule 07）
- TF-promoter cross-talk
- Reporter 衰减半衰期 > assay 时间 → 假阴性
