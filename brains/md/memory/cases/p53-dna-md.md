---
case_id: md-p53-dna-md
sim_type: standard
domain: protein_dna_md
target: "p53-DNA complex"
tools: [GROMACS]
status: validated
schema_version: 1
source: agent_run
tags: [p53, DNA, PBC, RMSD, RMSF, H-bond, GROMACS, 轨迹分析]
---

# p53-DNA 复合物 MD 与 PBC 校正分析复盘

- 领域: protein_dna_md
- 标签: p53, DNA, PBC, RMSD, RMSF, H-bond, GROMACS, 轨迹分析

## 背景

这个主题在旧仓库里有完整案例，但当前活跃层没有保留。它的价值不在于体系构建，而在于明确了一条分析前置原则：蛋白-DNA 这类复合物在做 RMSD、RMSF 和氢键分析前，必须先处理好 PBC 伪影。

## 核心问题

用户提供了已经完成的 p53-DNA 轨迹，需要判断复合物是否稳定，并解释 RMSD、RMSF 和蛋白-DNA 氢键的生物学意义。原始轨迹在未做 PBC 校正时会出现异常大的 RMSD，容易把伪影误判成真实解离。

## 过程摘要

1. 先对轨迹做 `gmx trjconv -pbc mol -center` 级别的 PBC 校正。
2. 用校正后的轨迹重新计算 `RMSD`、`RMSF` 和蛋白-DNA 氢键。
3. 把稳定相和不稳定相分开看，避免只报一个总平均值。
4. 用氢键数量和界面柔性解释复合物稳定性，而不是只盯着单个 RMSD 数字。

## 结果与学到什么

- 未校正 PBC 时，RMSD 可以被放大到完全不可信的数量级。
- 对蛋白-DNA 复合物来说，`RMSD + RMSF + H-bond` 比单独一个指标更可靠。
- 分析前的轨迹预处理本身就是结果可靠性的组成部分，不应被当成可省略步骤。
- 这类内容应保留在 `memory/cases`，因为它体现的是一个真实分析复盘，而不是单条命令模板。
