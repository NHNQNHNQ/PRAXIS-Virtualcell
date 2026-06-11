---
case_id: immuno-008-car-t-target-selection
schema_version: 1
task: car_target_selection_safety
immuno_task: car_target_selection_safety
antigen_class: tumor_neoantigen
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: cancer_aml
target_disease: AML (acute myeloid leukemia)
target_protein_uniprot: []
candidate_targets: CD19 (B-ALL gold standard), CD33, CD123, CLL-1
tools: [DepMap, GTEx, HPA (Human Protein Atlas), TabulaSapiens, scRNA-seq atlases]
key_paper_doi: 10.1056/NEJMoa1709866
status: validated
source: praxis_seed
---

# CAR-T target selection：tumor vs normal expression specificity

## Background
CAR-T target 必须 (1) tumor 高表达；(2) 正常组织（特别 essential tissue）低/无表达；(3) 表面定位（CAR 不能内化进 target）；(4) 不易 escape (mutational stability)。CD19 在 B-ALL 是 gold standard——但对 myeloid (AML) 类似 target 难找。

## What I actually did
1. **Tumor expression**：DepMap CCLE / TCGA 看 CD33/CD123 在 AML cell line + 患者 samples 表达
2. **Normal tissue**：GTEx + HPA + TabulaSapiens 跨 32 organ 看表达
3. **Single-cell normal expression**：HCA / TabulaSapiens 看 specific cell type，特别 essential cell type（hepatocyte, cardiomyocyte, neuron）
4. **Surface localization**：UniProt + HPA 免疫荧光 + Compartments DB 验证 cell surface
5. **Differential expression score**：tumor / max(normal_essential_tissue) ratio ≥ 10
6. **Loss-of-target escape risk**：tumor cell 是否依赖该 target 生存（DepMap essentiality）；non-essential 易 escape
7. **Off-tumor on-target risk**：CD19 → B cell aplasia (acceptable)；CD33 → myeloid suppression (acceptable short-term)；GD2 → 神经毒性 (concerning)
8. **CAR design 配套**：affinity tuning（高 affinity → off-tumor 更 toxic；medium affinity → 区分 tumor 高表达 vs 正常低表达）

## ★ 排除/不做的事
- **Bulk RNA-seq only**：bulk 平均 mask cell type-specific 表达
- **Essential tissue 不优先查**：肝/心/肺/脑 必首查
- **不查 cell surface**：membrane vs cytoplasmic localization 决定 CAR feasibility
- **Single source expression**：DepMap + GTEx + HPA + scRNA 多源 cross-validate
- **Affinity 不 tune**：high affinity 是 anti-pattern for differential expression target
- **不评估 escape risk**：tumor 依赖该 target 才不易 escape

## ★ 失败模式
- **Antigen escape**：CD19 negative B-ALL relapse 30%+；non-essential target 易丢
- **On-target off-tumor toxicity**：BCMA-CAR (multiple myeloma) → plasma cell aplasia
- **Lineage shift**：CAR pressure 引发 myeloid → lymphoid 转换（已观察 AML → ALL）
- **Soluble antigen interference**：BCMA 在血清中 soluble form 高浓度 → 阻断 CAR
- **CAR-T persistence vs antigen density**：低 antigen density 不足 trigger CAR
- **Cytokine release syndrome (CRS)**：高 burden 时 CAR-T 释放 IL-6/IFNγ → severe

## Lessons → seeds for rules
1. **Multi-source expression**：DepMap + GTEx + HPA + scRNA-seq atlases
2. **Essential tissue panel** specifically 评估
3. **Surface localization 强制 验证**
4. **Differential expression ratio ≥ 10**
5. **Escape risk via essentiality**：tumor 依赖该 target = 优先
6. **Affinity tuning 设计阶段考虑**
7. **Soluble antigen check** in patient serum
