---
case_id: md-d2r-remd
sim_type: remd
domain: membrane_protein_md
target: "D2R (Dopamine D2 Receptor)"
tools: [GROMACS, MDAnalysis]
status: validated
schema_version: 1
source: agent_run
tags: [GPCR, D2R, REMD, MDAnalysis, TM3-TM6]
---

# D2R REMD模拟分析复盘

- 领域: membrane_protein_md
- 标签: GPCR, D2R, REMD, MDAnalysis, TM3-TM6

## 背景

用户需要针对D2R（Dopamine D2 Receptor，多巴胺D2受体）的Inactive和Active两种状态的REMD（Replica Exchange Molecular Dynamics，温度交换分子动力学）自行完成模拟并生成轨迹，再分析GPCR激活的构象变化机制。这是一个GPCR结构生物学和增强采样方法结合的高级案例。

## 核心问题

用户需要针对D2R（Dopamine D2 Receptor，多巴胺D2受体）的Inactive和Active两种状态的REMD（Replica Exchange Molecular Dynamics，温度交换分子动力学）自行完成模拟并生成轨迹，再分析GPCR激活的构象变化机制。这是一个GPCR结构生物学和增强采样方法结合的高级案例。

## 过程摘要

1. TM3 IC端参考残基：resid 132 CA（A类GPCR TM3保守区域）。
2. TM6 IC端参考残基：resid 388 CA（A类GPCR TM6保守区域）。
3. 使用MDAnalysis的np.linalg.norm(tm3_ca - tm6_ca)计算3D距离，或分别计算XY和Z分量。
4. 分布：绘制Inact vs Active的直方图/核密度估计。

## 结果与学到什么

- 第一，GRO+XTQ加载问题解决。通过统一使用step5_input.gro作为拓扑参考，避免了TPR和XTC原子顺序不一致的问题。
- 第二，18-20个REMD周期分析。每周期10帧，共180-200帧数据。TM3-TM6距离（resid 132 CA到resid 388 CA）统计结果：
- Inactive态（18周期，180帧）：
- 多巴胺D2受体（D2R）是多巴胺能系统的核心受体，属于A类GPCR。主要功能：① 调节运动（黑质纹状体通路）；② 调控奖赏（腹侧被盖区）；③ 参与认知和情感（前额叶皮层）。D2R是精神分裂症、帕金森病、躁郁症和药物成瘾的核心药物靶点。
