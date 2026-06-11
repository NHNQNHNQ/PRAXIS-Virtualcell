---
case_id: microbiome-001-16s-dada2
task: 16s_amplicon_processing
input_data: 16S V3-V4 paired-end Illumina reads
target_organism: human gut microbiome
tools: [QIIME2, DADA2, Vsearch, SILVA 138 reference, GreenGenes2]
key_paper_doi: 10.1038/nmeth.3869
status: validated
microbiome_task: amplicon_16s
sequencing_type: 16S
sample_type: human_gut
reference_db: SILVA 138.1
dataset_accession: PRJNA48479
biomass_estimate: high
---

# 16S V3-V4 → ASV 表：DADA2 替代 OTU clustering

## Background
16S rRNA 是 microbiome characterization 标准 marker gene。**DADA2** (2016) 出现后 ASV (Amplicon Sequence Variant，单 nt resolution) 替代 OTU (97% identity cluster)。现代 16S 分析：QIIME2 + DADA2 + SILVA taxonomy。

## What I actually did
1. **Read QC**：FastQC + multiqc → trim primer + adapter
2. **Primer removal**：cutadapt for V3-V4 primers (341F + 805R)
3. **DADA2 denoising**：
   - `filterAndTrim` quality threshold (truncLen depends on read quality)
   - `learnErrors` (per-run error model)
   - `dada` (sample inference)
   - `mergePairs` (forward + reverse merge)
   - `makeSequenceTable` + `removeBimeraDenovo`
4. **Taxonomy assignment**：
   - SILVA 138 (most comprehensive)
   - 或 GreenGenes2 (reduced size)
5. **Phylogeny**：QIIME2 align → mafft + fasttree → rooted tree
6. **Quality metrics**：read counts post-filter (≥ 10k per sample preferred)
7. **Output**：ASV × sample table + taxonomy + tree → ready for downstream

## ★ 排除/不做的事
- **Primer 不 remove**：primer 序列在 ASV 中污染 taxonomy assignment
- **truncLen too short**：lose merged amplicon length
- **Skip chimera detection**：bimera + chimera 占 reads 5-30%
- **Per-run error model 不学**：不同 sequencing run 错误率不一
- **OTU clustering when DADA2 available**：ASV 信息更高
- **Single reference DB**：SILVA + RDP cross-validate for ambiguous taxa

## ★ 失败模式
- **Read overlap insufficient**：V3-V4 amplicon ~460 bp，2x250 read overlap ~40bp marginal
- **Reagent contamination**：DNA extraction kits 含 background (e.g., Burkholderia)；low biomass sample 严重
- **Primer mismatch**：rare taxa primer 不 cover, taxonomic bias
- **Copy number bias**：16S copy number 跨 species 1-15，abundance 估计偏
- **Genus-level resolution limit**：16S 在 species level 经常 ambiguous
- **Sequencing depth uneven**：rarefaction 必须

## Lessons → seeds for rules
1. **DADA2 ASV > OTU clustering**
2. **Per-run error model** in DADA2
3. **Chimera removal** mandatory
4. **SILVA 138 default**, RDP cross-check
5. **Read depth ≥ 10k** per sample
6. **Reagent blank control** for low biomass
7. **Genus-level analysis** safer than species
