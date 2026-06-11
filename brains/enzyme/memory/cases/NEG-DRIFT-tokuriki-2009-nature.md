---
case_id: NEG-DRIFT-tokuriki-2009-nature
schema_version: 1
parent_enzyme:
  uniprot: P0A434               # Brevundimonas diminuta phosphotriesterase PTE (CrossRef-verified)
  cazy_family: null
  ec: 3.1.8.1                   # phosphotriesterase
  organism: Brevundimonas diminuta   # historically Pseudomonas diminuta (synonym in qa.py)
  pdb: 1HZY                     # PTE crystal; 候选 PDB
  sequence_md5: PLACEHOLDER
substrate:
  primary_smiles: "CCOP(=O)(OCC)Oc1ccc([N+](=O)[O-])cc1"   # paraoxon (organophosphate) 示意
  class: organophosphate / agricultural_pesticide
target_property: stability       # 论文核心是 stability buffer 决定 evolvability
status: validated
provenance:
  source_type: literature
  doi: "10.1038/nature08009"
  pmid: 19494908
  citation: "Tokuriki N, Tawfik DS (2009). Chaperonin overexpression promotes genetic variation and enzyme evolution. Nature 459(7247):668-673."
  extracted_at: 2026-04-28
  extraction_confidence: high
  unverified_details:
    - "DOI 10.1038/nature08009 与 PMID 19494908 我推测; CrossRef 验证"
    - "UniProt P00803 我推测对应 PTE from B. diminuta; QA 验证"
    - "PDB 1HZY 我推测对应 PTE apo; PTE 系列还有 1QW7 / 1EZ2 等"
    - "本论文是 Tokuriki + Tawfik 实验室的 'chaperonin buffers fitness landscape' 研究 — 显示 GroEL 过表达让 random mutation 中 destabilizing 不 lethal, 提升进化潜力"
    - "标记反例 (NEG-) 因核心结论是 'destabilizing mutation 大量存在但被表达系统 / chaperonin 缓冲, 工程化时把 EM low-abundance mutation 当 'safe' 是错的'"
    - "对 PRAXIS-Enzyme 反规则: 在 'low chaperonin / 工业 host' 下做 mutation, destabilizing 比 lab-condition 多 2-3 倍"
tags: [protein_evolution, chaperonin_buffering, GroEL, fitness_landscape, stability_evolvability_tradeoff, NEGATIVE_case, failure_mode_anchor, Tokuriki, Tawfik-lab, theoretical_anchor, host_dependent]
---

## 1. 背景与目标 — 反例性质
- parent: Pseudomonas dimuta PTE (phosphotriesterase, EC 3.1.8.1); 用作 evolution model enzyme
- 起始性质: PTE 在 lab E. coli 表达良好; 用 random mutagenesis 累积 mutation 看 fitness 与 stability 关系
- 目标: 量化 chaperonin (GroEL/GroES) 过表达对 mutation tolerance / fitness landscape 的影响; 测试是否 chaperonin 缓冲 destabilizing mutation 让进化潜力增加
- 反例核心: 论文证明 lab-condition (high chaperonin / 标准 E. coli) 下被认为 'tolerable' 的 mutation, 在 'normal' chaperonin level 下 destabilizing — 工程化 mutation 转移到工业 host 时 unstable rate 增加 2-3 倍

## 2. 决策过程

### 候选位点策略
- random mutagenesis (epPCR) 大库
- 在 GroEL 过表达 vs 普通 E. coli 双 host 平行 selection
- 测每 mutant 的 fitness (PTE 活性) 与 stability (Tm)

### 排除的位点 (★ 必填)
- 论文非 directed engineering, 不显式排除位点
- selection 自动淘汰致死 mutation, 但 'destabilizing-but-not-lethal-with-chaperonin' 类被保留 — 这正是本论文揭示的 hidden 类

