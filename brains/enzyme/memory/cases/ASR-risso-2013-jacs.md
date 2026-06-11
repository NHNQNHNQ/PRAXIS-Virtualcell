---
case_id: ASR-risso-2013-jacs
schema_version: 1
parent_enzyme:
  uniprot: null                  # Ancestral β-lactamase reconstructed in silico, no extant UniProt
  cazy_family: null
  enzyme_family: ancestral_beta_lactamase / class_A
  ec: 3.5.2.6
  organism: Reconstructed Precambrian (~3 Gya) Last Common Ancestor of class A β-lactamases
  pdb: 4B88                     # ASR-resurrected ancestral β-lactamase 结构
substrate:
  primary_smiles: "CC1(C)S[C@@H]2N(C(=O)C[C@H]2NC(=O)Cc3ccccc3)C1C(=O)O"   # benzylpenicillin
  class: beta_lactam_antibiotic
target_property: thermostability   # 重构 ancestral 显示 hyperthermostability (Tm >100°C)
status: validated
provenance:
  source_type: literature
  doi: "10.1021/ja311630a"
  pmid: null
  citation: "Risso VA, Gavira JA, Mejia-Carmona DF, Gaucher EA, Sanchez-Ruiz JM (2013). Hyperstability and substrate promiscuity in laboratory resurrections of Precambrian β-lactamases. J Am Chem Soc 135(8):2899-2902."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1021/ja311630a 我推测 (well-cited Sanchez-Ruiz × Gaucher paper); QA via CrossRef 验证"
    - "Ancestral sequence reconstruction (ASR): 用 phylogenetic 树 + ML inference 重建祖先序列, 化学合成 + 重组表达 — 不存在 UniProt"
    - "PDB 4B88 我推测; ASR-β-lactamase 后续多个 PDB"
    - "Sanchez-Ruiz (Granada) + Gaucher (Georgia Tech) 经典 ASR 系列 — 揭示 thermostability is 'ancestral' property of life"
    - "本案例核心: 重建的 3 Gya 祖先 enzyme Tm >100°C, 远超现代后裔, 同时显示 substrate promiscuity 高"
tags: [ancestral_sequence_reconstruction, ASR, beta_lactamase, thermostability, hyperthermostability, substrate_promiscuity, evolution_engineering, Sanchez-Ruiz, Gaucher, non-CAZy]
---

## 1. 背景与目标
- parent: 不存在 — 这是 **ancestral sequence reconstruction (ASR)** 重建的 3 Gya 前 Last Common Ancestor of class A β-lactamases
- 起始 hypothesis: 早期生命在地热环境 (>50°C), ancestral enzyme 应 thermostable; 现代 enzyme thermostability 可能是 derived 而非 retained
- 目标: 重建 ancestral β-lactamase, 验证其热稳定性 + 底物范围
- 应用: 工业级 thermostable enzyme discovery 的另一独立路径 (与 directed evolution + consensus 不同)

## 2. 决策过程 — ASR pipeline

### 候选位点策略
- **不是单个 mutation 工程化**, 而是 **重建整个序列**:
  1. 收集现代 class A β-lactamase 序列 (~70+ orthologs)
  2. 构建 phylogenetic 树 (用 RAxML / PhyML / MrBayes)
  3. 在 internal node 用 ML inference 推断 ancestral sequence (用 PAML / FastML)
  4. 化学合成 ancestral gene (DNA synthesis 商业化), 重组表达
  5. 实验测试 hyperthermostability + substrate range

### 排除的位点 (★ 必填)
- ASR 不主动排除位点 — 是 reconstructed sequence
- 但 inference 自然保留催化 conservation: catalytic Ser70, Lys73 等不变 (跨所有现代 ortholog 一致)
- ASR 唯一 hyperparameter: phylogenetic 树拓扑 + substitution model 选择

### 计算工具与阈值
- ML phylogenetic inference (PAML codeml / FastML)
- Bootstrap / Bayesian posterior probabilities for confidence per ancestral residue
- 实验: gene synthesis (~$0.5-1K/gene 当时) + heterologous expression in E. coli + DSF Tm + activity assay

## 3. 实验结果

### 关键发现
| 量 | 量化 |
| --- | --- |
| Ancestral β-lactamase Tm | >100°C (vs 现代 TEM-1 ~52°C, 提升 ~50°C) |
| Substrate scope | 显著 broader than 现代 (接受 cephalosporin + penicillin classes 多种) |
| Activity (specific) | comparable 或略低于现代 |
| Folding / stability | hyperstable, melting curve sharp |

### 失败案例 (★ 必填)
- ASR confidence varies per residue; bootstrap < 0.70 的 residue 序列推断不稳, 多 alternative ancestral 需要测
- Multiple alternative ancestors (用不同 phylogenetic models 推断) 都 thermostable — 但程度有差
- Ancestral 重构假设 ortholog 集合 representative; 含 selection bias 风险
- 复活后 ancestor 仍是"实验室复活", 不能完全等同真实生命中曾存在的 enzyme

## 4. 学习收获
- **成立的规则候选**:
  - **ASR 是 thermostability engineering 的另一独立路径** (与 SCHEMA / consensus / directed evolution 互补)
  - **Ancestral hyperthermostability hypothesis**: 早期生命在地热环境, 重建 enzyme 一般 thermostable — 工程化时若有充足 ortholog phylogeny, 可探索 ASR
  - **Substrate promiscuity**: ancestral enzymes 一般 substrate scope 比现代特化的更广 — substrate scope engineering 也可受益于 ASR
  - **No directed evolution needed**: 一次 gene synthesis + 表达就拿到 hyperstable variant (相比 directed evolution 的多 round 流程)
- **被推翻的假设**:
  - "Thermostable enzymes 必从 thermophilic 现代物种获取" — ASR 显示通过 reconstruction 也能拿到
  - "Engineering 必涉及 mutation rounds" — ASR 是另一 paradigm, no mutation, 是 reconstruction
- **下次类似问题应优先尝试**:
  - 当目标 enzyme 有 well-resolved phylogeny (≥50 ortholog 跨地质时间) 时, 评估 ASR 路径
  - ASR + directed evolution 串联: ASR 起手 (拿 thermostable scaffold), 后续 directed evolution 优化 (substrate scope / activity)
- **应避免**:
  - 假设 ASR ancestral 完全等同真实 historical enzyme — 是 inference, 含 uncertainty
  - 只用一个 phylogenetic model — 多 model alternative ancestors 应同步测

## 5. 计算 / 实验原始数据
原始 phylogenetic inference + ancestral sequences + crystal structures 见 J Am Chem Soc 135(8) 2013; Sanchez-Ruiz lab 维护 ASR 数据库.
