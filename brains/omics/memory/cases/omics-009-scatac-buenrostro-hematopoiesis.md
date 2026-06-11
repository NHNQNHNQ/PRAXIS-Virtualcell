---
case_id: omics-009-scatac-buenrostro-hematopoiesis
modality: scATAC_seq
study: Buenrostro et al 2018, Integrated Single-Cell Analysis Maps Human Hematopoiesis
public_accession: GSE96769
doi: 10.1016/j.cell.2018.03.074
organism: Homo sapiens
tissue: human bone marrow + CD34+ HSPC
tools:
- ArchR 1.0.2
- SnapATAC2
- MACS3
- chromVAR
status: validated
validated: true
source: praxis_seed
study_design: cohort_lineage
assay_subtype: scATAC_fragments
cell_type_focus:
- hematopoiesis
- HSPC
- erythroid
- myeloid
method_choice:
- archr
- snapatac2
- macs3
- chromvar
case_class: success
---

# Buenrostro 2018：scATAC 造血层级 + chromVAR motif 活性

## Background
首批高质量 scATAC-seq 数据集之一，覆盖造血干细胞到分化 lineage 的 chromatin landscape。难点：scATAC 极稀疏（每细胞 ~10k 唯一 fragment）、binary/count 选择、peak calling 的"鸡生蛋"问题（cluster 用什么 feature？peak？bin？）

## What I actually did
1. **从 fragments file 而非 peak matrix 起步**——peak set 决定下游一切，先有 cell × bin matrix 再 cluster 再 call peak per cluster 再回 cell × peak
2. **ArchR ArrowFile**：tile cell × 500bp bin matrix，TSS enrichment + nFrag QC（TSS > 4, nFrag > 1000 是宽松阈值，干细胞场景可放）
3. **Doublet by ArchR's simulation method**（不是 scrublet——scATAC 不同生成模型）
4. **Iterative LSI**（不用 PCA）：scATAC binary/count 跑 LSI 比 PCA 合适。**第一个 LSI component 几乎总和 fragment count 相关，去掉**
5. **Cluster 用 LSI components 2-30** → UMAP → Leiden
6. **Per-cluster peak calling** with MACS3，再合并 union peak set → cell × peak matrix
7. **chromVAR motif activity**：不直接看 peak accessibility（太稀疏），看 motif (TF) level 的活性。GATA1 在 erythroid lineage 高、PU.1 在 myeloid 高
8. **Trajectory**：MAGIC 平滑后 Palantir 推断 pseudotime；motif activity 沿 pseudotime 渐变

## ★ 排除/不做的事
- **跑 PCA on raw count**：scATAC 0/1 主导，PCA 解释力差；用 LSI（TF-IDF + SVD）
- **使用 bulk ATAC peak set**：bulk peak miss cell-type-specific peaks（罕见 lineage 的 peak 不在 bulk）
- **保留 LSI component 1**：≈ 测序深度，混入 cluster
- **Peak-level DE**：scATAC 单 peak 信号太稀，统计 power 极低——升级到 motif level（chromVAR）或 gene activity score
- **mito QC 套用 RNA 阈值**：scATAC 没 mito reads（核 prep）；用 TSS enrichment + fragment size periodicity 当 QC

## ★ 失败模式
- **Peak set 决定一切**：用错 peak set 后续 cluster 全错；必须 iterate（LSI cluster → call peak → re-LSI on peaks）
- **Mitochondrial fragments 污染**：未过滤 chrM 的 fragments 会主导；ArchR 默认过滤
- **Library complexity 低 cell**：罕见 cell type 测得稀，看似 doublet 其实是 unique biology
- **Multiome（RNA+ATAC same cell）联合分析**：cell barcode 必须严格匹配，分析 pipeline 完全不同（用 Signac/MultiVI）
- **Motif analysis bias**：chromVAR motif activity 受 GC content 影响，需 background correction

## ★ QC sanity check (known answer)
- Anchor (Buenrostro 2018 hematopoiesis GSE96769)：
  - **GATA1** motif activity (chromVAR z-score) 在 erythroid lineage 显著高 (z > 2)
  - **PU.1 (SPI1)** motif activity 在 myeloid lineage 显著高
  - **KLF1** motif activity 在 erythroid 同向上
  - LSI component 1 与 fragment count Spearman ρ > 0.7（确认是 depth proxy，必丢）
  - TSS enrichment median ≥ 4；nFrag median ≥ 1000
- Pass criterion：GATA1 z > 2 in erythroid AND PU.1 z > 2 in myeloid AND LSI C1 与深度强相关
- Fail criterion：motif activity 整体平坦 → 用了 PCA 或没丢 C1；TSS < 4 → QC 失败 (核 prep 问题)

## Lessons → seeds for rules
1. **scATAC 用 LSI 不用 PCA**，并丢第一个 component（depth proxy）
2. **Iterative peak calling**：tile → LSI → cluster → per-cluster MACS → union peak → re-LSI
3. **TSS enrichment + nFrag 是 QC 主指标**，不是 mito%
4. **分析升一级**：peak → motif (chromVAR) → gene activity，因 single-peak 信号太稀
5. **Multiome 优于单 modality**：RNA+ATAC 同 cell 用 WNN/MultiVI 整合
