---
case_id: md-melatoninmt1-200ns-well-tempered-metadynamics
sim_type: metadynamics
domain: membrane_protein_md
target: "MT1 (Melatonin Receptor 1A) + 褪黑素配体"
tools: [GROMACS, PLUMED]
status: validated
schema_version: 1
source: agent_run
tags: [MT1, Melatonin, Melatonin受体, Metadynamics, GPCR, Class A, Plumed, 配体结合, 褪黑素, Well-tempered, sum_hills, FES]
---

# Melatonin进入MT1受体：200ns Well-tempered Metadynamics分析

- 领域: membrane_protein_md
- 标签: MT1, Melatonin, Melatonin受体, Metadynamics, GPCR, Class A, Plumed, 配体结合, 褪黑素, Well-tempered, sum_hills, FES

## 背景

用户需要针对MT1（Melatonin Receptor 1A）受体与褪黑素配体的200纳秒Well-tempered Metadynamics自行完成模拟并生成轨迹，再分析配体结合路径和结合自由能。这是一个Metadynamics增强采样方法的专业分析案例。

## 核心问题

用户需要针对MT1（Melatonin Receptor 1A）受体与褪黑素配体的200纳秒Well-tempered Metadynamics自行完成模拟并生成轨迹，再分析配体结合路径和结合自由能。这是一个Metadynamics增强采样方法的专业分析案例。

## 过程摘要

1. Step 1：绘制d_cenian随时间变化曲线。如果系统被困在某个区域（如s≈1.2nm，75%时间），说明采样不充分。
2. Step 2：绘制FES最小值ΔG随时间变化。如果ΔG持续下降（或上升），说明未收敛；如果趋于稳定，说明收敛。
3. Step 3：检查采样分布。实际采样分布应覆盖全部CV空间（从0到系统最大可能值）。如果只在部分区域采样，重建的FES不可靠。
4. Step 4：分段FES对比。将轨迹分成前半段和后半段，分别重建FES。如果两条曲线重叠，说明收敛。

## 结果与学到什么

- 第一，COLVAR数据处理。100M行→awk采样→约10000个数据点。绘制d_cenian随时间变化曲线。
- 第二，结合事件分析。从曲线可见：① 初始阶段（0-~80ns）：d_cenian在2-4nm范围波动，配体未稳定结合；② ~80ns时刻：d突然下降到<0.5nm，配体首次到达结合口袋；③ 后续75%时间：d保持在<1.5nm，配体保持结合态。
- 第三，FES重建和收敛性判断。使用PLUMED sum_hills重建FES：
- 【Metadynamics方法概述】
