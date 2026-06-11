---
case_id: omics-026-tung-2017-scrna-batch-effect-classic
schema_version: 1
modality: scRNA_seq
study: "Tung et al 2017, Batch effects and the effective design of single-cell gene expression studies"
public_accession: "GSE77288"
doi: 10.1038/srep39921
organism: Homo sapiens
tissue: "lymphoblastoid cell lines (LCL) from 3 unrelated YRI donors"
study_design: method_failure_demonstration
assay_subtype: fluidigm_c1_smartseq_3_donors_3_batches
cell_type_focus: [single_cell_type_LCL, batch_design_demonstration]
tools: [Fluidigm C1, Smart-seq, ERCC spike-in, scater 0.99, scran 0.99, limma, sva ComBat]
method_choice: [batch_design_demonstration, ercc_spike_in, balanced_blocked_design, batch_correction_baseline]
status: validated
validated: true
source: praxis_seed
case_class: failure_pattern
provenance:
  source_type: literature_failure_demonstration
  doi: 10.1038/srep39921
  extracted_at: 2026-05-01
tags: [failure_case, batch_effect, c1_capture, experimental_design, ercc_spike_in, foundational]
---

# Tung 2017：scRNA batch effect 教科书反例（C1 capture 顺序主导 PCA）

## Background
Stephens/Gilad 实验室 2017 年的小但关键论文，被后续每个 scRNA 教程 / scIB benchmark 反复引用。**实验设计**：3 个 unrelated YRI 个体的 lymphoblastoid cell line (LCL) × 3 次独立 Fluidigm C1 capture × 同一 cell line。**理想结果**：cell line 是 biology，capture 是 batch；若实验设计正确 + batch correct 得当，PCA 应该 cell-line-driven。**实际结果**：未校正时 **PC1 完全是 capture 顺序**（batch），PC2 才是 cell line。这是 case-based learning 的"教科书反例"——可视化展示了 batch effect 在 single cell 中的 dominant 性，比 case 003 (Tabula Muris cross-platform) 更教学化、更小、更容易复现。

## What this paper actually did (and what it found)
1. **设计**：3 cell line (NA19098, NA19101, NA19239) × 3 capture × 96 cells/capture = 864 cells total
2. **平衡 block design**：每个 capture 包含所有 3 cell lines（避免 cell line 与 capture 完全 confound）—— **这是关键**：如果一个 capture 只含一个 cell line，batch 与 biology 不可分
3. **ERCC spike-in**：每 cell 加同量 ERCC RNA，作为已知 ground truth 量化 technical noise
4. **未校正 PCA**：PC1 (29% variance) 完全沿 capture 顺序排（batch 1 / 2 / 3 集成各 cluster）；PC2 (15%) 才是 cell line
5. **校正 (limma removeBatchEffect / ComBat)** 后：PC1 (24%) 主要是 cell line；PC2 (11%) 残留 capture
6. **DE analysis**：未校正时跨 capture 的"DE genes" 数千；校正后剩余 ~200，与 cell line genetic difference 一致
7. **ERCC variance 量化**：未校正 ERCC variance ≈ biology variance（信号:噪声 ≈ 1:1）；校正后 SNR 提升至 5:1
8. **结论 / 推荐**：
   - 必须做 **balanced + blocked** experimental design（不允许 1 batch = 1 condition）
   - **ERCC spike-in** 是 quantitative QC（可选但极有用，2017 年 standard）
   - **Batch correction 必做**（ComBat / limma / sva）
   - **报告 batch + biology 双 PC contribution** 让读者判断 confound 程度

## ★ 排除/不做的事 (反面教材)
- **1 batch = 1 cell line 的 nested design**：完全 confound，没办法分离；事后 batch 校正都救不了
- **不做 ERCC spike-in**：technical noise 量级不可知；recovery 时 SNR 估计不可靠（2017 标准；2020+ 替代方案是大 cell 数 + 标准化）
- **PCA 未校正直接 cluster**：PC1 是 batch 时 cluster = batch artifact，不是 cell type
- **直接拿 raw count 跨 capture 跑 DE**：数千 false positive，与真 cell line difference 无关
- **不报告 PC variance breakdown by batch vs biology**：读者无法判断 confound 程度
- **跨 capture 的 normalization 用 size factor only**：忽略 capture-specific dropout 模式
- **小 batch (3 capture) 假设 batch effect 平均掉**：错；3 batch 不够 average，结构性 bias 仍在

