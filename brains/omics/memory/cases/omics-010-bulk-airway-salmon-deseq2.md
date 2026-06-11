---
case_id: omics-010-bulk-airway-salmon-deseq2
modality: bulk_RNA_seq
study: Himes et al 2014, airway smooth muscle dexamethasone treatment
public_accession: GSE52778
doi: 10.1371/journal.pone.0099625
organism: Homo sapiens
tissue: airway smooth muscle
tools:
- salmon 1.10
- tximeta 1.20
- DESeq2 1.42
- fastp
- MultiQC
status: validated
validated: true
source: praxis_seed
study_design: case_control_paired
assay_subtype: bulk_paired_short_read
cell_type_focus:
- bulk_tissue
method_choice:
- salmon
- tximeta
- deseq2
- fgsea
case_class: success
---

# airway 数据集：bulk RNA-seq pipeline 端到端最小可复现案例

## Background
Bioconductor `airway` 教学数据，4 个供体配对的 dex/对照。已知答案：dex 应诱导 DUSP1、KLF15、ZBTB16 等 GR-target；抑制 IL6、PTGS2 等炎症基因。是 bulk RNA-seq pipeline 的 hello-world，能跑通这个再跑别的。

## What I actually did
1. **下载 fastq from SRA**（`prefetch SRR1039508-SRR1039521` + `fasterq-dump`），共 16 paired files
2. **fastp QC + adapter trim**：默认参数 + `--detect_adapter_for_pe`；保留 read length ≥ 36
3. **MultiQC 聚合 fastp + salmon log**——必看，> 30% adapter 或 < 70% mapping 是红旗
4. **Salmon quant**：`salmon quant -i gencode_v44_index --libType A --validateMappings --gcBias --seqBias --threads 8`。**`--gcBias` 必加**（mRNA GC 含量影响 quant），`--libType A` 让 salmon 自动检测链特异性（错了会少 50% counts）
5. **tximeta** 读入 + `summarizeToGene()` → `DESeqDataSet`
6. `design = ~ donor + dex`——**donor 必须建模**（配对设计），不建模等于扔掉一半 power
7. `DESeq()` → `lfcShrink(coef='dex_trt_vs_untrt', type='apeglm')`
8. **Sanity check**：DUSP1（dex up，known GR target）应在 top 50 up-regulated；padj < 0.01 + LFC > 1.5
9. fgsea + Hallmark：HALLMARK_INFLAMMATORY_RESPONSE down，TNF_SIGNALING_VIA_NFKB down

## ★ 排除/不做的事
- **不做 paired analysis**：忽略 donor 让 within-donor variability 进 noise，p-value 升高、power 暴跌
- **STAR + featureCounts 直接当默认**：不是错，但 salmon transcript-level 然后 tximeta 聚合到 gene 是更现代 + 更准（多重比对正确分配）
- **跳过 `--gcBias --seqBias`**：DE rank 受 GC content 偏差污染，富集分析也受影响
- **`--libType ISR/ISF` 不指定让用户填**：错填半数 read 丢；用 `A` 自动检测后核对 log
- **不看 MultiQC 直接进 DE**：mapping rate 50% 也能跑出 DE 但全部 noise
- **跨实验/批次合并不入 batch design**：多 lane 数据 lane 是 batch；不入 design 等于忽视

## ★ 失败模式
- **rRNA contamination**：library prep 不干净 → 80%+ reads 比对到 rRNA，剩余太少 power 不足。`--validateMappings` 报警但人工要看
- **Strand 错指定**：`ISF` vs `ISR` 错了 quant 全错，但 pipeline 不报错——必须看 salmon log 的 mapping rate
- **DEG list inflation by lowly expressed**：filter `rowSums(counts >= 10) >= n_smallest_group` 去掉 < 10 count 跨组的，否则 BH 校正被低 power 噪声拖累
- **Reference 不一致**：训 index 用 GENCODE v44 但 metadata 用 v40 → 转录本 ID mismatch，约 5-10% transcript "missing"
- **`design = ~ dex` 漏掉 donor**：本案 4 配对供体，结果 dex KLF15 LFC 从 5.8 降到 2.3 padj 升 100x

## ★ QC sanity check (known answer)
- Anchor (Himes 2014 airway GSE52778)：
  - **DUSP1** in dex_up top 50 (LFC > 1.5, padj < 0.01)
  - **KLF15, ZBTB16, FKBP5** 也 up（已知 GR target）
  - **IL6, PTGS2** down（炎症抑制）
  - HALLMARK_INFLAMMATORY_RESPONSE: down (NES < -1.5)
  - HALLMARK_TNF_SIGNALING_VIA_NFKB: down
  - Salmon mapping rate per sample > 70%
  - design = ~ donor + dex 时 KLF15 LFC ≈ 5.8；漏 donor 时降到 2.3
- Pass criterion：DUSP1 in top 50 up AND HALLMARK_INFLAMMATORY down AND mapping > 70%
- Fail criterion：DUSP1 不在 top 50 → pipeline 配错 (libtype 错 / 漏 batch)；mapping < 70% → fastq QC 问题

## Lessons → seeds for rules
1. **Paired/longitudinal 设计必须 design 反映**——通常 `~ subject + condition`
2. **Salmon `--gcBias --seqBias` + `--libType A`** 是 default
3. **MultiQC 聚合是 mandatory step** 不是可选；mapping rate < 70% 阻塞 pipeline
4. **Reference 一致性**（FASTA + GTF + index 同版本）是常被忽略的复现性杀手
5. **Sanity check 用已知答案**——airway 数据 DUSP1 必出，否则 pipeline 配置有错
