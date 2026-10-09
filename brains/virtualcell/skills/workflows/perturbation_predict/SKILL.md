---
name: perturbation_predict
description: 预测基因扰动后的单细胞转录组响应(Coordinator 编排 + abstain 可靠性)
host_env: praxis-virtualcell
status: deployed
---

# perturbation_predict — 扰动响应预测

虚拟细胞核心 skill:给定 baseline 状态 + perturbation,预测 delta 表达并给可靠性判断。

## SOP
1. 准备 baseline scRNA + perturbation spec(genes / dose / time / 物种)。
2. Coordinator 路由到 perturbation subagent,PredictorRegistry ensemble 预测 delta 表达。
3. ReliabilityAgent 判断 accept / abstain(强基线下诚实报告)。
4. 输出 mean / uncertainty / provenance;simulated 产物自标。

## inputs
- perturbation: 扰动 spec(基因敲除 / 组合 / 药物 / 剂量)
- cell_type / species: 上下文
- simulate: bool(干跑标记)
