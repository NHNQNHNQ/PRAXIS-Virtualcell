---
case_id: omics-021-pluskal-2010-mzmine-metabolomics
schema_version: 1
modality: metabolomics
study: "Pluskal et al 2010, MZmine 2: Modular framework for processing, visualizing, and analyzing mass spectrometry-based molecular profile data (extended via MZmine 3 / Schmid 2023)"
public_accession: "MetaboLights MTBLS / GNPS public datasets (per study)"
doi: 10.1186/1471-2105-11-395
organism: "Homo sapiens / Mus musculus / Plant / Microbe (multi-organism)"
tissue: "plasma / urine / cell extract / tissue homogenate (LC-MS or GC-MS)"
study_design: cohort
assay_subtype: lc_ms_untargeted_metabolomics
cell_type_focus: [bulk_metabolome]
tools: [MZmine 3, XCMS 4.0, MS-DIAL 5, MetaboAnalyst 6.0, GNPS, SIRIUS 5, OpenMS 3]
method_choice: [untargeted_lcms, peak_picking_centwave, retention_time_alignment, gap_filling, spectral_matching, kegg_pathway_mapping]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1186/1471-2105-11-395
  extracted_at: 2026-04-29
tags: [metabolomics, lc_ms, mzmine, untargeted, peak_picking, annotation]
---

# Pluskal 2010 MZmine 2 / Schmid 2023 MZmine 3：LC-MS untargeted 代谢组学标准

## Background
Untargeted LC-MS metabolomics 的标准 pipeline：mzML raw data → peak picking → 跨样本 alignment → gap filling → annotation → 统计。MZmine 3 / XCMS 是社区两大主流工具。**case-based learning 角度**：metabolomics 与转录组/蛋白质组数据特性完全不同 — 化学结构标识、isotope pattern、adduct ion、pathway mapping 都是 LC-MS 特有问题。这是 PRAXIS-Omics 第一个代谢组学 case。

## What I actually did
1. **Raw data conversion**：vendor 格式 (.raw / .d / .wiff) → mzML（msconvert）；mass accuracy 校正（lock mass）
2. **Peak picking**：MZmine 3 Mass detector → ADAP/CentWave Chromatogram builder → ADAP feature finder
   - **m/z tolerance**: 5-10 ppm (high-resolution Orbitrap / TOF)
   - **noise level**: 1e3 (positive mode), 5e2 (negative)
   - **Peak duration**: 0.05 - 1.5 min
3. **Retention time alignment**：跨样本对齐（RANSAC 或 join aligner with m/z + RT tolerance）
4. **Gap filling**：alignment 后某些 sample 在 feature 处未检出 → re-extract 信号；用 same-RT-window XIC
5. **Isotope grouping + adduct annotation**：合并同一 metabolite 的 [M+H]+, [M+Na]+, [M+K]+, [M+H-H2O]+, dimer [2M+H]+ 等 ion；只保留 monoisotopic peak
6. **Annotation 三级**：
   - **Level 1**: authentic standard (m/z + RT + MS² match) — 真鉴定
   - **Level 2**: spectral library match (MS²) — putative annotation
   - **Level 3**: putative class (functional group) — 仅 m/z 推测
   - **Level 4**: unknown
7. **Statistical analysis**：MetaboAnalyst 6.0；log + Pareto scaling；PLS-DA / OPLS-DA 监督模式或 PCA 无监督
8. **Pathway mapping**：KEGG / HMDB / ChEBI ID → MetaboAnalyst pathway analysis (Hypergeometric + impact)
9. **Validation**：QC pool（每 5-10 个 sample 插入 pooled QC）→ peak intensity CV < 30% 视为 robust feature；其他 drop

## ★ 排除/不做的事
- **不做 QC pool**：injection drift 看不出来；时间过半 sample 信号衰减但你不知道
- **不做 isotope grouping**：单个 metabolite 被算成 5-10 个 feature → 统计 power 浪费、pathway map 错
- **Annotation Level 3 信任**：化学家级别的"putative" 误用作机制结论是常见学术错误
- **Cross-mode (positive + negative) 直接合并 feature table**：m/z 关系不同；要么分开做要么 careful annotation
- **跨实验室 / 跨 instrument 数据合并**：retention time + m/z accuracy 不同；只能在 annotation level 合并
- **统计前不 log + scale**：metabolomics intensity 跨 5-6 数量级，直接 ANOVA 假设违背
- **m/z tolerance 设过宽**：错误 grouping 不同 metabolite
- **n_samples per group < 8 跑 PLS-DA**：高度过拟合

