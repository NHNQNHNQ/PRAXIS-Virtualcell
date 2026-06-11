---
rule_id: task-overview-circuit
schema_version: 1
rule_type: landscape
applies_to:
  synth_tasks: [circuit]
  host_organisms: [ALL]
  scale: [ALL]
last_updated: 2026-04-29
---

## 基因线路景观

**典型 topology**：
- toggle switch（Gardner 2000）：两 mutually inhibitory repressors，bistable
- repressilator（Elowitz 2000）：3-cycle 振荡
- AND / OR / NAND gates（Cello）：组合逻辑
- feed-forward loop：noise filter / pulse generator

**核心要求**：
- Bistable / oscillator → parametric sweep（rule 06）
- Single-cell readout (flow cytometry)（rule 07）
- ODE 模型（COPASI / Tellurium / iBioSim）+ stochastic Gillespie 校验（noise 重要时）

**主流工具**：iBioSim, COPASI, Tellurium (libRoadRunner), SBML simulators, Cello (logic-to-DNA compiler)。

**典型陷阱**：
- 部件正交性差（leaky promoter / cross-talk）
- 资源 sharing（ribosome / polymerase）造成 burden 偏离 single-cell ODE 假设
- Bistable region 边缘的 bistable → monostable transition 由 host stress 触发
