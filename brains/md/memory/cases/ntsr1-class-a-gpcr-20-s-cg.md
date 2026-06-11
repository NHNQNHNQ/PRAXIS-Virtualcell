---
case_id: md-ntsr1-class-a-gpcr-20-s-cg
sim_type: coarse_grained
domain: coarse_grained_md
target: "NTSR1 (Neurotensin Receptor 1) Class A GPCR"
tools: [GROMACS, Martini, MDAnalysis]
status: validated
schema_version: 1
source: agent_run
tags: [NTSR1, GPCR, Class A, 脂质指纹, PIP₂, Martini, 粗粒化, CG, MD模拟, RDF, 膜蛋白, POP2]
---

# NTSR1 Class A GPCR 粗粒化脂质指纹分析：20 μs CG模拟（修正版）

- 领域: membrane_protein_md
- 标签: NTSR1, GPCR, Class A, 脂质指纹, PIP₂, Martini, 粗粒化, CG, MD模拟, RDF, 膜蛋白, POP2

## 背景

用户需要针对NTSR1（Neurotensin Receptor 1）GPCR的20微秒Martini粗粒化自行完成模拟并生成轨迹，再分析脂质与受体的相互作用。这是一个典型的GPCR膜蛋白-脂质相互作用分析案例。

## 核心问题

用户需要针对NTSR1（Neurotensin Receptor 1）GPCR的20微秒Martini粗粒化自行完成模拟并生成轨迹，再分析脂质与受体的相互作用。这是一个典型的GPCR膜蛋白-脂质相互作用分析案例。

## 过程摘要

1. Step 1：确认膜z范围。通过脂质head group的z坐标分布，识别膜的下限（通常z≈52nm）和上限（z≈78nm，CG膨胀后）。
2. Step 2：确认蛋白z位置。计算蛋白Cα的COM z值，如果在膜z范围内（约52-78nm），说明蛋白处于跨膜或贴膜状态。
3. Step 3：判断插入深度。计算蛋白XY平面到最近膜表面的距离。如果>3nm，说明蛋白未插入膜内层（表面结合态）。
4. 使用MDAnalysis的球坐标RDF分析功能。

## 结果与学到什么

- 第一，PIPC和POP2的关键区分。Agent发现原始分析犯了一个严重错误——将PIPC误认为PIP₂。实际区分：
- PIPC = PI（phosphatidylinositol，磷脂酰肌醇），每个分子8个Martini珠子，中性或弱负电。
- POP2 = PIP2（phosphatidylinositol 4,5-bisphosphate，磷脂酰肌醇4,5-二磷酸），每个分子16个Martini珠子，带强烈负电（-4至-5电荷）。
- 【关键概念澄清：PIPC ≠ PIP₂】
