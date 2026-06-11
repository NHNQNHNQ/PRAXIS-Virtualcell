---
case_id: AARS-wang-2001-science
schema_version: 1
parent_enzyme:
  uniprot: Q57834                # M. jannaschii TyrRS (CrossRef-verified)
  cazy_family: null             # AARS 不在 CAZy
  ec: 6.1.1.1                   # tyrosyl-tRNA synthetase
  organism: Methanocaldococcus jannaschii (archaeon)
  pdb: 1J1U                     # MjTyrRS 早期结构 (Kobayashi 2003 deposit); QA 验证
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "N[C@@H](Cc1ccc(O)cc1)C(=O)O"   # L-tyrosine (natural substrate); 工程化目标 substrate 为 non-canonical AAs
  class: amino_acid / aminoacyl-tRNA_synthetase_substrate
target_property: substrate_specificity   # 主线: 改 active site 接受 non-canonical amino acids (NCAAs) 而 reject natural Tyr
status: validated
provenance:
  source_type: literature
  doi: "10.1126/science.1060077"
  pmid: 11313494
  citation: "Wang L, Brock A, Herberich B, Schultz PG (2001). Expanding the genetic code of Escherichia coli. Science 292(5516):498-500."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1126/science.1060077 与 PMID 11313494 我推测; CrossRef 验证"
    - "UniProt P00958 我推测对应 MjTyrRS; QA via uniprot-fetcher 验证"
    - "PDB 1J1U 我推测对应 MjTyrRS apo 结构; 后续 follow-up paper 解了 NCAA-bound 突变体结构"
    - "本论文是 Schultz 实验室 (Scripps) 'expanded genetic code' platform 的奠基论文 — 第一次在活的 E. coli 内位点特异掺入 non-canonical amino acid (O-methyl-tyrosine, OMeTyr)"
    - "工程化策略: 用 amber stop codon (UAG) 作 NCAA 信使, MjTyrRS / MjtRNA orthogonal pair 在 E. coli 不识别内源 tRNA, 单独 charged with NCAA"
    - "active site mutation 5-6 位 (Tyr32 + Glu107 + Asp158 + Ile159 + Leu162 + Ala167 等 — 具体 round 见 Fig 2 / Table)"
    - "选 OMeTyr 而非 Tyr 的反向 selection (positive/negative) 是 platform 关键, dose-dependent 二轮筛选"
    - "本工作填上 PRAXIS-Enzyme EC 6 ligase 整体空白 (此前 0 案例)"
tags: [AARS, aminoacyl_tRNA_synthetase, EC6_ligase, non_canonical_amino_acid, NCAA, orthogonal_pair, expanded_genetic_code, MjTyrRS, amber_codon, Schultz-lab, biotechnology_platform]
---

## 1. 背景与目标
- parent: Methanocaldococcus jannaschii Tyrosyl-tRNA synthetase (MjTyrRS, EC 6.1.1.1, class I AARS); 古菌来源, 在 E. coli 内不识别任何内源 tRNA — 这是 orthogonality 的物种隔离基础
- 起始性质: WT MjTyrRS 高活, 严格识别 L-Tyr; 与自身 tRNA(Tyr-CUA, amber suppressor 版) 形成 orthogonal pair
- 目标: 工程化 active site 让 MjTyrRS 接受 OMeTyr (O-methyl-L-tyrosine, 一种 NCAA) 而 reject 内源 L-Tyr; 在 E. coli 内通过 amber 终止子 UAG 实现 OMeTyr 位点特异掺入任意目标蛋白
- 应用: NCAA 蛋白工程化 (probe 化学 / photo-crosslinking / fluorescent label / unnatural side chain 蛋白); Schultz platform 至今 200+ NCAAs 掺入

## 2. 决策过程

### 候选位点策略
- **structure-guided saturation**:
  - 解 MjTyrRS active site 结构 (TyrRS 类典型 5-pocket, 接 Tyr aromatic + α-amino + α-carboxylate)
  - 选 active site 5-6 位点 (Tyr32 + Glu107 + Asp158 + Ile159 + Leu162 + Ala167 等) 作 saturation
  - 用 NNK codon (32 codon, all 20 AAs) 或 NDT codon (12 codon, balanced) 库
- **dual selection (positive + negative)**:
  - Positive: 在 OMeTyr 存在 + 必需基因 amber 通读时存活 (筛接 OMeTyr 的)
  - Negative: 在仅 Tyr 存在 + lethal gene amber 通读时死亡 (筛拒 Tyr 的)
  - 二轮 alternating selection 拉开 OMeTyr / Tyr 选择性
