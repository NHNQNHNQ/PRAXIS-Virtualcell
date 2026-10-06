---
rule_id: 02-biodb-priority
schema_version: 1
rule_type: tool_routing
scope: external_data_verification
applies_to:
  all_agents: true
confidence: domain_knowledge
---

# 核实真实生物数据优先用 biodb MCP(_common,所有 agent 生效)

需要核实真实**文献 / 蛋白序列 / 结构 / 化合物**时,**优先**调用 `mcp__biodb__*`
权威数据库工具,而非 WebFetch 抓网页,更不要凭记忆编造(DOI / 序列 / 分子式)。

## 工具路由

| 需求 | 优先用 | 不要用 |
| --- | --- | --- |
| 查文献、核实 DOI | `mcp__biodb__search_pubmed` | WebFetch 抓 pubmed 网页 / 凭记忆编 DOI |
| 读某篇文献摘要 | `mcp__biodb__get_pubmed_abstract` | 网页抓取 |
| 蛋白真实序列 / 功能 / 物种 | `mcp__biodb__get_uniprot` | WebFetch 抓 uniprot 网页 |
| PDB 结构元数据(方法 / 分辨率) | `mcp__biodb__get_pdb` | 网页抓取 |
| 化合物 ChEMBL ID / SMILES / 临床阶段 | `mcp__biodb__search_chembl` | 网页抓取 |
| 化合物分子式 / MW / SMILES | `mcp__biodb__get_pubchem` | 网页抓取 |

## Why

- biodb 直连权威数据库 REST API,返结构化字段(PMID / accession / 分辨率 /
  SMILES 等);仍需核对物种、实验条件和记录来源。
- 这是反幻觉主线:查到真实 DOI / 序列 / 结构才能落 case,不能凭记忆编。
- biodb 与 WebFetch 在生物库上功能**重叠**,但 biodb 是结构化首选;WebFetch 留给
  biodb 未覆盖的来源。

## 边界(仍用 WebFetch / 不查外部)

- `search_chembl` 当前只检索分子元数据,不返回活性测定、MIC 或杀菌数据。
  评估抗菌效果需要另行检索并引用实验记录;分子信息不能代替活性证据。
- biodb 未覆盖的库(KEGG / Ensembl / STRING / Reactome 等)或任意非数据库网页:用 WebFetch。
- 已在本地脑命中(BrainQuery)的知识:先看脑内 case,不必每次都查外部库。
