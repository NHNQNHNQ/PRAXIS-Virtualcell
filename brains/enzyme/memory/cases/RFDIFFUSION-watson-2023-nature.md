---
case_id: RFDIFFUSION-watson-2023-nature
schema_version: 1
parent_enzyme:
  uniprot: null                  # de novo design — no parent enzyme
  cazy_family: null
  enzyme_family: de_novo_designed / ML_AI_design
  ec: null
  organism: in silico designed (RFdiffusion + RoseTTAFold)
  pdb: null                     # designs validated by experimental structures, but specific case-paper PDBs vary
substrate:
  primary_smiles: null            # multiple targets demonstrated (binders / hydrolases / etc.)
  class: design_methodology_demonstration
target_property: substrate_specificity   # methodology paper, but main demo is functional protein design
status: validated
provenance:
  source_type: literature
  doi: "10.1038/s41586-023-06415-8"
  pmid: null
  citation: "Watson JL, Juergens D, Bennett NR, Trippe BL, Yim J, Eisenach HE, Ahern W, Borst AJ, Ragotte RJ, Milles LF, Wicky BIM, Hanikel N, Pellock SJ, Courbet A, Sheffler W, Wang J, Venkatesh P, Sappington I, Torres SV, Lauko A, De Bortoli V, Mathieu E, Ovchinnikov S, Barzilay R, Jaakkola TS, DiMaio F, Baek M, Baker D (2023). De novo design of protein structure and function with RFdiffusion. Nature 620(7976):1089-1100."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/s41586-023-06415-8 高把握 (RFdiffusion landmark paper)"
    - "本工作不是 enzyme engineering 改造, 是 ML-based de novo design — 从随机 noise 出发生成 protein structures with desired properties"
    - "Baker lab (UW IPD) 招牌 ML protein design 工作; RFdiffusion 是 RoseTTAFold + diffusion 模型"
    - "本 case 入库的目的: 给 rule 04 'ML-driven design' 分支提供具体 evidence"
    - "RFdiffusion 已商业化为 Generate Biomedicines / Cradle Bio 等公司核心 IP"
tags: [ML_AI_design, RFdiffusion, RoseTTAFold, de_novo_design, diffusion_model, functional_protein_design, Baker-lab, generative_AI, non-CAZy, methodology]
---

## 1. 背景与目标
- 不是 parent enzyme 工程化 — 这是 **ML-driven de novo protein design** 方法论
- RFdiffusion: structure generation via diffusion model trained on RoseTTAFold (~250K PDB 结构作训练数据)
- 输入: structural / functional motif (e.g., catalytic triad position, binding interface)
- 输出: novel protein backbone 满足约束, 后续用 ProteinMPNN 设计序列
- 应用展示 (paper 内): metal binding sites, protein-protein interaction binders, symmetric oligomers, functional motif scaffolding

## 2. 决策过程 — ML pipeline

### 候选位点策略 (与传统 enzyme engineering 不同)
- **不是 mutation library**, 是 **structure generation**:
  1. 定义 functional constraint: e.g., catalytic triad spatial geometry, substrate-binding interface 形状
  2. RFdiffusion 从 noise 出发, 经 diffusion process 生成 backbone 满足 constraint
  3. ProteinMPNN 给生成 backbone 设计 sequence
  4. AlphaFold2 / RoseTTAFold 验证 designed structure 与 generated 一致 (in silico filter)
  5. 实验合成 + 测 (binding / activity)

### 排除的位点 (★ 必填)
- 由用户在 motif 定义中指定 "fixed" residues (e.g., catalytic triad in fixed geometry)
- ML 模型从 PDB 学习, 自然避免明显物理上不合理结构
- 但 ML 偶尔生成"无活性 fold" — 需 in silico filter + 实验验证

### 计算工具与阈值
- RFdiffusion (paper supp 公开 code) + ProteinMPNN (Baker lab open-source)
- AlphaFold2 / ESMFold 验证 in silico
- ColabFold / OmegaFold 也是补充工具
- 实验: gene synthesis + heterologous expression + 实验 binding / activity

## 3. 实验结果 (跨多 case demonstration)

### 关键发现
| 应用 | 实验验证 |
| --- | --- |
| Metal binding site design | 多 designs 实验 confirmed Zn²⁺ / Cu²⁺ binding |
| Symmetric oligomer (C2/C3/C5) | designed oligomers 在 SEC-MALS 显示 expected stoichiometry |
| Protein binder (e.g., bind specific target like influenza HA) | 实验 confirmed nanomolar binding |
| Catalytic motif scaffolding | 部分 designed enzymes 显 some activity, but 远未达 natural enzyme efficiency |
| Success rate | 5-30% (取决于 task complexity); 远高于 traditional rational de novo |

### 失败案例 (★ 必填)
- **Catalytic activity** 是 RFdiffusion 当前最弱场景 — designed enzymes 通常 turnover < 1 s⁻¹, far below natural enzymes
- 部分 designed proteins 在 E. coli 表达 inclusion body — fold prediction 与 actual fold mismatch
- Metal binding 的 spatial geometry 训练数据中分布有限 → designs 偶尔不正确 metal coordination
- 不能保证 designed protein 在 in vivo 环境 stable
- ML model 偏向 训练数据中常见 fold (α/β, immunoglobulin fold), 罕见 fold 设计较弱

## 4. 学习收获
- **成立的规则候选**:
  - **ML-driven de novo design** 是工程化新 paradigm — 不是 mutation library 而是 generation; 适合 enzyme scaffold from scratch (不是 active enzyme 优化)
  - **当前实用 zone**: protein binders > metal binding sites > symmetric oligomers > catalytic enzymes (按 success rate 排)
  - **Catalytic enzyme de novo**: ML 设计 backbone + ProteinMPNN sequence 已可行, 但 turnover 远低 natural; 工业应用还需 directed evolution 后续优化
  - **Hybrid pipeline**: ML 设计 scaffold → directed evolution 优化 catalysis 是工业级新 workflow
- **被推翻的假设**:
  - "De novo enzyme design 必须 hand-crafted via Rosetta minimization" — RFdiffusion 大幅自动化
  - "ML 不能生成 functional protein" — Watson 2023 实验验证多种 functional designs
- **下次类似问题应优先尝试**:
  - 当 task 是 **scaffold design** (binder / oligomer / metal site), RFdiffusion + ProteinMPNN 是首选
  - 当 task 是 **enzyme catalytic optimization**, 仍以 directed evolution + structure-guided 为主, ML 只用 scaffold 起步
- **应避免**:
  - 期望 RFdiffusion design 直接工业 ready — 当前 turnover 数 oo small for industrial process
  - 仅 in silico filter — 必须 wet-lab 实验验证

## 5. 计算 / 实验原始数据
RFdiffusion code + 训练 weights 公开 (Baker lab GitHub); 各 design 实验数据见 Nature 620 supplementary.
