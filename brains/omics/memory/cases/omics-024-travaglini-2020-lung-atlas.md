---
case_id: omics-024-travaglini-2020-lung-atlas
schema_version: 1
modality: scRNA_seq
study: "Travaglini et al 2020, A molecular cell atlas of the human lung from single-cell RNA sequencing"
public_accession: "GSE136831 (10x); Synapse syn21041850 (Smart-seq2)"
doi: 10.1038/s41586-020-2922-4
organism: Homo sapiens
tissue: "human lung (proximal airway / distal alveoli / blood; 3 anatomical compartments)"
study_design: cohort_reference
assay_subtype: hybrid_smartseq2_10x_chromium
cell_type_focus: [AT2_alveolar, AT1, club_cell, basal_cell, ciliated, tuft, ionocyte, pulmonary_capillary, alveolar_macrophage]
tools: [Cellranger 3.0, Scanpy 1.4, Seurat 3.0, fastMNN, Harmony, BBKNN, scrublet 0.2]
method_choice: [hybrid_ss2_10x_design, facs_enrichment_for_rare, harmony_cross_platform, ontology_curation, marker_validation_in_situ]
status: validated
validated: true
source: praxis_seed
case_class: success
provenance:
  source_type: literature
  doi: 10.1038/s41586-020-2922-4
  extracted_at: 2026-05-01
tags: [lung_atlas, disease_relevant, hybrid_platform, rare_cell_types, cross_platform_integration]
---

# Travaglini 2020 Human Lung Atlas：cross-platform 的 disease-relevant 旗舰 reference

## Background
Travaglini 2020 是当前最权威的 human lung scRNA atlas（HLCA 雏形）：~75K cells across 58 cell types，3 anatomical compartments（proximal airway / distal alveoli / blood），来自 3 patients。**关键设计**：Smart-seq2（FACS-sorted, full-length, 高灵敏检 rare cell type）+ 10x Chromium（liquid-droplet, broad coverage）混合策略；cross-platform 整合是 anti-rule 集中地（rule 03 cross-platform）。这是 PRAXIS-Omics 第一个**disease-anchored reference atlas case**：与 case 001 (PBMC) 的 healthy benchmark / case 005 (NSCLC tumor) 互补，是 COVID-19 / 哮喘 / 肺癌等下游分析的 reference。

## What I actually did
1. **Hybrid platform 设计**（关键决策）：
   - **10x Chromium**: 高 throughput, ~50k cells/sample, broad cell type coverage，但 read length 短，低-丰度基因 dropout 大
   - **Smart-seq2 + FACS sort**: 384-well plate, ~5k cells total, full-length transcript, 丰度低 cell type 用 marker FACS 富集后再 SS2 → tuft cell / ionocyte 才"显形"
2. **Per-platform QC**:
   - 10x: nGenes ≥ 200, nUMI ≥ 500, mito% ≤ 25 (lung 特有 — 肺组织 mito 高于 PBMC)
   - SS2: SS2-specific QC, ERCC spike-in normalize, gene_count > 1500（per-cell deeper 但 fewer cells）
3. **Cross-platform integration**:
   - **Per-compartment first**: airway / alveoli / blood 三 compartment 分开 integrate（每 compartment 内 dataset 数 < 5 vs 跨 compartment 多）
   - **Harmony with batch=platform**: 平衡 mixing + biology preservation
   - **Cross-platform NOT naive concat**: SS2 + 10x 直接 concat 会让 SS2 cells 形成 outlier cluster
   - **Marker overlap check post-integration**: SFTPC, EPCAM 等已知 marker 在 10x cluster 和 SS2 cluster 中表达模式一致才算成功
4. **58 cell type ontology**:
   - 3 levels: cell_class > cell_type > cell_subtype
   - **Manual curation by domain expert**, not auto-call (rule 05)
   - 每 cell type ≥ 5 marker genes (rule 02 multi-marker; case 015 single-marker rejected)
5. **Rare cell type validation**:
   - **Tuft cell** (POU2F3+): 仅 ~0.04% of lung cells; SS2 + FACS sort enrichment 是唯一发现路径
   - **Ionocyte** (FOXI1+, CFTR+): 同上 rare; 文章前两年才被发现，atlas 验证存在
6. **In-situ confirmation**: 关键 marker（SFTPC, KRT5, SCGB1A1, FOXJ1）做 immunofluorescence (IF) on tissue sections 验证 cell type 空间分布

