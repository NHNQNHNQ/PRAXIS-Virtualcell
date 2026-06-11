---
case_id: omics-008-mofa-cll-multiomics
modality: bulk_multiomics
study: Argelaguet et al 2018, MOFA application to CLL
public_accession: ICGC CLLE-ES + array data
doi: 10.15252/msb.20178124
organism: Homo sapiens
tissue: CLL B cells (200 patients)
tools:
- MOFA+ (mofapy2)
- DIABLO (mixOmics)
- JIVE
status: validated
validated: true
source: praxis_seed
study_design: cohort_factor_analysis
assay_subtype: bulk_multiomics_4_views
cell_type_focus:
- B_cell_CLL
method_choice:
- mofa_plus
- diablo
- jive
case_class: success
---

# CLL multi-omics with MOFA+：因子分析整合 RNA + DNA甲基化 + ex-vivo药物 + somatic mutation

## Background
MOFA 在 200 例 CLL 患者上整合 4 个 modality：bulk RNA-seq、DNA methylation array、ex vivo drug response、somatic mutation。**目标不是分类**而是无监督因子分解，识别哪些 latent factors 跨 modality 一致解释 patient 异质性（IGHV 状态、trisomy 12 等）。

## What I actually did
1. **每个 modality 独立预处理**：RNA log + HVG top 5000；methylation 取 CpG with high variance；drug response z-score；mutation 二值化
2. **Sample × feature 矩阵对齐**：同一 patient set across modalities（共有 ~190 患者，缺一个 modality 的删）
3. **MOFA+ 训练**：`MOFA(views=[RNA, meth, drug, mut], n_factors=15, schedule='convergence')`——n_factors 不能太多否则过拟合 noise，太少损失生物学
4. **Factor 解释**：每个 factor 输出 (1) variance explained per modality bar plot；(2) top loadings；(3) factor value vs patient metadata
5. **Factor 1 主导 IGHV mutation status**（M-CLL vs U-CLL），跨 4 modality 都强解释 → 真生物学；factor 5 仅在 drug 强表达 → 可能 batch 或技术
6. **Sparsity prior**（spike-and-slab）让 loading 解释性更好——多数 feature loading=0，少数 driver feature 突出

## ★ 排除/不做的事
- **不预先 PCA 降维就喂 MOFA**：feature 数差异极大（meth 450k vs mut 50）会让 high-d modality 主导
- **Modality scale 不归一化**：MOFA 用 reconstruction error，scale 差 1000x 的 modality 算法只关心大 scale 的
- **缺失 imputation 后再 MOFA**：MOFA 原生支持 missing；二次 imputation 引入虚假 pattern
- **n_factors=50 一刀切**：> 真因子数会出现"phantom factor"——只在 1 modality 解释少量 variance，noise
- **factor 当 cluster 用**：MOFA factor 是 continuous latent，不是离散类别；硬切会丢信息

## ★ 失败模式
- **Modality dominance**：methylation 450k 维度 vs mutation 50 维度，未归一化时 meth 吃掉 80% factor
- **Patient confounder 进 factor**：性别、年龄、采样地点没建模会作为 dominant factor 出来——deflate 后再做生物解读
- **Sparsity 太弱**：所有 feature loading 非零，可解释性差；spike-and-slab 是默认
- **小 modality（如 mutation 50 features）几乎不影响 factor**：但其实是 driver mutation，需要 ARD（automatic relevance determination）权重
- **Reproducibility**：随机初始化敏感；跑多次（≥10 seed）取 robust factors

## ★ QC sanity check (known answer)
- Anchor (Argelaguet 2018 CLL ICGC CLLE-ES)：
  - **Factor 1** 强解释 IGHV mutation status（M-CLL vs U-CLL），跨 4 modality (RNA / methylation / drug / mutation) 都解释 > 5% variance
  - **Factor 2-3** 解释 trisomy 12 / del(11q) 等 cytogenetic abnormality
  - n_factors elbow ≈ 5-15（不该 > 25）
  - Sparsity (spike-and-slab) 后多数 feature loading = 0；driver feature 突出
  - Multi-seed (≥ 10) 取 stable factors，cosine similarity > 0.8
- Pass criterion：factor 1 separates IGHV M vs U AND cross-modality variance > 5% on ≥ 2 views
- Fail criterion：n_factors > 25 → phantom factors；cross-seed similarity < 0.5 → 不 robust

## Lessons → seeds for rules
1. **MOFA 前每个 modality 独立 normalize 到可比 scale**（z-score 或 unit variance）
2. **n_factors 跑 elbow analysis**：variance explained vs factors 拐点（通常 5-15）
3. **Sparsity prior 强制开**（spike-and-slab）以便解释
4. **Factor validation 跨 modality**：variance > 5% 在 ≥ 2 modality 才算 robust factor
5. **Reproducibility**：多 seed 取 stable factors（cosine similarity > 0.8 across runs）
6. **DIABLO 替代场景**：有 supervision（已知 outcome）时 DIABLO 比 MOFA 更适合
