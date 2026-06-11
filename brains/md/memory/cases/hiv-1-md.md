---
case_id: md-hiv-1-md
sim_type: standard
domain: protein_ligand_md
target: "HIV-1 protease + DMP 450 抑制剂复合物"
tools: [GROMACS]
status: validated
schema_version: 1
source: agent_run
tags: [HIV-1 protease, 配体参数化, 活性位点分析, 报告写法, 蛋白酶抑制剂, MD分析套路]
---

# HIV-1 蛋白酶抑制剂复合物 MD 分析复盘

- 领域: protein_ligand_md
- 标签: HIV-1 protease, 配体参数化, 活性位点分析, 报告写法, 蛋白酶抑制剂, MD分析套路

## 背景

这个主题原先有两张近似案例卡：一张偏“分析套路”，一张偏“为什么要把结果写成生物学叙事”。合并后保留两层价值：既保留复合物 MD 的关键读出，也保留报告表达为什么重要。

## 核心问题

需要基于 HIV-1 蛋白酶与 DMP 450 抑制剂复合物，自建体系、运行模拟，并把配体稳定性、催化位点距离、氢键占有率和 flap 柔性翻译成可读的生物学报告。

## 过程摘要

1. 先完成复合物体系构建与配体参数化。
2. 运行生产 MD，观察配体 `RMSD`、Asp25 距离、氢键数和 flap 柔性。
3. 用这些指标评估抑制剂是否稳定占据活性位点并限制催化相关构象变化。
4. 不只罗列命令和数值，而是把这些指标组织成“占据、阻断、限制”的锁死机制叙事。

## 结果与学到什么

- 复合物 MD 的重点不是单纯稳定性，而是如何解释活性位点锁定机制。
- 配体 `RMSD`、Asp25 距离、氢键占有率和 flap 柔性可以组成一套稳定的分析骨架。
- 配体参数化和报告表达都属于可复用方法，应在 `skills` 固化；案例经历保留在 `memory/cases`。

