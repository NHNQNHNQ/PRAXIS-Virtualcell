---
rule_id: 03-mcp-tools-catalog
schema_version: 1
rule_type: tool_routing
scope: mcp_tool_routing
applies_to:
  all_agents: true
confidence: domain_knowledge
---

# 平台 MCP 工具目录与任务路由(_common,所有 agent 生效)

本平台接入的交互式 MCP 工具(命名 `mcp__<server>__<tool>`),按任务选择。
MCP 工具是**交互式**的(多步调用 + 看中间结果决策),比一次性 skill 灵活。

## MCP 工具总览

| MCP server | 工具 | 用途 | 适用任务 |
| --- | --- | --- | --- |
| **biodb** | search_pubmed / get_pubmed_abstract / get_uniprot / get_pdb / search_chembl / get_pubchem | 检索真实文献 / 序列 / 结构元数据 / 化合物元数据 | 证据检索(详见 rule 02) |
| **dock** | prepare_receptor / prepare_ligand / define_box / run_dock / get_file / write_file | 分子对接(gnina,交互式 box→对接→检查评分与姿势) | 靶点结合假设分析 |
| **gmx** | write_file / run_step / run_background / poll_job / get_file | MD 建系 + 模拟(交互式多步) | 结构与动力学分析(需可用的 GROMACS 环境) |

## 任务路由

- **证据检索**:需核实真实生物数据(文献 DOI / 蛋白序列 / PDB 结构 / 化合物)→
  优先 `mcp__biodb__*`(见 rule 02),不要凭记忆编、不要只靠网页抓取。
- **靶点结合假设分析**:做分子对接 → `mcp__dock__*`。典型流程:
  `prepare_ligand`(SMILES→3D sdf) → `define_box`(从共晶配体 resname 或结合位点
  residue_ids 定位口袋) → `run_dock`(gnina CNN) → 检查 `best_affinity` 和姿势。
  必要时根据结构依据调整 box / exhaustiveness;评分不能直接解释为 MIC 或杀菌能力。
- **结构与动力学分析**:分子动力学建系 + 模拟 → `mcp__gmx__*`(
  BrainQuery 先行 → write_file mdp/top → run_step grompp → run_background mdrun →
  poll_job → get_file 分析)。
- 只有工具已配置、所需软件已安装且输入文件可用时,才报告对接或模拟实际执行。
  未配置工具或失败结果应保留状态和依据,不能用文字推演替代执行结果。

## Why

- 明确路由让检索、对接和模拟各自提供可追溯的证据,并保留各类证据的适用边界。
- 交互式 MCP(对接 / 建系)适合"看中间结果再决策"的探索性任务;pipeline 分析
  仍用 skill(一次输入→输出)更直接。
