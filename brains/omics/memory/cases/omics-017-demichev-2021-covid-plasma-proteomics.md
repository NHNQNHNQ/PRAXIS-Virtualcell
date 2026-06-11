---
case_id: omics-017-demichev-2021-covid-plasma-proteomics
schema_version: 1
modality: proteomics
study: "Demichev et al 2021, A time-resolved proteomic and prognostic map of COVID-19"
public_accession: "PXD024041 (PRIDE) + companion ProteomicsDB submissions"
doi: 10.1016/j.cels.2020.10.010
organism: Homo sapiens
tissue: blood plasma
study_design: cohort
assay_subtype: dia_ms_plasma
cell_type_focus: [bulk_plasma_proteome]
tools: [DIA-NN 1.8, MaxQuant 2.0, Perseus 1.6, MSstats 4.0, limma 3.46]
method_choice: [dia_ms, dia_nn_maxlfq, plasma_depletion_optional, missing_value_modeling, pca_for_qc]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1016/j.cels.2020.10.010
  extracted_at: 2026-04-29
tags: [proteomics, dia_ms, plasma, covid, time_resolved, dia_nn]
---

# Demichev 2021：COVID-19 时间分辨血浆蛋白质组（DIA-MS 范例）

## Background
~700 个血浆样本，覆盖 ~200 个 COVID-19 患者（mild → critical）+ 健康对照，跨多个时间点。Data-Independent Acquisition (DIA) MS + DIA-NN 量化。**plasma proteomics 范式**：~5000 蛋白质量化，时间维度 + cohort，预后建模。这是 PRAXIS-Omics 的第一个 proteomics case，覆盖 DIA-MS 工作流的核心决策（与 scRNA / bulk RNA 完全不同的 wet → analysis pipeline）。

## What I actually did
1. **MS data acquisition**：Bruker timsTOF Pro DIA-PASEF；每个样本 ~30 min gradient
2. **DIA-NN 1.8 search**：library-free 模式（spectral library 由 DIA-NN 内部生成），`--match-between-runs`，FDR 1% peptide + protein
3. **Quantification**：MaxLFQ algorithm in DIA-NN（不用 raw intensity sum）—— more robust to missing values
4. **Per-batch QC**：median CV between replicates，injection-level intensity drift；> 30% CV 的 sample 重测
5. **Missing value handling**：DIA-NN MaxLFQ 已模型化部分 missing；剩余 missing > 50% 的蛋白丢弃；剩余 < 50% missing 的 protein 用 KNN imputation（**仅在 PCA / clustering 时用；统计 test 用 MSstats 不 impute**）
6. **Normalization**：median-centered log2 ratio (MaxLFQ output)；per-injection normalization 默认开
7. **Batch effect**：MS run 顺序 + day-of-injection 是 batch；用 ComBat 校正前先 PCA 看是否需要
8. **Cohort 比较**：limma + linear model with `~ batch + severity + time`
9. **Pathway enrichment**：fgsea / Reactome on protein → corresponding gene
10. **Time-resolved trajectory**：mixed-effect model per protein with random subject effect (longitudinal)

## ★ 排除/不做的事
- **DDA / library-based search 当默认**：DIA + library-free DIA-NN 是 2021+ 的 SOTA；DDA 在 plasma 高 dynamic range 下 ~3000 蛋白，DIA 可达 ~5000
- **Raw intensity sum 当 quant**：MaxLFQ 算法处理 missing 更稳定
- **Imputation 后跑 statistical test**：违反假设；MSstats / limma 直接处理 missing
- **跨 instrument 不校正**：不同 timsTOF / Q-Exactive 的 m/z 范围 + ppm 不同
- **不做 protein FDR 控制**：peptide FDR 1% 不等于 protein FDR 1%；DIA-NN 原生支持 protein-level FDR
- **完全删除有 missing value 的蛋白**：丢失大量信号；> 50% missing 才丢
- **不区分 plasma vs serum**：凝血过程不同，plasma is preferred for multi-omics

## ★ 失败模式
- **Sample contamination by RBC lysis**：hemoglobin overwhelms low-abundance plasma proteins；离心质量差时严重
- **Albumin / IgG 主导**：未做 depletion 时 top14 蛋白占 90% 信号 → 低丰度 cytokine 测不到；但 depletion 引入 batch effect → trade-off
- **Time bias**：早期 sample 都是 critical 患者（早死亡），晚期 sample 是 mild —— 时间和 severity 共变
- **Batch ≠ severity**：cohort 招募集中在某 wave 后 → batch 与 cohort 混淆；招募阶段必须均衡
- **Peptide → protein assignment ambiguity**：peptide 可能 map 到多个 protein（"razor peptide"）；DIA-NN 默认按 Occam's razor 分配
- **Inter-run variability without MS QC standard**：每批 inject 内部标准（如 iRT peptide）才能跨批比较

## ★ 方法选择决策链
```
proteomics 数据？
├─ DIA vs DDA → DIA + DIA-NN (default 2021+) for plasma high dynamic range
├─ Quantification → MaxLFQ (DIA-NN built-in; not raw intensity)
├─ Missing handling
│   ├─ For PCA / clustering → KNN impute
│   └─ For DE / regression → MSstats / limma 直接 model missing
├─ Batch correction
│   ├─ MS run order → 用 ComBat 或加 covariate
│   └─ Instrument cross-comparison → 谨慎；优先 single-instrument
├─ Plasma depletion (top14)
│   ├─ Trade-off：低丰度可测 vs depletion batch effect
│   └─ Recommended: yes for biomarker discovery, no for global profiling
└─ Multi-protein composite score → 比 single protein 更稳，但需要多 cohort 验证
```

## ★ QC sanity check (known answer)
- Anchor (Demichev 2021 COVID plasma)：
  - **SAA1, SAA2** (acute phase reactants) 在 severe COVID 升高 > 10× 健康对照
  - **CRP** 同向上调
  - **APOA1, APOA2** (HDL component) 下调 in severe（已知 cholesterol 通路扰动）
  - **GSN (gelsolin)** 下调 in severe（actin sequestration）
  - 健康对照 PCA 与 mild COVID 区分 + severe 形成第三 cluster
- Pass criterion：SAA1 LFC > 3 in severe + APOA1 LFC < -1 + PCA 三 cluster
- Fail criterion：SAA1 不变 → batch 主导（severity 信号被压）；PCA 单 cluster → normalization 过度

## Lessons → seeds for rules
1. **DIA-MS + DIA-NN MaxLFQ 是 2021+ proteomics 默认**（不是 DDA）
2. **Imputation 仅在 PCA / clustering 时用**；statistical test 让 MSstats / limma 自己处理 missing
3. **Missing < 50% 才 keep**；> 50% 丢
4. **MS run order = batch**：必须建模或 ComBat
5. **Time × severity 共变**是 cohort 招募阶段的设计问题，不能事后挽救
6. **iRT internal standard** 跨批 sample 是 mandatory QC（peptide retention time normalization）
7. **Plasma depletion 是双刃剑**：low-abundance 可测但 batch effect 进来；biomarker discovery 倾向 yes
