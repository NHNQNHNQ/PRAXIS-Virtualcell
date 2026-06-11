---
case_id: microbiome-002-shotgun-kraken
task: shotgun_metagenomics_taxonomy
input_data: shotgun metagenomic Illumina paired-end reads
tools: [Kraken2, Bracken, MetaPhlAn4, Centrifuge, mOTUs2, sourmash]
key_paper_doi: 10.1186/s13059-019-1891-0
status: validated
microbiome_task: shotgun_taxonomy
sequencing_type: shotgun_short
sample_type: human_gut
reference_db: GTDB R220
dataset_accession: PRJEB6070
biomass_estimate: high
---

# Shotgun metagenomics taxonomy：Kraken2 + Bracken vs MetaPhlAn4

## Background
Shotgun metagenomics 比 16S 高 resolution + functional info。**Taxonomy classification** 主流两路：(1) **Kraken2 + Bracken**：k-mer-based, fast, requires large reference DB；(2) **MetaPhlAn4**：marker-gene-based, smaller DB, conservative classification。

## What I actually did
1. **Read QC + host removal**：fastp QC + bowtie2 vs human genome (hg38) → remove host reads
2. **Kraken2**：reads → genus-level/species-level call by k-mer against custom DB (Standard / PlusPF)
3. **Bracken refinement**：Kraken2 raw count → per-genome abundance estimate
4. **MetaPhlAn4 alternate**：marker gene (~5M genes from SGB) → species-level abundance
5. **Cross-validation**：Kraken+Bracken vs MetaPhlAn4 → species detected by both = high confidence
6. **Database choice**：
   - GTDB R220 (SGB-aware, 包括 unculturable)
   - RefSeq complete (curated but biased towards cultured)
7. **Confidence score**：Kraken2 confidence threshold (0.05 default; higher = more strict)
8. **Output**：sample × species abundance table + relative abundance

## ★ 排除/不做的事
- **Host reads 不 remove**：human DNA 主导 read pool，microbe coverage 低
- **Single classifier**：Kraken alone 假阳率 5-15%；MetaPhlAn alone miss novel SGB
- **Default confidence**：Kraken default 0.05 给 false positive；0.1-0.2 better
- **Skip Bracken**：raw Kraken count overestimate rare species (each k-mer unique hit)
- **Forget non-bacterial**：fungi / virus / archaea 同 pipeline 跑或 separate
- **% relative abundance only**：absolute quantification needs 16S spike-in or qPCR

## ★ 失败模式
- **Closely-related species confusion**：E.coli vs Shigella 95% genome identity → classifier confused
- **Novel taxa not in DB**：不在 reference DB 的 species → missed or assigned to nearest neighbor
- **Reagent / lab contamination**：low biomass severe issue (control samples 必跑)
- **Strain heterogeneity**：multiple strain of same species 看似 single species in classifier
- **Functional pathway != species composition**：abundance shift may not = function shift
- **DNA degradation**：dead microbe DNA still detected

## Lessons → seeds for rules
1. **Kraken2 + Bracken + MetaPhlAn4 dual classifier**
2. **Host removal mandatory**
3. **Confidence threshold 0.1+**
4. **Custom DB (GTDB)** for unculturable
5. **Negative control (DNA blank)** for contamination
6. **Genus level safer** for closely-related
7. **Functional + taxonomy parallel** (HUMAnN follows)
