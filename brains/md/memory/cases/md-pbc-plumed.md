---
case_id: md-md-pbc-plumed
sim_type: standard
domain: md_workflow_distillation
target: "MD 工作流规则蒸馏 (混合力场/PBC反应坐标/PLUMED版本耦合)"
tools: [GROMACS, PLUMED]
status: validated
schema_version: 1
source: agent_run
tags: [GROMACS, PLUMED, 混合力场, PBC, umbrella_sampling, metadynamics]
---

# MD 技能蒸馏复盘：混合力场、PBC 反应坐标与 PLUMED 版本耦合

- 领域: md_workflow_distillation
- 标签: GROMACS, PLUMED, 混合力场, PBC, umbrella_sampling, metadynamics

## 背景

这个主题原先分成两张近似案例卡：一张强调跨案例规则，一张强调这些规则的学习路径。合并后保留“规则从哪里长出来”的脉络，而不是只保留压缩结论。

## 核心问题

需要把多个旧案例中重复出现的失败模式收敛成少数可复用规则，同时保留这些规则是如何从拓扑构建错误、膜体系 CV 设计问题和 `PLUMED-GROMACS` 版本耦合中逐步暴露出来的。

## 过程摘要

1. 混合力场案例表明：自动化工具输出必须做结构和数值双重验证。
2. 膜体系案例表明：`PBC` 边界会污染反应坐标设计，必须先验证物理意义再采样。
3. 增强采样案例表明：进入 `PLUMED` 路线前必须前置确认 `GROMACS` 版本、编译方式和 MPI 约束。
4. 每次蒸馏都要把结论转成短规则，但不能丢掉这些规则来自哪些失败过程。

## 结果与学到什么

- 自动化输出不等于可信输入，必须做双重验证。
- `PBC` 和版本兼容是增强采样失败的高频根源。
- 低层错误会在高层模拟里被放大。
- 这类内容适合保留在 `memory/cases`，因为它本质上是一条学习路径，而不是单个 task 的操作手册。