## ★ 失败模式
- **Solvent contamination**：phthalates / PEG / ions from tubing 是 ubiquitous contaminant；blank injection (solvent only) 必扣除
- **Carryover**：上一 sample 的强信号留到下一个 → 必须 sample 之间 blank wash
- **Adduct 混淆**：[M+Na]+ 和另一 metabolite 的 [M+H]+ 巧合 m/z 一样
- **In-source fragmentation**：electrospray 内部断裂 → fragment ion 被当成新 feature
- **Suppression**：matrix effect 在 plasma 严重；spike-in internal standard 校正
- **RT shift > tolerance**：column aging → tail end of run RT shift；alignment 失败
- **Negative-mode polarity 弱信号**：lipid + sugar 在 positive mode 强，amino acid 在 negative 强
- **Pathway analysis ID 不匹配**：KEGG vs HMDB vs ChEBI 不同 ID；映射失败导致 pathway 缺失
- **Quantification 假设 linear**：高浓度饱和；需要 dilution series 验证 linear range

## ★ 方法选择决策链
```
LC-MS untargeted metabolomics?
├─ Sample type
│   ├─ Plasma → positive + negative mode；溴化物 + 蛋白沉淀 prep
│   ├─ Urine → positive mode；creatinine normalization
│   ├─ Tissue → polar + nonpolar extract分开
│   └─ Cell extract → quench rapidly
├─ Instrument
│   ├─ Orbitrap (high mass accuracy ~ppm) → MZmine 3 / XCMS
│   ├─ TOF → MS-DIAL (DIA 友好)
│   └─ Triple quad (targeted) → 不同 workflow，跳过此 rule
├─ Annotation tier
│   ├─ Level 1 → authentic standard 必备
│   ├─ Level 2 → MS² library match (METLIN / NIST / GNPS)
│   ├─ Level 3 → 化学家 review；不直接发表机制结论
│   └─ Level 4 → unknown 但仍可统计
└─ Pathway analysis
    ├─ KEGG → cleanest map but smaller universe
    ├─ HMDB + Reactome → human-focused
    └─ MetaboAnalyst → user-friendly aggregator
```

## ★ QC sanity check (known answer)
- Anchor (典型 plasma untargeted)：
  - **Pooled QC injection CV** < 20% on top 80% features → pipeline robust
  - **Internal standards (deuterated metabolites)** RT shift < 0.05 min, intensity CV < 15%
  - **Total feature count** 在 Orbitrap plasma 通常 5000-10000 (positive mode)
  - **Annotation level 1 + 2 比例** 通常 < 30% (level 4 unknown 是大头)
  - **Known abundant metabolite (e.g., creatinine in urine, glucose in plasma)** 应在 top 20 intensity peak
- Pass criterion：QC CV < 30% + 内标 stable + 已知高丰度 metabolite 命中
- Fail criterion：QC CV > 50% → injection drift 严重；内标 RT shift > 0.1 min → column 老化

## Lessons → seeds for rules
1. **QC pool 是 mandatory** (每 5-10 sample)；不做 = 数据不可信
2. **Isotope + adduct grouping 必做**：feature 数会从 ~20k 缩到 ~5k metabolite-level
3. **Annotation tier 必标注**：Level 1-4 严格区分；mechanism 解读只在 Level 1+2
4. **Cross-mode (pos/neg) 分别做 statistical**，annotation 阶段合并
5. **Internal standard spike-in** 是 quantitative metabolomics 必备（不只是 QC pool）
6. **Sample prep dominates**：plasma vs urine vs tissue 走完全不同 workflow
7. **Pathway analysis 用 KEGG/HMDB ID 不用名字**：name 歧义大 (citrate vs citric acid vs cit)
