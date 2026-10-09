# PRAXIS Skills & MCP 补充推荐计划

> 2026-06-11 · 基于 PRAXIS-2 现状盘点 + 外部公开生物 MCP/skills 生态调研

---

## 一、现状盘点

| 维度 | 现状 |
|---|---|
| 学科大脑 | 14 学科,389 cases / 169 rules / 167 skills(自研 workflow run.py) |
| 已接 MCP | `gmx`(MD 交互执行:write_file/run_step/run_background/poll/get_file)+ `echo`(测试) |
| skill 执行 | SkillExec → SSH conda activate host_env → run.py(一次输入→输出的 pipeline) |
| 知识检索 | BrainQuery 查**本地脑**(cases/rules/skills),不连外部实时数据 |
| GAP-E2E | 52 green skill 中 DONE_real 25(真跑验证) |
| **关键缺口** | agent 只能查本地脑 + 跑本地 skill,**无法实时查真实生物数据库**(PubMed/UniProt/PDB/ChEMBL),核实文献/序列/结构靠脑内 case 或 WebFetch 白名单 |

### 集成约束(决定可选路径)
- PRAXIS MCP = **stdio transport**,`command` 指向有 mcp lib 的解释器
- `.53` **node v12.22.9 + 无 npx** → 外部 **TypeScript/npx 类 MCP 装不了**(需 node18+)
- **Python stdio MCP 直接可接**(echo/gmx 即是)

---

## 二、补充原则(MCP vs Skill 判据)

| 该补什么 | 判据 | 形态 |
|---|---|---|
| **交互式多步 + agent 看中间结果决策** | 对接 box 调参、建系试错、结构预测看质量重跑 | **专用 MCP**(仿 gmx,自研) |
| **外部实时数据源访问** | 查 PubMed/UniProt/PDB/ChEMBL 真实记录 | **数据库 MCP**(自研 Python 或集成现成) |
| **确定性 pipeline(一次跑完)** | RNA-seq/docking/MD 分析链 | **Skill**(run.py,现有模式) |
| **通用工具(非领域特定)** | RDKit/BioPython/Scanpy 基础操作 | **借鉴公开 skill**(不自研) |

核心:**领域真分析链自研**(PRAXIS 护城河,GAP-E2E 已验证);**通用工具/数据访问用公开的**(不重复造轮子)。

---

## 三、推荐 A:生物数据库 MCP 【最高 ROI / P0】

**为什么最高 ROI**:PRAXIS 当前 agent 查不到外部实时数据,只能靠脑内 case + WebFetch 白名单。补数据库 MCP 后,agent 能**实时核实真实文献/序列/结构/化合物**——直接补强反幻觉(不编 DOI、能查真实 UniProt 序列、真实 PDB 结构、真实 ChEMBL 活性),覆盖全 14 学科。

### 外部现成 MCP(若 ops 升 node18+ 可直接集成)
| 类别 | MCP server | 数据源 | 维护者 |
|---|---|---|---|
| 文献 | PubMed / medRxiv / bioRxiv MCP | 39M 文献 + 预印本 | cyanheads / JackKuo666 |
| 蛋白 | UniProt / RCSB PDB / AlphaFold MCP | 序列/结构/预测结构 | Augmented Nature / cnyambura |
| 化学药物 | PubChem / ChEMBL / SureChEMBL / OpenFDA MCP | 化合物/活性/专利/FDA | cyanheads / Augmented Nature |
| 基因组 | Ensembl / NCBI Datasets / GTEx MCP | 注释/组装/表达 | Augmented Nature |
| 通路网络 | Reactome / STRING / Gene Ontology MCP | 通路/互作/功能 | Augmented Nature / MCPmed |
| 表达 | GEO MCP | 表达数据集 | MCPmed |
| 临床 | ClinicalTrials.gov MCP | 临床试验 | cyanheads |
| 聚合 | Biotools(PubMed+UniProt+GenBank+KEGG+PDB)/ BioThings(MyGene/MyVariant) | 多库一站 | BACH-AI / Augmented Nature |

### 推荐落地路径(规避 node 约束)
**自研轻量 Python 生物数据库 MCP**(`praxis2/mcp/servers/biodb_server.py`,仿 gmx_server):
- 本质是调 REST API(PubMed E-utilities / UniProt REST / RCSB / ChEMBL / PubChem),~5-8 个 tool
- `search_pubmed(query)` / `get_uniprot(accession)` / `get_pdb(pdb_id)` / `search_chembl(smiles/target)` / `get_pubchem(cid/smiles)`
- 不依赖 npx(纯 Python + requests),**`.53` egress 实测全通**(2026-06-11):PubMed esearch 真返(`CRISPR Cas9`→39330 命中+PMID)/ UniProt(P00698)200 / RCSB(1AKI)200 / PubChem 200 / ChEMBL 真返分子
- **优先 P0**:5-8 个核心库覆盖 80% 查询需求,自研可控 + 配合现有反幻觉门(检索先行)

