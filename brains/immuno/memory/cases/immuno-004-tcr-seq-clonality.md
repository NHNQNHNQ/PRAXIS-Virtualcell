---
case_id: immuno-004-tcr-seq-clonality
schema_version: 1
task: tcr_repertoire_analysis
immuno_task: tcr_repertoire_analysis
antigen_class: tumor_neoantigen
hla_class: n/a
hla_alleles: []
peptide_length_bin: n/a
disease_indication: cancer_melanoma
target_data: TCR-seq from melanoma TIL (TIL-derived T cell receptor sequencing)
target_protein_uniprot: []
tools: [MiXCR, IgBLAST, Immcantation, scirpy (for scTCR), GLIPH2, TCRdist3]
key_paper_doi: 10.1038/nm.4051
status: validated
source: praxis_seed
---

# TCR-seq：clonality + CDR3 motif + antigen specificity 推断

## Background
TCR-seq（bulk or single-cell）测 T cell α/β chain CDR3——是 immune monitoring 核心。Clonality 高 = 抗原驱动 expansion (good)；clonality 低 = polyclonal 状态 (different biology)。CAR-T / TIL therapy 必备分析。

## What I actually did
1. **Raw data**：bulk TCR-seq Illumina paired-end OR scTCR-seq (10x VDJ)
2. **Alignment**：MiXCR `analyze` → V/D/J gene + CDR3 amino acid
3. **QC**：read count per sample / unique CDR3 / OOF (out-of-frame) ratio
4. **Diversity metrics**：
   - Shannon entropy（low = expanded clones dominate）
   - Simpson D50（top clone count to reach 50% reads）
   - Gini coefficient
   - Chao1 (estimated unique clone richness)
5. **Top 100 clones**：rank + frequency + V-J usage + CDR3 length distribution
6. **GLIPH2 / TCRdist3**：cluster CDR3 by sequence similarity → motif suggestive of shared antigen
7. **Antigen specificity**：query VDJdb / IEDB / McPAS for known antigen-specific TCRs in cluster
8. **Public vs private**：public TCR (跨 patient 共享) 可能 viral；private 是个体化
9. **Tumor vs blood TCR overlap**：tumor 富集 clone 是 candidate tumor-reactive

## ★ 排除/不做的事
- **OOF rate 不查**：> 30% OOF 可能 PCR/sequencing 错误
- **Bulk TCR-seq 当 functional readout**：sequence 不直接 prove activity
- **Single-chain TCR**：没 αβ pair sequence，antigen specificity 推断弱
- **Antigen specificity 信任 single database**：VDJdb 与 McPAS 部分不一致
- **Clonality 跨 sample 直接比较 not normalized**：sequencing depth 影响必须 rarefaction
- **All public TCR当 antigen-specific**：很多 public 是 noise / common rearrangement

## ★ 失败模式
- **PCR bias**：multiplex primer 偏好某些 V gene，frequency 失真
- **Allele-specific primer mismatch**：少见 V gene allele 引物 miss
- **Clone definition ambiguity**：CDR3 nucleotide vs amino acid 同一 vs 不同 clone
- **TCRαβ pairing in bulk**：bulk 不能 pair α 与 β，single-cell 才能
- **Convergent recombination**：相同 CDR3 来自不同 V/J recomb → 多 reads 但同 sequence
- **Memory bias**：long-lived memory T cell 高 frequency 不一定 active
- **Specificity prediction bias**：databases 偏 viral antigen，tumor neoantigen sparse

## Lessons → seeds for rules
1. **MiXCR + IgBLAST cross-validate**
2. **Diversity 4 metric** combined（Shannon + D50 + Gini + Chao1）
3. **GLIPH2 cluster + database query** for antigen
4. **Single-cell TCR > bulk** for αβ pair
5. **Tumor vs blood overlap** for tumor-reactive
6. **Rarefaction normalize** before cross-sample
7. **Public vs private 标签**
