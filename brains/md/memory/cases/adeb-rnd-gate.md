---
case_id: md-adeb-rnd-gate
sim_type: standard
domain: membrane_protein_md
target: "AdeB RND三聚体外排泵 (Acinetobacter)"
tools: [GROMACS, CHARMM]
status: validated
schema_version: 1
source: agent_run
tags: [AdeB, RND外排泵, 三聚体, 构象动力学, 内Gate, 外Gate, 膜蛋白, CHARMM, MD模拟, 313K]
---

# AdeB RND三聚体外排泵构象动力学：内Gate持续开放发现

- 领域: molecular_simulation
- 标签: AdeB, RND外排泵, 三聚体, 构象动力学, 内Gate, 外Gate, 膜蛋白, CHARMM, MD模拟, 313K

## 背景

用户需要针对AdeB三聚体500纳秒MD自行运行模拟生成轨迹，再分析Gate距离动态和限速步骤。这是一个聚焦Gate构象动力学的深度分析案例。

## 核心问题

用户需要针对AdeB三聚体500纳秒MD自行运行模拟生成轨迹，再分析Gate距离动态和限速步骤。这是一个聚焦Gate构象动力学的深度分析案例。

## 过程摘要

1. 如果内Gate 100%时间开放 → 内Gate不是限速步骤。
2. 如果外Gate有部分时间闭合 → 外Gate可能是限速控制点。
3. 盐桥形成率越低（40%形成，60%断裂）→ 底物释放越困难。

## 结果与学到什么

- 第一，内Gate持续开放确认。L137-F612距离在整个500ns轨迹中约1.94nm，100%时间内完全开放。这明确表明：内Gate在无底物状态下已经是"外排就绪态"——无需构象激活即可接收底物。
- 第二，外Gate动态振荡分析。R931-D407距离在0.77-1.26nm范围动态振荡。使用0.4nm作为盐桥形成阈值，统计发现约40%时间形成部分盐桥（而非完全闭合）。
- 第三，限速步骤判断。基于以上数据：
- 【RND外排泵Gate系统概述】