**或** ops 升 `.53` node18+ → 直接配 Augmented Nature 全系列(20+ 库),零开发但依赖外部维护。

---

## 四、推荐 B:学科交互 MCP 【自研仿 gmx / P1】

高频"探索性多步"学科,封装高层工具让 agent 交互决策:

| MCP | 工具集 | 价值 |
|---|---|---|
| **dock**(已设计) | prepare_receptor/prepare_ligand/define_box/run_dock/get_file/write_file | 对接探索:box 定位→对接→看 affinity→调参重对接。praxis-dock env 工具就绪(gnina/obabel/rdkit/meeko) |
| structure_predict | submit_fold(序列)/poll/get_structure/assess_quality | boltz/esmfold 交互:序列→结构→看 pLDDT→重跑。权重 hf-mirror 可下 |
| (MD,已有 gmx) | — | 已验证模式 |

dock 设计已基本成型(标准 6 工具 + CNN rescoring),可直接进实现。

---

## 五、推荐 C:通用工具 Skills 借鉴 【低成本 / P2】

**公开 skills 库(MIT 许可,可直接借鉴/集成)**:
- **K-Dense-AI/claude-scientific-skills**(144 skills):RDKit/Datamol/DeepChem/OpenMM/MDAnalysis/BioPython/Scanpy/scVelo/PyDESeq2/MAFFT/IQ-TREE + 78 数据库 REST 访问
- **jaechang-hits/SciAgent-Skills**(197 skills):RNA-seq/single-cell/proteomics,BixBench 92%

**借鉴策略**(不照搬):
- PRAXIS 现有 167 skills 是**领域真分析链**(护城河);公开库是**通用工具封装**
- 对 PRAXIS **缺的通用工具**(如独立的 RDKit 操作、BioPython 序列处理),可参考公开 skill 的 SKILL.md 模式补,放标准路径 `brains/<学科>/skills/workflows/`
- 数据库访问类(78 库 REST)与推荐 A 的 biodb MCP 重叠 → 用 MCP 形态(交互查询)而非 skill(一次性)

---

## 六、优先级路线图

| 优先级 | 项 | 工作量 | 解锁价值 |
|---|---|---|---|
| **P0** | 自研 biodb MCP(PubMed/UniProt/PDB/ChEMBL/PubChem ~6 tool) | 中(仿 gmx,REST 调用) | **全学科 agent 实时查真实数据,补强反幻觉** |
| **P1** | dock MCP(已设计) | 中 | 对接学科交互式 |
| **P1.5** | ops 升 `.53` node18+ | 小(ops) | 解锁 Augmented Nature 全系列 + CC npx MCP |
| **P2** | structure_predict 交互 MCP | 中 | 结构预测交互 |
| **P2** | 借鉴公开通用 skill 补缺口(RDKit/BioPython 独立操作) | 小-中 | 通用工具覆盖 |
| **P3** | 集成现成生物 MCP(升 node 后,GEO/STRING/Reactome 等长尾库) | 小 | 长尾数据库 |

### 建议起步
**P0 自研 biodb MCP** 最值得先做:
1. ROI 最高(全学科 + 反幻觉,不只单学科)
2. 规避 node 约束(纯 Python)
3. 与现有反幻觉门(检索先行/stop_hook)协同——agent 查到真实 DOI/序列才能落 case
4. 仿 gmx_server 模式,有先例

---

## 七、引用(外部生态)

- [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) — 144 科学 skills,MIT
- [jaechang-hits/SciAgent-Skills](https://github.com/jaechang-hits/SciAgent-Skills) — 197 生信 skills
- [TensorBlock/awesome-mcp-servers (healthcare/life-sciences)](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/healthcare--life-sciences.md)
- [pathintegral-institute/mcp.science](https://github.com/pathintegral-institute/mcp.science) — 开源科学 MCP(Materials Project/GPAW/Jupyter)
- [Augmented-Nature 生物 MCP 系列](https://github.com/Augmented-Nature) — UniProt/ChEMBL/PDB/Ensembl/Reactome 等 20+ 库
- [IntuitionLabs: MCP Servers for Biotech](https://intuitionlabs.ai/articles/mcp-servers-biotech-guide) — 生物 MCP 分类指南
- [MCPmed (PMC12927880)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12927880/) — MCP-enabled bioinformatics web services 倡议