## ★ 排除/不做的事
- **SS2 + 10x naive concat 整合**：scale + dropout 完全不同；必须 batch=platform 校正
- **Lung 用 PBMC 标准 mito% 5%**：肺细胞代谢高，mito% ≤ 25% 才合适（rule 02 organ-aware mito，case 003 echo）
- **Auto-call cell type 不做 domain review**：tuft / ionocyte 等罕见 cell type 用 unsupervised cluster 易被合并
- **不做 in-situ validation 直接发表 cell type**：spatial confirmation 在 atlas paper 是 expected step
- **Rare cell type with < 30 cells 当独立 cluster**：power 不够；标 review，等 SS2 富集
- **不区分 anatomical compartment**：airway 和 alveoli 在 sequencing 前就该解剖分开；混合采样 = 失去 compartment-specific cell type
- **跨 patient 不 batch correct**：3 patient 间个体差异 > technical batch；必须 batch=patient

## ★ 失败模式
- **Tuft / ionocyte 缺失**：纯 10x 数据捕捉不到（< 0.1% 比例）；只用 10x 的 atlas 文章被审稿驳回需补 SS2
- **AT1 vs AT2 混淆**：AT1 (PDPN+, AGER+) 和 AT2 (SFTPC+) 在 10x 短 read 下 AGER 检测灵敏度低；若不验证两者比例（健康 lung AT1:AT2 ≈ 95:5）可能 mislabel
- **Cross-patient batch dominate**：3 patients 中一人病史长，单跑出独立 cluster；不 batch 校正会污染所有 cell type 计数
- **FACS bias**：FACS-sorted SS2 通常富集某 marker；该 marker 表达分布不能信，下游差异分析跳过该基因
- **Anatomical bleeding**：proximal airway sample 含 distal contamination → 该 sample 出现 AT2 等 distal cell type 是 cross-contamination
- **Reference atlas 时效**：2020 → 2025 cell type ontology 演化（如 lung CellRef 2024 更新），用旧 atlas 跑新 query 会有 unmapped cells

## ★ 方法选择决策链
```
建立 disease-relevant atlas?
├─ 单 platform (10x only) → 高通量但漏 rare cell type；用作 first pass + 后续补 SS2
├─ Hybrid (10x + SS2 FACS) → reference atlas standard；Travaglini 2020 / Tabula Sapiens 都是
├─ Cross-platform integration → 必 batch=platform，不能 naive concat
├─ Compartment 设计 → anatomy 决定 sampling，不是事后聚类
└─ Annotation → manual + multi-marker (≥5/cluster); rare types ≥ 30 cells；in-situ validate

Use atlas as reference (downstream)?
├─ Mapping query data via Symphony / scArches / Azimuth
├─ Check ontology level (cell_class vs cell_subtype) — 不要硬 map 到深层 ontology
├─ Unmapped cells > 5% → query 包含 atlas 没见过的 cell state
└─ Atlas version lock in provenance（2020 vs 2024 不同）
```

## ★ QC sanity check (known answer)
- Anchor (Travaglini 2020 lung atlas)：
  - **AT1:AT2 ratio ≈ 95:5** in alveolar compartment (cross-checked with histology)
  - **AT2 marker** SFTPC, SFTPB, ABCA3 high
  - **Club cell** SCGB1A1+ (proximal airway), SCGB3A2 (distal)
  - **Ciliated cell** FOXJ1+, TPPP3+
  - **Tuft cell** POU2F3+, AVIL+ (~0.04%, only via SS2 enrichment)
  - **Ionocyte** FOXI1+, CFTR+ (~0.05%, only via SS2)
  - **Cross-compartment**: blood macrophage (CD68+, ITGAM+) ≠ alveolar macrophage (FABP4+, MRC1+) — 同 macrophage class 不同 niche
- Pass criterion: 上述 marker 与 cell type 一致 + AT1:AT2 接近 95:5 + tuft + ionocyte 至少 ≥ 30 cells each
- Fail criterion: 单 10x dataset 没 tuft/ionocyte → 必须补 SS2；AT1:AT2 颠倒 → 标注或 sampling artifact

## Lessons → seeds for rules
1. **Atlas-grade paper 必混合 platform**：10x breadth + SS2 depth + FACS rare cell enrichment 三件套
2. **Per-tissue mito%**（rule 02 强化）：lung ≤ 25%，PBMC ≤ 15%，brain ≤ 5%
3. **Rare cell type discovery 路径**：unsupervised cluster 通常漏 < 0.1% 比例的 cell type；专属 enrichment 路径
4. **Anatomical compartment 在 sampling 阶段决定**：事后聚类不能挽救 mixed sampling
5. **Ontology multi-level + manual curation**：cell_class > cell_type > cell_subtype，rare type 在 subtype 层；automatic call 在 subtype 层不可信
6. **In-situ validation 是 atlas 标准 deliverable**：marker IF on tissue section 才发 atlas paper
7. **Atlas version lock**: 同 reference atlas 多版本（2020 vs 2024），mapping query 要 record 版本