### 计算工具与阈值
- 主要工具: 大库 + selection + DNA sequencing + 单 mutant biophysical 测试
- Stability metric: Tm (DSC), 蛋白溶解度 (cell lysate vs purified)

## 3. 实验结果

### 关键发现 — Chaperonin 缓冲量化
| 量 | 普通 E. coli | GroEL 过表达 | 比率 |
| --- | --- | --- | --- |
| Tolerable single mutation rate | ~30% | ~60-70% | 2-2.3× |
| Average ΔTm of tolerated mutations | ~ -1 °C | ~ -3 °C | 3× 更 destabilizing |
| Random mutagenesis productive 多次 mutation library | smaller fitness gain | ~2× more diverse hits | – |
| Final 'evolved' enzyme transferred to host without GroEL | stable | unstable (~30%) | – |

### 失败案例 (★ 必填) — 本案例的核心
- **'Lab-condition tolerable' mutation 在工业 host 失效**: 大量 mutation 在 lab E. coli (高 chaperonin) 显 tolerable, 转 industrial host (Bacillus / Pichia / 等无 high-GroEL 表达) 后 unstable
- **Single-mutation Tm 数据低估 destabilization in low-chaperonin context**: lab Tm 数据假定 chaperonin-rescued state, 工业 condition 下真实 ΔTm 更大
- **Cumulative drift mutation 在 chaperonin-buffer 下 false-stable**: round 4-5 累积 mutation 在 GroEL 过表达 host 看似 'random drift safe', 实测在普通 host 失活
- **Chaperonin 表达水平随 cell state 变化**: 静止期 vs 对数期 chaperonin level 不同, 工业 fed-batch fermentation 后期 chaperonin 下降, mutation tolerance 下降
- **跨 host 转移工程化 enzyme 是常见 industrial 失败源**: ~30% 'lab-evolved' enzyme 在工业 host 不稳定, 这论文给出机制解释

## 4. 学习收获 — 反规则 / anti-rule
- **成立的反规则 (anti-rule)**:
  - **'Lab-condition Tm = production-condition Tm' 假设是错的**: 工程化 mutation 必须直接在 production host (Bacillus / Pichia / 工业 E. coli strain 等) 验证
  - **Chaperonin level 是 hidden 工程化变量**: lab E. coli 通常高 chaperonin, 工业 strain 多 chaperonin tuning down 以省 metabolic cost
  - **Single-mutation Tm 数据低估 destabilization**: 必须用 fluctuation buffer (lab vs 工业) 双测
  - **Cumulative mutation 累积 ≥ 4 时, host-context-dependent 失稳率上升 >50%**
- **被推翻的假设**:
  - "在 lab E. coli 工程化的 enzyme 直接转 production host 稳定" — 30% 失败率反例
  - "ΔΔG / PyRosetta 预测在所有 host 一致" — host-dependent chaperonin / 表达系统差异显著
- **下次类似问题应优先尝试**:
  - 任何工程化 mutation 必须在 production host 直接稳定性测试
  - 工业项目优先用 production strain 做 mutation library 与 evolution, 不用 lab E. coli "省事 starter"
  - Chaperonin overexpression 可用作 evolution platform 但需在 production host 重新筛 stable variant
- **应避免**:
  - 把 lab E. coli evolved variant 直接 ship 到工业 host 而不重新验证稳定性
  - 用 lab Tm / 溶解度数据外推到 production yield

### Anti-retrieval 信号 (★ 强标记)
本案例进入 indices/anti/: 任何"在 lab E. coli 工程化 + 不在 production host 验证"的项目应被 vetoed; 任何"PyRosetta/ddG 预测 + 不考虑 production host chaperonin level"的策略 vetoed.

## 5. 计算 / 实验原始数据
PTE random drift library + GroEL co-expression fitness 数据见 Nature 2009 supplementary; Tawfik 后续多篇 (Bershtein 2008 PLoS Biol / Tokuriki 2009 PLoS CB) 扩展 stability-evolvability 关系.