## ★ 失败模式 (论文记录的)
- **Confounded design 的下游惩罚**：如果 batch 1 全是 line A，batch 2 全是 line B → 任何 "DE between line A vs B" 实际是 batch effect，但永远无法分辨
- **Capture-specific dropout**：Fluidigm C1 不同 capture 的 cell capture efficiency 不同 → 同 cell line 的相同基因，不同 capture 中 dropout 模式不同 → 不能用 simple log-norm 抹平
- **ERCC vs biological gene 不一致**：某些 capture 中 ERCC normalize 后 biological signal 更乱 → suggests 该 capture 的 lysis efficiency 异常
- **跨 capture cell number 不平衡**：60 vs 96 vs 96 → 60 那批 statistical power 不足，metric 不可信
- **后续 reanalysis 结论**：2020+ 学者再做时，发现 Tung 2017 推荐的 **balanced block design** 是必要不充分；3 个体 + 3 capture 仍然 underpowered for 真正的 inter-individual variance 估计；用作教学没问题，作为 benchmark 偏小
- **C1 平台被 droplet 取代**：Fluidigm C1 已不主流（成本 + 通量），但 batch effect 教训完全适用 droplet 平台（10x Chromium 的 GEM 批次也是 batch）

## ★ 方法选择决策链 (Tung 给出的)
```
设计 scRNA 实验?
├─ Step 1：cell-line / condition 分配
│   ├─ 必须 balanced：每 batch 包含所有 condition
│   ├─ Nested design (1 batch = 1 condition) → STOP，不可救
│   └─ 至少 2 batch 包含每个 condition → minimum
├─ Step 2：spike-in 加 ERCC（2017 标准；2020+ 可省但仍推荐）
├─ Step 3：cell number per batch 平衡（差 < 30%）
├─ Step 4：跑 batch correction (ComBat / limma / Harmony / scVI)
└─ Step 5：报告 PC variance by source + ERCC SNR

分析?
├─ 未校正先跑 PCA + 看 PC1/2 的 batch vs biology 来源
├─ 校正后 PCA + 同样的 breakdown
├─ DE 分析必须有 batch covariate
└─ 总报告含校正前/后对比
```

## ★ QC sanity check (known answer)
- Anchor (Tung 2017 LCL × 3 capture)：
  - **未校正 PC1**: ~29% variance, mostly capture (batch)
  - **未校正 PC2**: ~15% variance, mostly cell line (biology)
  - **校正后 PC1**: ~24%, mostly cell line
  - **ERCC variance**: 校正前 ≈ biological variance (SNR ~1:1)；校正后 SNR ~5:1
  - **DE between cell lines (校正后)**: ~200 genes，对应 inter-individual genetic variants 已知模式
  - **Cell number across captures**: 平衡（差 < 30%）
- Pass criterion: 校正前 PC1 是 batch + 校正后 PC1 是 biology + DE = ~200 in expected range
- Fail criterion: 校正后 PC1 仍是 batch → batch correction 失败；DE > 1000 → 残留 batch 假阳

## Lessons → seeds for rules
1. **Balanced + blocked experimental design 是 scRNA 必备**（不是事后救济）— rule 04 evidence 加强
2. **PC variance breakdown by batch vs biology 必报**：读者据此判断 confound 程度
3. **ERCC spike-in (2017 标准 / 2020+ 推荐)**：作为 SNR 量化器
4. **Capture / GEM 批次本质都是 batch**：从 C1 到 10x Chromium，物理批次都得校正
5. **Batch effect 在 single cell 比 bulk 更主导**（dropout + sparsity）—— rule 04 强化
6. **3-batch design 是教学最小数**：真正 cohort 推荐 ≥ 5 batch / 3+ condition
7. **校正前后双 PCA + DE count 对比** 是 scRNA paper 的标准 deliverable —— Reviewer 该 enforce
