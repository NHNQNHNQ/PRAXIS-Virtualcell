---
case_id: md-1aki100ns-md
sim_type: standard
domain: soluble_protein_md
target: "Lysozyme 1AKI (鸡蛋白溶菌酶水溶液体系)"
tools: [GROMACS]
status: validated
schema_version: 1
source: benchmark
tags: [GROMACS, 水溶液体系, 1AKI, 溶菌酶, 本地构建, 轨迹输出, nstxout-compressed]
---

# 1AKI 溶菌酶水溶液本地 GROMACS 复盘

- 领域: 分子动力学模拟
- 标签: GROMACS, 水溶液体系, 1AKI, 溶菌酶, 本地构建, 轨迹输出, nstxout-compressed

## 背景

这个主题原先分散成两张近似案例卡：一张强调 1AKI 100ns 轨迹输出修复，一张强调水溶液体系的本地 `gmx` 入门路线。合并后保留两者的信息：既保留具体修复经历，也保留这条路线为什么适合作为本地默认基线。

## 核心问题

需要一条从零开始、本地可复现、可分析轨迹的水溶液蛋白 MD 路线，并避免 `nstxout` 配置不当导致“模拟跑完但没有可分析轨迹”的静默失败。

## 过程摘要

1. 从 1AKI 蛋白结构出发，用本地 `gmx` 完成 `pdb2gmx -> editconf -> solvate -> genion -> grompp -> mdrun`。
2. 采用正方体水盒、TIP3P 水模型和约 0.15 M 盐浓度，建立标准蛋白水溶液体系。
3. 在每一步检查坐标文件与 `topol.top` 的 `[ molecules ]` 是否一致，避免把计数错误带入后续阶段。
4. 重新检查生产 `MDP`，把“轨迹输出是否存在”作为和温压参数同级的重要前置检查。
5. 用 `EM -> NVT -> NPT -> MD` 的完整顺序验证这条路线的稳定性与可复现性。

## 结果与学到什么

- 水溶液体系最适合作为本地 `gmx` 的默认路线和入门验证路线。
- `nstxout-compressed`、`tc-grps`、`[ molecules ]` 一致性是三个必须前置检查点。
- “任务跑完但没有轨迹”是典型静默失败，不能等分析阶段才发现。
- 这类案例适合保留在 `memory/cases`，因为它既有体系背景，也有明确的学习过程和修复过程。

