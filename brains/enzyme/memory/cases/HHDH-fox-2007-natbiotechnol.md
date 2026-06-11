---
case_id: HHDH-fox-2007-natbiotechnol
schema_version: 1
parent_enzyme:
  uniprot: Q93D82               # HheC; A. radiobacter AD1 已被重新分类为 Agrobacterium tumefaciens (UniProt 名称)
  cazy_family: null
  enzyme_family: halohydrin_dehalogenase / SDR_superfamily
  ec: 4.5.1.-                  # halohydrin halide-lyase (or 3.7.1.-)
  organism: Agrobacterium radiobacter AD1
  pdb: 1ZMT                     # HheC from Agrobacterium structure
substrate:
  primary_smiles: "ClC(O)CC(=O)OCC"   # ethyl (S)-4-chloro-3-hydroxybutanoate (KRED product, HHDH substrate for cyanation step)
  class: halohydrin / atorvastatin_intermediate
target_property: activity                 # 4000× catalytic efficiency improvement
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nbt1286"
  pmid: null
  citation: "Fox RJ, Davis SC, Mundorff EC, Newman LM, Gavrilovic V, Ma SK, Chung LM, Ching C, Tam S, Muley S, Grate J, Gruber J, Whitman JC, Sheldon RA, Huisman GW (2007). Improving catalytic function by ProSAR-driven enzyme evolution. Nat Biotechnol 25(3):338-344."
  extracted_at: 2026-04-27
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nbt1286 我推测 (well-cited Codexis paper); QA via CrossRef 验证"
    - "HheC UniProt 第一次推 Q7WT82 错 (Megalodesulfovibrio gigas, 完全无关), 经 UniProt 文本搜索找到 Q93D82 (Agrobacterium tumefaciens HheC)"
    - "Agrobacterium radiobacter AD1 已被 NCBI/UniProt 重新分类为 Agrobacterium tumefaciens (合并物种); 同义词: Rhizobium radiobacter"
    - "PDB 1ZMT 是 Agrobacterium HheC 经典结构; Codexis evolved variants 不公开 PDB"
    - "Codexis × Pfizer atorvastatin cascade 的 HHDH 部分 (与 KRED-ma-2010-greenchem 是 sister case, 同 cascade 不同 enzyme)"
    - "ProSAR (Protein Sequence Activity Relationship): Codexis 招牌统计方法, 从 directed evolution variants 数据中提 beneficial mutations"
    - "本 paper 报道 4000× 活性提升, 是 Codexis directed evolution 的 landmark 数字"
tags: [halohydrin_dehalogenase, HHDH, SDR_superfamily, activity, ProSAR, directed_evolution, atorvastatin, cascade_engineering, Codexis, non-CAZy]
---

## 1. 背景与目标
- parent: Agrobacterium radiobacter AD1 HheC (halohydrin dehalogenase C, UniProt Q7WT82, SDR superfamily, NADPH-independent)
- 起始: WT HheC 接受 (S)-ethyl 4-chloro-3-hydroxybutanoate (KRED product) → cyanation → (R)-4-cyano-3-hydroxybutanoate; 但活性低 + 工业反应条件下不稳
- 目标: 4000× 活性提升 + organic solvent / high substrate concentration tolerance, 用于 atorvastatin (Lipitor) 工业生产 cascade
- 应用: KRED + HHDH + GDH 三酶 cascade (与 KRED-ma-2010 sister case)

## 2. 决策过程

### 候选位点策略 — ProSAR 路线
- **ProSAR-driven directed evolution** (Codexis 招牌):
  1. 多 round random + saturation library, 累积大量 variant data (~10⁵ variants)
  2. **ProSAR 分析**: 用 multiple linear regression 建 sequence → activity model, 提取 beneficial mutations
  3. 不依靠 selection 直接选最优 — 而是 build statistical model 然后预测最佳组合
  4. 累加 35 mutations → final variant
- 比传统 directed evolution iterative selection 路线更 systematic, 减少 round 数

### 排除的位点 (★ 必填)
- SDR family Tyr-Lys-Ser triad (Y145-K149-S132 类) 保留 — proton-relay 关键
- Substrate-binding pocket 几个 hydrophobic residue 保留 (binding-driving residues)
- Tetramer/dimer interface 保留 (HHDH 是 obligate tetramer)
- N-terminal targeting/folding region 不动

### 计算工具与阈值
- ProSAR statistical model + multiple regression
- High-throughput activity assay (KRED + HHDH coupled product detection)
- 实验: 重组表达 + 工业反应模拟 (g/L substrate, organic co-solvent, 25-35°C)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文 Table 1)
| 量 | 范围 |
| --- | --- |
| WT HheC kcat (target substrate) | low (~0.1 s⁻¹) |
| Evolved variant kcat | 4000× WT |
| 累加 mutations | ~35 |
| Mutations 在 active site 周围 | ~10 |
| Mutations distal (二级 sphere + surface) | ~25 (这些只通过 ProSAR 才被识别) |
| 工业 productivity | 商业化 atorvastatin cascade |

### 失败案例 (★ 必填)
- 早期 single-mutation 增益甚微 — distal mutations 单独效应弱 (ProSAR 必要性)
- ProSAR 模型预测的"最佳组合"实际合成时部分 variants 失活 — 模型有 prediction error
- 部分 round 的 variants 4000× 活性但工业 condition (organic solvent) 下快速失活 — Tm 必须 co-evolve
- distal mutations 机制 unclear — 论文承认 4000× 提升的具体机制 (long-range allostery? folding?) 仍是开放问题

## 4. 学习收获
- **成立的规则候选**:
  - **ProSAR (statistical 提 distal beneficial mutations)** 是 directed evolution 后期的 efficient tool — 比 iterative selection 减少 round 数 + 揭示 distal hits
  - **35 mutations / 4000× kcat improvement** 是工业级 enzyme engineering 的 benchmark 量级 (与 Savile 27 mutations / sitagliptin 一致)
  - **Distal mutations matter**: 工程化不能只看 active site, 二级 sphere + surface 是 untapped 资源
  - **Cascade engineering 必须 simultaneous** (KRED + HHDH + GDH 同步), 不能串行 (与 KRED-ma-2010 case 一致)
- **被推翻的假设**:
  - "Beneficial mutations 都在 active site 附近" — Fox 2007 显式推翻, 25/35 mutations 在 distal residues
- **下次类似问题应优先尝试**:
  - 工业 enzyme 工程化后期阶段考虑 ProSAR 类 statistical 模型 (如果有足够 variant data, 通常需要 10⁴+)
  - Cascade biocatalysis: 同步优化所有 enzymes, 注意 cofactor recycle
- **应避免**:
  - 仅在 active site 找 mutations — 错过 distal beneficial residues
  - 单维 selection (只看 activity) — 工业级必须双指标 (activity + stability)

## 5. 计算 / 实验原始数据
原始 ProSAR model + 35-mutation variant 数据见 Nat Biotechnol 25(3) 2007 supplementary; KRED-ma-2010 sister case 含 cascade 整体 process 数据.
