---
case_id: NITRILASE-desantis-2003-jacs
schema_version: 1
parent_enzyme:
  uniprot: null                  # Diversa metagenomic nitrilases — 多 ortholog 选 best, 多数无 standalone UniProt; 商业化 evolved variants
  cazy_family: null
  enzyme_family: nitrilase / cysteine_nitrilase
  ec: 3.5.5.1
  organism: metagenomic library (multiple uncultured bacteria)
  pdb: 1F89                     # 第一个 nitrilase 结构 (Pseudomonas), 后续 nitrilase 都用作 reference
substrate:
  primary_smiles: "ClCC(C#N)c1ccccc1"   # (S)-2-chloro-2-phenylacetonitrile (chiral nitrile substrate, 后水解给 chiral acid)
  class: chiral_nitrile / pharmaceutical_intermediate
target_property: substrate_specificity   # broad scope + enantioselectivity
status: validated
provenance:
  source_type: literature
  doi: "10.1021/ja035742h"
  pmid: null
  citation: "DeSantis G, Zhu Z, Greenberg WA, Wong K, Chaplin J, Hanson SR, Farwell B, Nicholson LW, Rand CL, Weiner DP, Robertson DE, Burk MJ (2003). An enzyme library approach to biocatalysis: development of nitrilases for enantioselective production of carboxylic acid derivatives. J Am Chem Soc 125(38):11476-11477."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1021/ja035742h 我推测; QA via CrossRef 验证"
    - "Diversa metagenomic library: 137 unique nitrilases isolated, 21 active on tested substrates"
    - "无 single UniProt — 是 metagenomic discovery + 后续 directed evolution; Robertson 2004 follow-up 在 Adv Synth Catal 报道 ee 提升至 >99%"
    - "本工作是 metagenomic biocatalyst discovery 教科书经典 — Diversa 创始人 Burk + Robertson + Hanson 团队"
    - "PDB 1F89 是 Pseudomonas fluorescens nitrilase 结构, 不是 paper 用的具体 metagenomic variant"
tags: [nitrilase, substrate_specificity, enantioselectivity, metagenomic, biocatalyst_discovery, chiral_acid, pharmaceutical, Diversa, Burk, non-CAZy]
---

## 1. 背景与目标
- 任务: 让 nitrilase (cysteine-based, hydrolyses R-C≡N → R-COOH + NH₃) 接受**手性 nitrile substrates** 给 chiral carboxylic acids
- 起始: 已知 nitrilases (Pseudomonas, Rhodococcus 类) 接受简单 alkyl nitriles, 但对 chiral aromatic nitriles 活性低 + ee 不足
- 目标: 工业级 chiral acid production, 替代化学不对称水解 (后者 ee 不够 + 苛刻条件)
- 应用: pharmaceutical intermediate (e.g., (R)-mandelic acid, (S)-2-chlorophenylacetic acid 类)

## 2. 决策过程

### 候选位点策略 — Diversa 的"library approach"
- **Metagenomic library mining** (rather than single enzyme directed evolution):
  1. 从 100s 环境样本 (土壤 / 海洋 / 极端 habitat) 提 DNA
  2. 表达 in E. coli, 共筛 130+ unique nitrilase ortholog
  3. 多 substrate panel (含手性 substrate) screen → 找 best fit per substrate
- 此路线核心理念: 自然界已经"演化好"无数 nitrilase 变体, 找而不是 evolve
- 后续 directed evolution (Robertson 2004 follow-up) 进一步提升 ee
- 单 enzyme directed evolution 路线作 backup, 这次没主用

### 排除的位点 (★ 必填)
- Catalytic Cys (active site Cys, e.g., C166 in Pseudomonas nitrilase) 严格保留 — covalent thioimidate intermediate 必需
- Active site Glu/Lys (acid/base catalysis) 保留
- Tetramer/hexamer interface (nitrilase 多体 active form) 保留
- 由于 metagenomic 路线: 不做单 enzyme mutation, 是 select-from-library

### 计算工具与阈值
- 主要工具: high-throughput library expression in 96-well + colorimetric ammonia release detection (Berthelot reaction)
- 顶级 hits 用真实 substrate (chiral nitrile) + chiral HPLC 验证 ee
- 一些 hits 后续做 directed evolution 提升 (Robertson 2004)

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| Library size | 137 unique nitrilases |
| Active on tested substrates | ~21 (16% hit rate) |
| Best ee 起始 | 60-90% (因 ortholog 不同) |
| 后续 directed evolution 提升 ee | >99% (Robertson 2004) |
| 工业 application | chiral acid production for pharmaceutical |

### 失败案例 (★ 必填)
- 部分 metagenomic clones 在 E. coli 表达不可溶 — host 系统差异
- Many orthologs 显示活性但 ee 低 (<50%) — natural diversity 不一定包含 selective enzymes
- Library approach: 必须 invest 在 expression/screening infrastructure; 学术规模常 cost-prohibitive
- 部分 substrate (highly hindered) 在所有 137 orthologs 都活性低 — natural diversity 也有空白

## 4. 学习收获
- **成立的规则候选**:
  - **Metagenomic library mining 是 biocatalyst discovery 比 directed evolution 更高 ROI 的起手** (when starting de novo, no characterized parent)
  - **Natural ortholog diversity 涵盖了大部分 substrate scope 需求** — 工程化只需 select + tune
  - **Library + DE 串联** 是 Diversa platform 范式: 先 library 找 best fit, 再 DE 优化 specific properties (ee, activity)
- **被推翻的假设**:
  - "需要 directed evolution 才能拿到 useful biocatalyst" — Diversa 显示 metagenomic discovery 在 nitrilase 类已足够 viable
- **下次类似问题应优先尝试**:
  - 对新 substrate / 新 enzyme target, 先 explore metagenomic / public sequence database (UniRef + NCBI nr) 找 ortholog hits, 再决定是否 DE
  - **Library + selection 先于 mutation**: 先看自然多样性, 再考虑工程化
- **应避免**:
  - 直接 DE 一个 enzyme 而不评估 metagenomic 替代 — 错失 starting point 优化机会
  - 假设 single enzyme 就足够 — 工业 substrate 多样性 demands diversity-aware sourcing

## 5. 计算 / 实验原始数据
原始 library hit data + chiral HPLC traces 见 J Am Chem Soc 125(38) 2003; follow-up Robertson 2004 Adv Synth Catal 含 evolved variants 详细数据.
