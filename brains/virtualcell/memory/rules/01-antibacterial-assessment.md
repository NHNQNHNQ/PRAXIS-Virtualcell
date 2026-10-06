---
rule_id: 01-antibacterial-assessment
schema_version: 1
rule_type: evidence_and_tool_routing
scope: antibacterial_candidate_assessment
applies_to:
  agent: virtualcell
confidence: implementation_contract
---

# 抗菌候选分子分析

检索词：抗菌 候选 分子 药物 活性 药敏 耐药 机制 靶点 依据 预测 MIC SIR OOD
Escherichia coli escherichia_coli Acinetobacter baumannii acinetobacter_baumannii
SMILES MDR direct MIC。

`virtualcell` 是当前默认 agent 的兼容目录名。任务是解释候选分子的抗菌活性工具
结果、整合耐药背景证据并提出可验证的机制假说。

## 输入与工具选择

1. 核对候选 ID、SMILES 或肽序列、细菌物种，以及用户要分析的终点。
   区分物种层面活性和具体菌株药敏；没有菌株输入与模型支持时不输出菌株特异结论。
2. 小分子活性走 MDR 的 `requested_outputs: ["activity"]`；单次请求仅接受一项
   `drug_panel`，并保留模型返回的 OOD、弃权和工件不可用状态。
   当前保留的真实小分子活性工件针对 Escherichia coli，不能直接跨物种外推。
3. Acinetobacter baumannii 小分子可使用独立 `abwm` direct MIC 工具。
   输入只接受 `{"task":"mic","model":"direct","smiles":"..."}`。
   该模型只输入结构，不输入菌株、基因组、培养条件、细胞状态或靶点。
4. 已知药物的 SIR/耐药背景分析使用 MDR 支持的请求和物种规则；
   新分子的结构活性预测不能代替已知药物的临床药敏分类。

## 实际调用入口

MDR 与 direct MIC 目前是独立 CLI/API 组件。仅在已注册相应执行工具、配置模型
工件且所需环境可用时调用；默认 praxis2 registry 不自动注册这两个预测器。
若已启用 `Bash` 执行工具，可从仓库根通过下列现有入口运行准备好的输入文件：

```bash
python -m praxis_virtualcell.mdr_gnb run --request REQUEST.json
PYTHONPATH=components/abaumannii_mic/src python -m abwm predict --input INPUT.json --model-root models/abaumannii/direct_mic --seed 42 --scheme compound
```

MDR 活性请求格式见 `examples/ecoli_activity.json`；direct MIC 的安装、输入和
模型范围见 `components/abaumannii_mic/README.md`。已部署的 MDR API 亦提供 `/predict`。
没有实际工具结果时报告“未执行”或具体失败原因，不用 LLM 补造数值。

## 证据与解释

- 优先检索同一分子、同一物种的实验记录，并记录结构标识、单位、测定类型、
  菌株、培养条件、PMID/DOI 或数据库记录 ID。相似分子和不同物种的证据单独说明。
- `mcp__biodb__search_chembl` 当前检索分子元数据，不返回 MIC 活性测定；
  不把化合物 ID、临床阶段或 SMILES 当作抗菌实验证据。
- 用 PubMed、UniProt、PDB 和可用的对接工具比较机制依据；确认蛋白物种、
  结构来源和结合位点。区分直接靶点实验、文献关联、耐药机制与对接假说。
- LLM 可以提出机制假说、支持与反对证据和验证方案。现有 MIC 模型不输出蛋白靶点；
  对接评分不单独证明细胞内靶点，也不等价于 MIC 或细菌杀伤能力。

## 结果边界

报告分别说明实验观察、模型预测和机制假说，并关联来源或工具结果。
保留 MIC 的原始单位及 log10/log2 定义、模型/工件版本、适用物种、OOD 与弃权原因。
鲍曼 direct MIC 的 `interval90` 是学习到的预测分布宽度，未经外部校准，不能称为
临床置信区间。MIC 是生长抑制终点；没有相应实验数据时不输出杀伤率、MBC 或
时间杀菌曲线。此入口未实现细胞状态演化、扰动模型或世界模型预测。
