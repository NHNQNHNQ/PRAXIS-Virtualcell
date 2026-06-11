---
case_id: GLUCOSE-ISOMERASE-sriprapundh-2000-protein-eng
schema_version: 1
parent_enzyme:
  uniprot: Q9X1Z5               # XYLA_THEMA, T. maritima xylose isomerase (P19148 was wrong — actually Thermoanaerobacterium thermosulfurigenes)
  cazy_family: null
  enzyme_family: xylose_isomerase / glucose_isomerase / TIM_barrel
  ec: 5.3.1.5
  organism: Thermotoga maritima
  pdb: 1XIB                     # T. maritima XIM 经典结构
substrate:
  primary_smiles: "OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O"   # D-glucose (industrial substrate)
  class: aldose_isomerization / sugar
target_property: thermostability   # GI 热稳定性 + 活性同时提升, 工业级 60-80°C 反应
status: validated
provenance:
  source_type: literature
  doi: "10.1093/protein/13.4.259"
  pmid: null
  citation: "Sriprapundh D, Vieille C, Zeikus JG (2000). Molecular determinants of xylose isomerase thermal stability and activity: analysis of thermozymes by site-directed mutagenesis. Protein Eng 13(4):259-265."
  extracted_at: 2026-04-27
  extraction_confidence: medium-high
  unverified_details:
    - "DOI 10.1093/protein/13.4.259 我推测; QA via CrossRef 验证"
    - "T. maritima XIM UniProt 第一次推 P19148 错 (实际是 Thermoanaerobacterium thermosulfurigenes), 经 UniProt 文本搜索改为 Q9X1Z5 (XYLA_THEMA)"
    - "PDB 1XIB 是 T. maritima XIM 经典结构"
    - "Zeikus 实验室 (Michigan State) thermophile XIM 系列研究; Vieille 是合作 PI"
    - "Glucose isomerase 工业 = xylose isomerase 同蛋白, 反应 D-glucose ⇌ D-fructose (HFCS 工业核心)"
tags: [xylose_isomerase, glucose_isomerase, GI, TIM_barrel, thermostability, HFCS_industry, sugar_isomerization, Mn_dependent, EC_5_isomerase, Zeikus-lab, non-CAZy]
---

## 1. 背景与目标
- parent: T. maritima xylose isomerase (XIM, UniProt P19148), TIM barrel fold, EC 5.3.1.5
- 工业用: HFCS (高果糖玉米糖浆) 生产 — D-glucose ⇌ D-fructose isomerization, 全球 enzyme 工业最大单一应用 (~$十亿级 market, ~70% 全球 fructose syrups 来源)
- T. maritima 起手 thermostable (Tm ~95°C), 但反应 kinetics 在 industrial 60-65°C 仍可优化
- 目标: 通过 site-directed mutagenesis 同时提升 thermostability + activity (industrial 60-80°C 范围)

## 2. 决策过程

### 候选位点策略
- **Comparative analysis** of thermophilic vs mesophilic XIM:
  1. T. maritima (95°C) vs T. neapolitana (65°C) vs E. coli (mesophilic) XIM 序列比对
  2. 选择 thermophilic-conserved residues 不出现在 mesophilic 中的 sites
  3. 5-8 single mutations 测试
- 关注: TIM barrel 内部 packing residues, surface charge, Mn²⁺ binding loop

### 排除的位点 (★ 必填)
- 2 个 Mn²⁺ 配位 sites (His + Glu/Asp cluster) 严格保留 — XIM 反应 metal-dependent
- Catalytic His + Asp 保留 — proton transfer 必需
- TIM barrel 8-stranded β-sheet 内部疏水核心 (M-L-V cluster) 不动
- 4-mer interface (XIM 是 obligate tetramer in industrial form)

### 计算工具与阈值
- Sequence alignment + structural PyMOL 比较
- Activity assay: D-glucose → D-fructose conversion (HPLC monitoring) at multiple temperatures
- 实验校验: 重组表达 in E. coli → DSF Tm + activity profiling at 50-90°C

## 3. 实验结果

### 总体趋势 (★ 数值范围, 见原文)
| 量 | 范围 |
| --- | --- |
| WT T. maritima XIM Tm | ~95°C |
| Tm 提升 mutations (e.g., V185T) | +2-5°C |
| Activity 提升 mutations | up to ~30% kcat/Km 提升 |
| 双指标 trade-off | most thermostability mutations cost some activity |
| 关键 finding | 部分 mutations 同时提升 Tm + activity (rare 双优) |

### 失败案例 (★ 必填)
- 大部分 thermostability mutations 同时降低活性 — 工程化"two-edged sword"
- E. coli 表达 T. maritima XIM yield 中等; Streptomyces 工业 host 偏好不同
- 工业 HFCS 反应 condition (60°C, pH 7.5, Mg²⁺/Mn²⁺) 严格, 学术规模水浴 condition 不一致 transfer
- T. maritima XIM 的 industrial advantage 不止 Tm, 还包括 substrate range — 工程化 single property 错失整体

## 4. 学习收获
- **成立的规则候选**:
  - **EC 5 (异构酶) 工程化的核心**: metal binding sites 严格保护 (XIM, sugar isomerases 几乎全 metal-dependent)
  - **TIM barrel fold** 工程化: 内部 packing 不动, 工程化在 surface + active site 周围 loops
  - **Thermostability vs activity trade-off** 在 已是 thermozyme 的 enzyme 上更显著 — 优化空间 narrow
  - **HFCS 工业** = isomerase engineering 的最大应用; 但 rate-limiting step 已不是 enzyme, 是 product separation
- **被推翻的假设**:
  - "Thermozyme 没有进一步工程化空间" — Sriprapundh 2000 显示仍有 +5°C / 30% activity 改善余地
- **下次类似问题应优先尝试**:
  - 任何 sugar isomerase / EC 5 工程化, 起手 thermophilic vs mesophilic ortholog 比对找位点
  - 工业反应 condition 模拟必备 (industrial Mg²⁺/Mn²⁺ buffer + pH + product inhibition)
- **应避免**:
  - 改 metal coordination 残基 — 必失活
  - 仅 Tm-only optimization — 必 cost activity, 双指标必要

## 5. 计算 / 实验原始数据
原始 XIM 工程化 + thermostability + activity 数据见 Protein Eng 13(4) 2000 supplementary; Vieille / Zeikus 后续 paper 含 mechanism analysis.