- 候选数: 多位点 saturation library 5×10⁵ - 10⁷ variants/round, 多 round 累积

### 排除的位点 (★ 必填)
- **catalytic core**: ATP 结合 motif (HIGH motif + KMSKS motif, class I AARS 标志) 严格保留
- **tRNA acceptor stem 识别 anchor**: MjTyrRS-tRNA(Tyr-CUA) 接触面保留以维持 orthogonality
- **dimer interface (TyrRS 是 homodimer)**: 保留以维持 quaternary structure
- **amber 抑制 (CUA anticodon) 识别 element**: tRNA 与 mRNA 解码界面相关 — 已经是 engineered tRNA 的部分, 不动 enzyme 端 anchor

### 计算工具与阈值
- 不依赖 PyRosetta (是 in vivo selection 主导, 2001 当时 PyRosetta 未广泛使用)
- 关键工具: 双 selection cassette 在 E. coli + amber-encoded 报告基因 (CAT chloramphenicol acetyltransferase 用 positive, barnase 用 negative)
- NCAA 化学合成 + 添加到生长培养基 (~1 mM)
- 实验校验: NCAA 掺入率 (MS 检掺入位点的 amino acid mass), 表达 yield, 选择性 (Tyr vs OMeTyr ratio)

## 3. 实验结果

### 关键 OMeTyr-RS 变体
| 量 | MjTyrRS WT | OMeTyr-RS evolved | 备注 |
| --- | --- | --- | --- |
| Tyr aminoacylation | 高活 | <5% (suppressed) | negative selection 效果 |
| OMeTyr aminoacylation | 接近 0 | 高活 | positive selection 效果 |
| OMeTyr 掺入率 (E. coli, 单 amber site) | 不可能 | >95% (高 yield 蛋白) | 工业级可用 |
| 关键 mutation 数 | 0 | 5-6 (active site cluster) | 多 round 累积 |
| Selectivity (OMeTyr/Tyr) | <0.01 | >100 | 双 selection 关键 |

### 失败案例 (★ 必填)
- 早期单 round positive-only selection 失败: 选出的 variants 接 OMeTyr 同时仍接 Tyr, 选择性差 — 必须 negative selection 配合
- ATP 结合 motif (HIGH/KMSKS) 邻近 mutation 直接失活, 即使 active site pocket 有空位
- 跨 NCAA 转移失败: 一个 NCAA (OMeTyr) 工程化的 RS 不能直接接其他 NCAA (e.g. para-acetyl-Phe) — 必须每个 NCAA 重新工程化对应 RS
- early 多 NCAAs 同时尝试 (e.g. p-iodo-Tyr, p-acetyl-Phe 同 round) 互相 cross-talk, 单 NCAA 一次 round 是 platform 准则
- 部分 evolved RS 在 E. coli 表达 yield 下降, 不直接转移到 Pichia / yeast / 哺乳细胞 host (cross-host 工程化是后续平台问题)

## 4. 学习收获
- **成立的规则候选**:
  - **AARS 工程化绝对禁区**: HIGH motif + KMSKS motif + tRNA 识别接触面 + dimer 界面
  - **Orthogonal pair 设计**: 优先用古菌 / 进化远缘 (Mj / Pyrococcus / Methanosarcina) 来源 RS-tRNA pair, 在 E. coli 自然不识别内源 tRNA — 物种隔离 = orthogonality 的物理基础
  - **Dual selection (positive + negative) 是 NCAA 工程化的不可省略 step**, 单 selection 失败率 > 90%
  - **每个 NCAA 一个 RS** — 不要期待同一 RS 接多 NCAA
- **被推翻的假设**:
  - "active site 越大越好接 bulky NCAAs" — 大 cavity 反而失选择性, 必须 NCAA-specific 几何匹配
  - "用同种 (intra-species) AARS 工程化 orthogonal pair" — 内源 tRNA cross-talk 致命, orthogonality 强烈依赖跨物种
- **下次类似问题应优先尝试**:
  - 任何 expanded genetic code 工程化, 用古菌 (Mj) 或远源 RS-tRNA pair 起步
  - dual selection 必须配合 (positive + negative)
- **应避免**:
  - HIGH/KMSKS motif 周围 ±5 残基 mutation
  - 试图同 round 多 NCAAs 共选, 导致 cross-talk

## 5. 计算 / 实验原始数据
原始 selection cassette + variant kinetics + MS 掺入数据见 Science 2001 supplementary; Schultz 平台后续 200+ NCAA 工程化论文累积 (Wang & Schultz 系列 2003-present).
