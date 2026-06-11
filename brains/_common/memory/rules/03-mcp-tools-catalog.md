---
rule_id: 03-mcp-tools-catalog
schema_version: 1
rule_type: tool_routing
scope: mcp_tool_routing
applies_to:
  all_agents: true
confidence: domain_knowledge
---

# 平台 MCP 工具目录与学科路由(_common,所有 13 学科 agent 生效)

本平台接入的交互式 MCP 工具(命名 `mcp__<server>__<tool>`),按学科该用哪些。
MCP 工具是**交互式**的(多步调用 + 看中间结果决策),比一次性 skill 灵活。

## MCP 工具总览

| MCP server | 工具 | 用途 | 适用学科 |
| --- | --- | --- | --- |
| **biodb** | search_pubmed / get_pubmed_abstract / get_uniprot / get_pdb / search_chembl / get_pubchem | 实时核实真实文献 / 序列 / 结构 / 化合物 | **全 13 学科**(详见 rule 02) |
| **dock** | prepare_receptor / prepare_ligand / define_box / run_dock / get_file / write_file | 分子对接(gnina,交互式 box→对接→看 affinity→调参重对接) | dock / drug / protein |
| **gmx** | write_file / run_step / run_background / poll_job / get_file | MD 建系 + 模拟(交互式多步) | md(详见 md rule 11) |

## 学科路由

- **所有学科**:需核实真实生物数据(文献 DOI / 蛋白序列 / PDB 结构 / 化合物)→
  优先 `mcp__biodb__*`(见 rule 02),不要凭记忆编、不要只靠网页抓取。
- **dock / drug / protein**:做分子对接 → `mcp__dock__*`。典型流程:
  `prepare_ligand`(SMILES→3D sdf) → `define_box`(从共晶配体 resname 或结合位点
  residue_ids 定位口袋) → `run_dock`(gnina CNN) → 看 `best_affinity` 不满意调
  box / exhaustiveness 重对接。对接是探索性的,不要一次就收。
- **md**:分子动力学建系 + 模拟 → `mcp__gmx__*`(见 md rule 11 MCP 执行协议:
  BrainQuery 先行 → write_file mdp/top → run_step grompp → run_background mdrun →
  poll_job → get_file 分析)。
- **其他学科**(cell / crispr / cryo / enzyme / immuno / microbiome / omics /
  pharma / synth):本学科真分析走 SkillExec(run.py pipeline,一次跑完),
  外部数据核实用 biodb。这些学科暂无专用交互式 MCP(分析是 pipeline,skill 已覆盖)。

## Why

- 明确路由避免两类错误:① agent 不知道有这些交互式 MCP 工具,该对接却手算 /
  该查数据库却编;② agent 用错工具(如对接学科不用 dock)。
- 交互式 MCP(对接 / 建系)适合"看中间结果再决策"的探索性任务;pipeline 分析
  仍用 skill(一次输入→输出)更直接。
