---
case_id: omics-004-bulk-tcga-brca-deseq2
modality: bulk_RNA_seq
study: TCGA-BRCA cohort, basal vs luminal subtypes
public_accession: TCGA-BRCA (recount3 / GDC)
doi: 10.1038/nature11412
organism: Homo sapiens
tissue: breast tumor
tools:
- DESeq2 1.42
- salmon 1.10
- tximeta 1.20
- fgsea 1.28
- edgeR 4.0
status: validated
validated: true
source: praxis_seed
study_design: cohort_subtype
assay_subtype: bulk_cohort_human_tumor
cell_type_focus:
- bulk_tissue
method_choice:
- deseq2
- salmon_tximeta
- fgsea_hallmark
case_class: success
---

# TCGA-BRCA：bulk DE + subtype 比较的标准

## Background
TCGA 乳腺癌队列 ~1100 患者，5 个 PAM50 内在亚型（Luminal A/B/Basal/Her2/Normal-like），是 cancer subtype DE 的范例数据集。Basal 与 Luminal A 之间的 DE 是经典 benchmark（已知答案：ESR1、KRT5/14、FOXA1、KRT8/18 等）

## What I actually did
1. **读 raw counts**（不是 TPM/FPKM——DESeq2 要 raw integer count）。从 recount3 R 包或 GDC `STAR_counts` 拉
2. **样本筛选**：只留 primary tumor `01A`（去掉 normal `11A`、metastasis `06A`）。**不混 normal 进 DE**，否则你测的不是 subtype 差异是 tumor vs normal
3. **PAM50 子型**：从 BRCA clinical 表读 `PAM50_call`；过滤 NA
4. `DESeqDataSetFromMatrix(counts, coldata, design=~ batch + subtype)`——TCGA 跨多个测序中心，**batch 必须入 design**（plate ID 或 institution）
5. **预过滤**：`rowSums(counts(dds) >= 10) >= smallest_group_size`——降维省时间且去 low-info genes
6. `DESeq()` 默认 Wald + BH。**收缩 LFC：`lfcShrink(type='apeglm')`**——TCGA 大样本本来 LFC 估计已稳定，apeglm 主要给低表达基因更可靠 ranking
7. **结果检查**：MA plot 应对称（不对称 = batch/normalization 问题）；p-value histogram 应"反 J"（U 形 = 模型不当）
8. **Pathway**：fgsea + MSigDB Hallmark/C2。Basal vs Luminal A 必出 EMT、MYC targets、estrogen response 反向

## ★ 排除/不做的事
- **不入 batch 进 design**：TCGA 26 plates，batch 主成分占方差 > 10%，不校正会污染结果
- **用 TPM/CPM 进 DESeq2**：normalization 重复+破坏 NB 假设；DESeq2 自己内部用 size factor
- **混 normal sample 进 subtype DE**：稀释信号，BRCA1/ESR1 等关键差异被洗
- **不做 LFC shrinkage**：低表达基因 LFC 极端值会污染 ranking 和 pathway
- **过度过滤 lowly expressed**：< 1 count 的全去通常 OK，但 < 10 across all samples 太激进会丢 cell-type-specific 基因

## ★ 失败模式
- **Sample contamination**：TCGA 部分 sample 有 stromal contamination（病理本身），ESTIMATE score 异常，纯肿瘤分析需先过滤
- **Confounder 与 subtype 共变**：年龄、菌种、grade 与 subtype 强相关；想测的因素如果和 subtype 共变，结果不可解读
- **Multiple testing across subtypes**：5 subtype 5 vs 5 比较 = 10 测试，需要全局多重校正不只 BH per test
- **GSEA 结果不稳**：rank 用 stat（Wald stat）比 LFC 稳；用 LFC 带零方差基因 NA 多

## ★ QC sanity check (known answer)
- Anchor (TCGA-BRCA, Basal vs LumA contrast)：
  - **ESR1**：down in Basal (LFC < -2, padj 顶端 1%)
  - **KRT5, KRT14** (basal markers)：up in Basal (LFC > 2)
  - **FOXA1, KRT8, KRT18** (luminal markers)：up in LumA (down in Basal)
  - HALLMARK_ESTROGEN_RESPONSE_LATE: down in Basal (NES < -1.5)
  - MA plot 对称（不对称 = batch / norm 问题）；p-value histogram 反 J 形
- Pass criterion：ESR1 LFC < -2 AND KRT5 LFC > 2 AND p-histogram 反 J
- Fail criterion：ESR1 LFC ~0 → batch (plate) 没建模；p-hist U 形 → 模型 misspec

## Lessons → seeds for rules
1. **Bulk DE：raw counts + DESeq2/edgeR**，永远不要用 TPM 进 NB 模型
2. **Batch 必须建模**——TCGA、GTEx、长时间收集的队列尤其
3. **LFC shrinkage 是默认**而不是可选，特别是低表达基因丰富时
4. **GSEA rank 用 test statistic 而非 LFC**，更稳定
5. **正常组织和肿瘤的 DE 是另一个问题**——subtype DE 必须在肿瘤内做
