---
case_id: md-melatonin-fentanyl-md
sim_type: umbrella_sampling
domain: membrane_permeation_md
target: "Melatonin 与 Fentanyl 跨 POPC 膜"
tools: [GROMACS, CHARMM36, GAFF2, WHAM]
status: validated
schema_version: 1
source: agent_run
tags: [GROMACS, CHARMM36, GAFF2, POPC, umbrella_sampling, 跨膜MD, PMF, PBC]
---

# Melatonin 与 Fentanyl 跨膜 MD 与伞形采样复盘

- 领域: transmembrane_md
- 标签: GROMACS, CHARMM36, GAFF2, POPC, umbrella_sampling, 跨膜MD, PMF, PBC

## 背景

这个主题原先有两张近似案例卡，一张更偏流程经验，一张更偏学习价值说明。合并后保留两部分信息：既保留跨膜 PMF 的执行路线，也保留混合力场和 PBC 反应坐标为什么会成为高频坑点。

## 核心问题

需要比较褪黑素和芬太尼跨 POPC 膜的渗透性，并用本地构建体系、SMD、窗口提取和伞形采样重建跨膜 PMF，同时避免参数错误和反应坐标错误导致的系统性失败。

## 过程摘要

1. 先验证膜本身稳定，再把配体加入体系，避免把膜不稳定误判成配体效应。
2. 混合力场前先检查小分子原子质量、`[ atomtypes ]` 区块和总拓扑 include 顺序。
3. 用 SMD 只做路径探索，不把单条拉伸轨迹直接当作 PMF 结果。
4. 窗口提取后逐窗检查目标距离、均值和波动，再进入正式 umbrella sampling。
5. 最后用 `WHAM` 重建 PMF，并结合分子电荷、`logP` 和 `TPSA` 做机制解读。

## 结果与学到什么

- `GAFF` 质量错误会直接导致能量爆炸和 `NaN` 崩溃，属于必须先排除的基础问题。
- 膜体系反应坐标一旦受到 `PBC` 边界干扰，后面所有采样都会失真。
- 跨膜渗透性的核心比较对象是能垒和 PMF 曲线形态，而不是单个瞬时构象。
- 这类内容应保留在 `memory/cases`，因为它体现的是案例学习过程，而不是单一命令模板。

